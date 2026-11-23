# -*- coding: utf-8 -*-
r"""用大模型迭代「道」的功能：发现→提改法→在白名单里真改→验一遍→留账。

设计取舍：不让大模型直接改代码（它看不见副作用，改坏了没人兜）。
改成「参数级白名单」——每个可改点都写死文件、正则、当前值、允许范围、验收指标，
大模型只能在范围内挑值并说明理由；脚本负责备份、替换、编译检查、指标复测，
任何一步失败自动回滚。这样它真能改到功能上，又不至于把程序改死。

产出：F:\Daodao\巡检报告\大模型迭代_YYYYMMDD_HHMM.md

用法：python 大模型迭代.py [--dry]
"""
import io
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.request

BASE = r"F:\Daodao"
QB = os.path.join(BASE, "自我状态", "问题库.json")
LOG = os.path.join(BASE, "同步日志.txt")
REPORT_DIR = os.path.join(BASE, "巡检报告")
KEY_FILE = os.path.join(BASE, "src", "桌面分身", "key.txt")
PY = r"E:\Python313\python.exe"
API = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
MODEL_CHAIN = ("glm-4-flash", "glm-4.7-flash", "glm-4-air")

# 可改点白名单：(名字, 文件, 正则, 当前值, 下限, 上限, 说明, 改完复测的脚本)
TARGETS = [
    {
        "name": "filter_high_shelf_db",
        "file": os.path.join(BASE, "tools", "语音", "人声滤镜_biquad.py"),
        "pattern": r"_high_shelf\(sr, 3200\.0, (-[0-9.]+)\)",
        "current": -2.0, "min": -3.5, "max": -1.0,
        "why": "3200Hz 高搁架增益（dB）。负得越多压得越狠、越不刺耳但也越闷；往 0 走就是变亮",
        "metric": "harsh",
    },
    {
        "name": "filter_peak_db",
        "file": os.path.join(BASE, "tools", "语音", "人声滤镜_biquad.py"),
        "pattern": r"_peaking\(sr, 4500\.0, (-[0-9.]+), q=0\.9\)",
        "current": -1.5, "min": -3.0, "max": -0.5,
        "why": "4500Hz 钟形峰增益（dB）。负得越多 4~5k 越平、电音越轻；往 0 走会更硬",
        "metric": "harsh",
    },
    {
        "name": "judge_D_db",
        "file": os.path.join(BASE, "tools", "音乐", "人声", "演唱合格检查.py"),
        "pattern": r"D_MIN\s*=\s*([0-9.]+)",
        "current": 6.0, "min": 4.0, "max": 9.0,
        "why": "句内动态差门槛（dB）。真人基线未知，暂按经验区间",
        "metric": None,
    },
    {
        "name": "judge_V_ratio",
        "file": os.path.join(BASE, "tools", "音乐", "人声", "演唱合格检查.py"),
        "pattern": r"V_MIN\s*=\s*([0-9.]+)",
        "current": 0.30, "min": 0.15, "max": 0.45,
        "why": "长句颤音调制占比门槛（0~1）",
        "metric": None,
    },
]

SYS = """你是「道」的工程负责人，任务是拿真实数据把功能往前推一小步。
只依据给的材料说话，不许编造；不许提“重构整个模块”这类大动作。
输出纯 JSON，不要代码块：
{"本轮改":{"name":"上面白名单里的其中一个 name","新值":数字,"理由":"一句"},
 "新问题":[{"标题":"","严重度":"P0|P1|P2","复现":"","依据":""}],
 "下一步":[{"项":"能力名","修法":"具体到文件/参数/命令"}],
 "综述":""}
原则：一次只改一个参数，新值必须落在给的范围里。
注意：滤镜参数已经压到实测最优点（再往 0 走会被判为变差并回滚）；如果一个滤镜参数没有更优空间，就去改判据类参数。"""


def read_key():
    return io.open(KEY_FILE, encoding="utf-8").read().strip()


def call_llm(prompt):
    key = read_key()
    last = None
    for model in MODEL_CHAIN:
        body = {"model": model, "messages": [
            {"role": "system", "content": SYS},
            {"role": "user", "content": prompt},
        ], "temperature": 0.3, "max_tokens": 1200}
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
    raise last


