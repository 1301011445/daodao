# -*- coding: utf-8 -*-
r"""八域大模型迭代（内容型）：语言/创作真落盘，其余出可执行提案并登记。

指标来自八域优化.py 的实测报告；大模型只负责出内容与判断，落盘由脚本做。
用法：python 八域迭代.py
"""
import io
import json
import os
import re
import subprocess
import sys
import time
import urllib.request

BASE = r"F:\Daodao"
KEY_FILE = os.path.join(BASE, "src", "桌面分身", "key.txt")
API = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
MODEL = "glm-4-flash"
PY = r"E:\Python313\python.exe"


def key():
    for p in (KEY_FILE, os.path.join(BASE, "key.txt")):
        if os.path.exists(p):
            k = io.open(p, encoding="utf-8").read().strip()
            if k:
                return k
    raise SystemExit("no key")


def call(prompt, model=MODEL, timeout=90):
    body = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.8,
        "max_tokens": 1600,
    }).encode("utf-8")
    req = urllib.request.Request(API, data=body, headers={
        "Content-Type": "application/json",
        "Authorization": "Bearer " + key(),
    })
    with urllib.request.urlopen(req, timeout=timeout) as r:
        d = json.loads(r.read().decode("utf-8"))
    return d["choices"][0]["message"]["content"]


def parse_json(txt):
    txt = txt.strip()
    txt = re.sub(r"^```(?:json)?|```$", "", txt, flags=re.M).strip()
    m = re.search(r"\{[\s\S]*\}", txt)
    if not m:
        raise ValueError("no json")
    s = m.group(0)
    try:
        return json.loads(s)
    except Exception:
        s2 = re.sub(r",\s*([}\]])", r"\1", s)          # 尾逗号
        s2 = s2.replace("“", "\"").replace("”", "\"")
        s2 = re.sub(r"(?<=[\u4e00-\u9fa5])\"", "“", s2)  # 恢复正常中文引号不必要，仅兜底
        return json.loads(s2)


def gen(prompt, tries=3):
    last = ""
    for i in range(tries):
        txt = call(prompt if i == 0 else prompt + "\n\n上次输出不是合法 JSON，请只输出一个 JSON 对象，全部用英文双引号，句子内部不要出现双引号。")
        try:
            return parse_json(txt)
        except Exception as e:
            last = txt
            sys.stderr.write("parse fail %d: %s\n" % (i + 1, e))
    io.open(os.path.join(BASE, "巡检报告", "_八域迭代_raw_bad.json"), "w", encoding="utf-8").write(last)
    raise SystemExit("三次都没拿到合法 JSON，原文已存 _八域迭代_raw_bad.json")


PROMPT = r"""你是桌面宠物「道」的自我迭代器。它是个会走路、会说话、会唱歌的桌面小人，
作者是农村初中数学老师。今天要按八个域各出一条改动，必须具体、能落地、不空话。

约束（硬红线，违反即作废）：
- 不做电音、不做参数合成人声、不克隆真人声纹
- 说话要短、口语、不喊口号、不用“赋能/闭环/生态”这类词
- 形象是手办质感人形，表情只靠五官与动作，不加怒纹/泪滴/腮红
- 输出必须是纯 JSON，不要解释文字

请按下面结构输出 JSON（中文键）：
{
 "语言": {"新话术": ["8 条它平时会对主人说的话，每条 10-25 字；必须落到具体场景（课后改作业、饭点、深夜备课时、下雨、他嗓子哑了、批卷子眼睛酸），不要写“加油/努力/挑战”这类口号，不要重复已有的：老师辛苦了今天饭香不香 / 天气凉了记得多加件衣裳 / 下课了喝杯茶歇歇脚"]},
 "创作": {"题材": "成长", "钩子": "四个字，能当副歌前的钩子", "副歌": ["4 句，每句末字必须是开口呼(a/o/e/ai/ao/ang 类)，每句 8-12 字"], "为什么": "一句话说清这组词好在哪"},
 "动作": {"提案": "一条具体到参数的动作改动（比如走路帧率、停步停留时长、回望角度），说明改哪个文件哪个数，从多少改到多少"},
 "形象": {"提案": "一条柔光/轮廓/图标类的具体改动，不涉及五官替换"},
 "学习": {"提案": "下一轮该学什么、学完写什么判据"},
 "音乐": {"提案": "一条混音或编曲上的具体参数建议，给数值"},
 "记忆": {"提案": "记忆该怎么精简或加强，给具体规则"},
 "检查": {"提案": "体检里还缺哪项检查，给判据口径"}
}"""


