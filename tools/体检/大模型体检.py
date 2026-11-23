# -*- coding: utf-8 -*-
r"""让大模型体检「道」：读问题库 + 最近日志，找出新问题、更新老问题、给修法。

产出：
1) F:\Daodao\巡检报告\大模型体检_YYYYMMDD_HHMM.md   给人看的报告
2) 问题库.json 就地更新（改前先备份到 问题库_bak_*.json）
只允许大模型做两类改动：登记新问题、把已有未解决问题改成 solved（附依据），
别的字段一律不动，避免它乱改历史。

用法：
    python 大模型体检.py            # 走一遍并落盘
    python 大模型体检.py --dry      # 只看报告，不改问题库
"""
import io
import json
import os
import re
import sys
import time
import urllib.request

BASE = r"F:\Daodao"
QB = os.path.join(BASE, "自我状态", "问题库.json")
LOG = os.path.join(BASE, "同步日志.txt")
REPORT_DIR = os.path.join(BASE, "巡检报告")
KEY_FILE = os.path.join(BASE, "src", "桌面分身", "key.txt")
API = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
MODEL_CHAIN = ("glm-4-flash", "glm-4.7-flash", "glm-4-air")

SYS = """你是桌面助手「道」的自检工程师。只根据给你的问题库和日志说话，不许编造。
任务：
1) 找新问题：日志里出现但没有登记在问题库里的故障/反复失败/明显退步，登记进来；只登真实出现过的，别凭空猜。
2) 更新老问题：如果日志证据表明某个未解决问题已经解决了，把它标 solved 并写清依据；证据不足就不要动。
3) 给修法：对仍 open 的问题，各给一句能落地的下一步（要具体到文件/命令/参数）。
输出必须是纯 JSON，不要代码块，不要多余文字：
{"新问题":[{"标题":"","严重度":"P0|P1|P2","复现":"","依据":""}],
 "状态更新":[{"id":"Q-xxx","状态":"solved","解决说明":""}],
 "下一步":[{"id":"Q-xxx","修法":""}],
 "综述":""}"""


def read_key():
    return io.open(KEY_FILE, encoding="utf-8").read().strip()


def call_llm(prompt):
    key = read_key()
    last = None
    for model in MODEL_CHAIN:
        body = {"model": model, "messages": [
            {"role": "system", "content": SYS},
            {"role": "user", "content": prompt},
        ], "temperature": 0.2, "max_tokens": 2200}
        req = urllib.request.Request(API, data=json.dumps(body, ensure_ascii=False).encode("utf-8"), method="POST")
        req.add_header("Content-Type", "application/json")
        req.add_header("Authorization", "Bearer " + key)
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                obj = json.loads(r.read().decode("utf-8"))
            txt = obj["choices"][0]["message"]["content"].strip()
            if txt:
                return txt, model
            raise ValueError("empty")
        except Exception as e:
            last = e
            continue
    raise last


def _fix_escapes(t):
    """把大模型常写坏的反斜杠（Windows 路径）补成合法转义：\D 这种一律变 \\\\D。"""
    return re.sub(r'(?<!\\)\\(?!["\\/bfnrtu])', r'\\\\', t)


def parse_json(txt):
    m = re.search(r"\{[\s\S]*\}", txt)
    if not m:
        raise ValueError("no json")
    body = m.group(0)
    for cand in (body, _fix_escapes(body)):
        try:
            return json.loads(cand)
        except Exception:
            continue
    raise ValueError("invalid json")


def next_id(qs):
    n = 0
    for q in qs:
        m = re.match(r"Q-(\d+)", str(q.get("id", "")))
        if m:
            n = max(n, int(m.group(1)))
    return n