def fix_escapes(t):
    return re.sub(r'(?<!\\)\\(?!["\\/bfnrtu])', r'\\\\', t)


def parse_json(txt):
    m = re.search(r"\{[\s\S]*\}", txt)
    if not m:
        raise ValueError("no json")
    body = m.group(0)
    for cand in (body, fix_escapes(body)):
        try:
            return json.loads(cand)
        except Exception:
            continue
    raise ValueError("invalid json")


def recent_context(n=60):
    lines = []
    if os.path.exists(LOG):
        lines = io.open(LOG, encoding="utf-8", errors="replace").read().splitlines()[-n:]
    return "\n".join(lines)


def open_issues():
    d = json.load(io.open(QB, encoding="utf-8"))
    return d, d["问题"]


def measure(name, file_path):
    """改完复测：对滤镜用 30 秒真语音算刺耳比，对判据只做编译检查。"""
    if name.startswith("filter"):
        code = (
            "import sys;sys.path.insert(0,r'F:\\Daodao\\tools\\语音');"
            "import numpy as np,soundfile as sf;"
            "from 人声滤镜_biquad import apply_chain;"
            "x,sr=sf.read(r'F:\\Daodao\\曲库\\_试音_声库\\语音_原始.mp3',dtype='float32');"
            "y=apply_chain(x,sr);"
            "f=np.fft.rfftfreq(len(x),1/sr);"
            "X=np.abs(np.fft.rfft(x*np.hanning(len(x))));Y=np.abs(np.fft.rfft(y*np.hanning(len(y))));"
            "h0=X[(f>=3200)&(f<=8000)].mean()/X[(f>=300)&(f<=3200)].mean();"
            "h1=Y[(f>=3200)&(f<=8000)].mean()/Y[(f>=300)&(f<=3200)].mean();"
            "print('harsh %.3f->%.3f'%(h0,h1))"
        )
        p = subprocess.run([PY, "-c", code], capture_output=True, text=True, timeout=120)
        return (p.stdout.strip() or p.stderr.strip())[:200]
    p = subprocess.run([PY, "-m", "py_compile", file_path], capture_output=True, text=True)
    return "compile ok" if p.returncode == 0 else ("compile FAIL " + p.stderr[:160])