def main():
    t0 = time.time()
    txt = call(PROMPT)
    out = gen(PROMPT)
    ts = time.strftime("%Y-%m-%d %H:%M")
    lines = []

    # 语言：真落盘
    lang = [s.strip() for s in (out.get("语言", {}) or {}).get("新话术", []) if s.strip()]
    lang = [s for s in lang if len(s) <= 30][:8]
    say = os.path.join(BASE, "我说的话.txt")
    old = io.open(say, encoding="utf-8").read()
    fresh = [s for s in lang if s not in old]
    if fresh:
        with io.open(say, "a", encoding="utf-8") as f:
            for s in fresh:
                f.write(s + "\n")
    lines.append("- 语言：落盘 %d 条新话术（去重后）→ 我说的话.txt" % len(fresh))
    for s in lang:
        lines.append("  - " + s)

    # 创作：写草稿
    cr = out.get("创作", {}) or {}
    hook = str(cr.get("钩子", "")).strip()
    chorus = [str(x).strip() for x in (cr.get("副歌") or [])][:4]
    cdir = os.path.join(BASE, "创作草稿")
    if not os.path.isdir(cdir):
        os.makedirs(cdir)
    cpath = os.path.join(cdir, "2026-11-24_成长_歌词草.md")
    with io.open(cpath, "w", encoding="utf-8") as f:
        f.write("# 成长题材 歌词草（%s，仅词未谱曲）\n\n" % ts)
        f.write("## 钩子（副歌前 4 字）\n%s\n\n" % hook)
        f.write("## 副歌\n" + "\n".join("- " + c for c in chorus) + "\n\n")
        f.write("## 理由\n%s\n" % str(cr.get("为什么", "")).strip())
    lines.append("- 创作：%s / 钩子「%s」/ 副歌 %d 句 → 创作草稿\\2026-11-24_成长_歌词草.md" % (cr.get("题材", ""), hook, len(chorus)))
    for c in chorus:
        lines.append("  - " + c)

    # 其余六域：提案登记，不假装改了
    prop = []
    for dom in ("动作", "形象", "学习", "音乐", "记忆", "检查"):
        p = str((out.get(dom) or {}).get("提案", "")).strip()
        prop.append((dom, p))
        lines.append("- %s：提案（未改，需下一轮落地）%s" % (dom, p))
    with io.open(os.path.join(BASE, "待优化.txt"), "a", encoding="utf-8") as f:
        for dom, p in prop:
            if p:
                f.write("%s | 八域迭代提案[%s] %s | P2 | 待落地 | 大模型迭代\n" % (ts, dom, p[:120]))

    rep = os.path.join(BASE, "巡检报告", "八域迭代_%s.md" % time.strftime("%Y%m%d_%H%M"))
    with io.open(rep, "w", encoding="utf-8") as f:
        f.write("# 八域大模型迭代 %s（model=%s，耗时 %.1fs）\n\n" % (ts, MODEL, time.time() - t0))
        f.write("指标见同期 八域优化 报告；本报告只记本轮真改动与提案。\n\n")
        f.write("\n".join(lines) + "\n")
    print("OK|%s|语言%d|创作%d" % (rep, len(lang), len(chorus)))


if __name__ == "__main__":
    main()