def main():
    dry = "--dry" in sys.argv
    d = json.load(io.open(QB, encoding="utf-8"))
    qs = d["问题"]
    open_items = [q for q in qs if q.get("状态") != "solved"]
    log_text = ""
    if os.path.exists(LOG):
        raw = io.open(LOG, encoding="utf-8", errors="replace").read().splitlines()
        log_text = "\n".join(raw[-160:])

    brief = "\n".join("#%s [%s/%s] %s" % (q.get("id"), q.get("严重度"), q.get("状态"), q.get("标题")) for q in open_items)
    prompt = "【未解决问题 %d 条】\n%s\n\n【最近日志】\n%s" % (len(open_items), brief, log_text[-6000:])
    txt, model = call_llm(prompt)
    try:
        out = parse_json(txt)
    except Exception:
        txt, model = call_llm(prompt + "\n\n上一次输出被截断或不合法，这次务必输出完整、合法的纯 JSON，条目控制在 6 条以内。")
        try:
            out = parse_json(txt)
        except Exception as e:
            print("ERR 大模型没给合法 JSON：%r\n原文：%s" % (e, txt[:400]))
            return 2

    new_items = []
    n = next_id(qs)
    for it in out.get("新问题", [])[:10]:
        t = str(it.get("标题", "")).strip()
        if not t:
            continue
        n += 1
        new_items.append({
            "id": "Q-%03d" % n,
            "标题": t,
            "来源": "大模型体检",
            "严重度": it.get("严重度", "P2") if it.get("严重度") in ("P0", "P1", "P2") else "P2",
            "状态": "open",
            "发现时间": time.strftime("%Y-%m-%d %H:%M"),
            "复现": str(it.get("复现", ""))[:300],
            "依据": str(it.get("依据", ""))[:300],
            "scored": False,
        })

    updates, rejected = [], []
    EVID = ("实测", "自检", "退出码", "PASS", "RESULT", "OK|", "重建后")
    DOUBT = ("可能", "未查明", "推测", "疑似", "大概")
    for up in out.get("状态更新", [])[:10]:
        qid = str(up.get("id", ""))
        note = str(up.get("解决说明", ""))
        if up.get("状态") != "solved":
            continue
        # 只认带验证证据的「已解决」，否则一律押回待核，避免大模型凭感觉关单
        if any(k in note for k in DOUBT) or not any(k in note for k in EVID):
            rejected.append((qid, note[:120]))
            continue
        for q in qs:
            if q.get("id") == qid and q.get("状态") != "solved":
                q["状态"] = "solved"
                q["解决时间"] = time.strftime("%Y-%m-%d %H:%M")
                q["解决说明"] = note[:400]
                updates.append(qid)
                break

    os.makedirs(REPORT_DIR, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M")
    rep = os.path.join(REPORT_DIR, "大模型体检_%s.md" % stamp)
    lines = ["# 大模型体检 %s（model=%s）" % (time.strftime("%Y-%m-%d %H:%M"), model), ""]
    lines.append("体检前未解决 **%d** 条；本次新增 **%d** 条，标记解决 **%d** 条。" % (len(open_items), len(new_items), len(updates)))
    lines.append("")
    if out.get("综述"):
        lines += ["## 综述", "", str(out["综述"]), ""]
    lines += ["## 新问题", ""]
    lines += ["- **%s** [%s] %s" % (it["id"], it["严重度"], it["标题"]) for it in new_items] or ["- 无"]
    lines += ["", "## 标记解决", ""]
    lines += ["- %s" % u for u in updates] or ["- 无"]
    lines += ["", "## 证据不足、押回待核（未改状态）", ""]
    lines += ["- %s %s" % (qid, note) for qid, note in rejected] or ["- 无"]
    lines += ["", "## 下一步", ""]
    for s in out.get("下一步", [])[:12]:
        lines.append("- **%s** %s" % (s.get("id", ""), str(s.get("修法", ""))[:200]))
    if not out.get("下一步"):
        lines.append("- 无")
    io.open(rep, "w", encoding="utf-8").write("\n".join(lines) + "\n")

    if not dry:
        bak = os.path.join(BASE, "自我状态", "问题库_bak_%s.json" % stamp)
        io.open(bak, "w", encoding="utf-8").write(io.open(QB, encoding="utf-8").read())
        qs.extend(new_items)
        d["版本"] = int(d.get("版本", 1)) + 1
        io.open(QB, "w", encoding="utf-8").write(json.dumps(d, ensure_ascii=False, indent=2))
        io.open(LOG, "a", encoding="utf-8").write("")

    print("REPORT|%s" % rep)
    print("新增=%d 解决=%d 仍未解决=%d 模型=%s" % (len(new_items), len(updates),
          len([q for q in qs if q.get("状态") != "solved"]), model))
    return 0


if __name__ == "__main__":
    sys.exit(main())