def main():
    dry = "--dry" in sys.argv
    d, qs = open_issues()
    open_items = [q for q in qs if q.get("状态") != "solved"]
    brief = "\n".join("#%s [%s] %s" % (q.get("id"), q.get("严重度"), q.get("标题")) for q in open_items[:40])
    tgt = "\n".join("%s | 当前 %s | 允许 %s~%s | %s" % (t["name"], t["current"], t["min"], t["max"], t["why"]) for t in TARGETS)
    prompt = "【可改参数白名单】\n%s\n\n【未解决问题 %d 条】\n%s\n\n【最近日志】\n%s" % (
        tgt, len(open_items), brief, recent_context(50)[-5000:])
    txt, model = call_llm(prompt)
    try:
        out = parse_json(txt)
    except Exception:
        txt, model = call_llm(prompt + "\n\n上次输出不合法，这次务必给完整纯 JSON，只允许一个参数。")
        out = parse_json(txt)

    pick = out.get("本轮改") or {}
    name = str(pick.get("name", ""))
    applied, result, note = None, "", ""
    t = next((x for x in TARGETS if x["name"] == name), None)
    if t:
        try:
            new = float(pick.get("新值"))
        except Exception:
            new = None
        if dry:
            note = "dry：未落盘（会改 %s %s → %s）" % (name, t["current"], new)
        elif new is not None and t["min"] <= new <= t["max"] and abs(new - t["current"]) > 1e-9:
            src = io.open(t["file"], encoding="utf-8").read()
            m = re.search(t["pattern"], src)
            if not m:
                note = "正则没匹配上，跳过"
            else:
                baseline = measure(t["name"], t["file"])
                bak = t["file"] + ".bak_%s" % time.strftime("%Y%m%d%H%M")
                shutil.copy2(t["file"], bak)
                new_src = src[:m.start(1)] + str(new) + src[m.end(1):]
                io.open(t["file"], "w", encoding="utf-8").write(new_src)
                result = measure(t["name"], t["file"])
                worse = False
                b0 = re.search(r"harsh [0-9.]+->([0-9.]+)", baseline)
                b1 = re.search(r"harsh .*->([0-9.]+)", result)
                if b0 and b1:
                    worse = float(b1.group(1)) > float(b0.group(1)) - 0.003
                if result.startswith("compile FAIL") or worse:
                    io.open(t["file"], "w", encoding="utf-8").write(src)
                    note = ("编译失败已回滚" if result.startswith("compile FAIL") else "指标变差已回滚：" + result)
                else:
                    # 同步镜像到 exe 目录 / 根目录（滤镜模块有两份副本）
                    for mirror in (os.path.join(BASE, "src", "桌面分身", "人声滤镜_biquad.py"),
                                   os.path.join(BASE, "人声滤镜_biquad.py")):
                        if os.path.exists(mirror) and "biquad" in t["file"]:
                            shutil.copy2(t["file"], mirror)
                    applied = (name, t["current"], new)
                    note = str(pick.get("理由", ""))[:200]
        else:
            note = "新值超范围或没变，跳过"
    else:
        note = "大模型没给出白名单内的参数名"

    # 新问题登记
    n = 0
    added = []
    for q in qs:
        mm = re.match(r"Q-(\d+)", str(q.get("id", "")))
        if mm:
            n = max(n, int(mm.group(1)))
    seen = [str(x.get("标题", "")) for x in qs]
    for it in out.get("新问题", [])[:6]:
        title = str(it.get("标题", "")).strip()
        if not title:
            continue
        if any(title[:6] in t or t[:6] in title for t in seen if t):
            continue
        n += 1
        added.append({"id": "Q-%03d" % n, "标题": title, "来源": "大模型迭代",
                      "严重度": it.get("严重度", "P2") if it.get("严重度") in ("P0", "P1", "P2") else "P2",
                      "状态": "open", "发现时间": time.strftime("%Y-%m-%d %H:%M"),
                      "复现": str(it.get("复现", ""))[:300], "依据": str(it.get("依据", ""))[:300],
                      "scored": False})

    os.makedirs(REPORT_DIR, exist_ok=True)
    rep = os.path.join(REPORT_DIR, "大模型迭代_%s.md" % time.strftime("%Y%m%d_%H%M"))
    L = ["# 大模型迭代 %s（model=%s）" % (time.strftime("%Y-%m-%d %H:%M"), model), ""]
    L += ["## 本轮改动", ""]
    if applied:
        L += ["- %s：%s → %s（%s）" % (applied[0], applied[1], applied[2], note),
              "- 复测：`%s`" % result]
    else:
        L += ["- 未改（%s）" % note]
    L += ["", "## 新登记问题", ""] + (["- **%s** [%s] %s" % (x["id"], x["严重度"], x["标题"]) for x in added] or ["- 无"])
    L += ["", "## 下一步", ""] + (["- **%s** %s" % (s.get("项", ""), str(s.get("修法", ""))[:200]) for s in out.get("下一步", [])[:10]] or ["- 无"])
    if out.get("综述"):
        L += ["", "## 综述", "", str(out["综述"])]
    io.open(rep, "w", encoding="utf-8").write("\n".join(L) + "\n")

    if not dry:
        if added:
            b = os.path.join(BASE, "自我状态", "问题库_bak_%s.json" % time.strftime("%Y%m%d_%H%M"))
            shutil.copy2(QB, b)
            qs.extend(added)
            d["版本"] = int(d.get("版本", 1)) + 1
            io.open(QB, "w", encoding="utf-8").write(json.dumps(d, ensure_ascii=False, indent=2))
        io.open(LOG, "a", encoding="utf-8").write(
            "%s [大模型迭代] %s\n" % (time.strftime("%Y-%m-%d %H:%M"),
                                     ("改 %s %s->%s，复测 %s" % (applied[0], applied[1], applied[2], result)) if applied else ("未改：" + note)))

    print("ITER|%s" % rep)
    print("改动=%s 新问题=%d 模型=%s" % ("%s %s->%s" % applied if applied else "无", len(added), model))
    return 0


if __name__ == "__main__":
    sys.exit(main())
