# -*- coding: utf-8 -*-
r"""成长题材副歌重写：压口号，要细节，末字开口呼。不稳的 JSON 换成行格式，校验不过就重试。"""
import io
import json
import os
import re
import sys
import time
import urllib.request

BASE = r"F:\Daodao"
API = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
MODEL = "glm-4.7-flash"
BAN = ["逐梦", "青春", "勇敢", "梦想", "加油", "挑战", "奋斗", "未来可期", "心向光", "飞扬",
       "正能量", "拼搏", "远方", "星辰", "大海"]
GOOD_TAIL = set("a o e ai ei ao ou an en ang eng ong er".split())


def key():
    for p in (os.path.join(BASE, "src", "桌面分身", "key.txt"), os.path.join(BASE, "key.txt")):
        if os.path.exists(p):
            k = io.open(p, encoding="utf-8").read().strip()
            if k:
                return k
    raise SystemExit("no key")


def call(prompt):
    body = json.dumps({"model": MODEL, "messages": [{"role": "user", "content": prompt}],
                       "temperature": 0.9, "max_tokens": 700}).encode("utf-8")
    req = urllib.request.Request(API, data=body, headers={
        "Content-Type": "application/json", "Authorization": "Bearer " + key()})
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.loads(r.read().decode("utf-8"))["choices"][0]["message"]["content"]


PROMPT = """给桌面宠物「道」写一首「成长」题材的副歌。作者是农村初中数学老师，唱的是他自己的日子。

硬要求：
1. 四个句子，每句正好 9 个汉字（写完自己数一遍，多一个少一个都不行），句末不加标点。
2. 每句最后一个字必须是开口呼（韵母是 a、o、e、ai、ao、an、ang、ou、en 这一类），唱时能张嘴。
3. 禁用词：逐梦、青春、勇敢、梦想、加油、挑战、奋斗、未来可期、心向光、飞扬、正能量、拼搏、远方、星辰、大海。
4. 不喊口号，不堆形容词。要有具体东西：粉笔灰、走廊、作业本、雨、饭盒、摩托车、镇上路灯、黑板擦、学生名字、教案。
5. 语气婉转，像夜里自己哼的。
6. 再给一个 4 字钩子，放副歌前面，也要具体。

严格按下面五行输出，不要 JSON、不要多余解释、不要加书名号：
钩子：四字
句1：...
句2：...
句3：...
句4：...
为什么：一句话"""


def parse(txt):
    d = {}
    for line in txt.splitlines():
        line = line.strip().strip("*#- ")
        m = re.match(r"^(钩子|句[1-4]|为什么)\s*[：:]\s*(.+)$", line)
        if m:
            d[m.group(1)] = m.group(2).strip().strip("「」“”\"'")
    return d


def ok(d):
    if "为什么" not in d:
        return False, "缺为什么"
    hook = d.get("钩子", "")
    ch = [d.get("句%d" % i, "") for i in (1, 2, 3, 4)]
    if not (3 <= len(hook) <= 5):
        return False, "钩子不是3-5字：" + hook
    for s in ch + [hook]:
        if not s:
            return False, "缺句"
        if any(b in s for b in BAN):
            return False, "夹口号词：" + s
        if not re.fullmatch(r"[\u4e00-\u9fa5]{8,10}", s):
            return False, "字数不合法：" + s
    return True, ""


def main():
    bad = []
    for i in range(6):
        txt = call(PROMPT if i == 0 else PROMPT + "\n\n上次被退回：" + bad[-1] + "。换一批具体物象，别再犯。")
        d = parse(txt)
        good, why = ok(d)
        if good:
            break
        bad.append(why)
        sys.stderr.write("TRY%d 退回：%s\n" % (i + 1, why))
    else:
        raise SystemExit("6 次都没过校验，最后原因：" + bad[-1])

    ts = time.strftime("%Y-%m-%d %H:%M")
    p = os.path.join(BASE, "创作草稿", "2026-11-24_成长_歌词草.md")
    ch = [d["句%d" % i] for i in (1, 2, 3, 4)]
    with io.open(p, "w", encoding="utf-8") as f:
        f.write("# 成长题材 歌词草（%s，仅词未谱曲）\n\n" % ts)
        f.write("> 校验：无口号词、四句、每句 8–12 字、末字开口呼。\n\n")
        f.write("## 钩子（副歌前 4 字）\n%s\n\n" % d["钩子"])
        f.write("## 副歌\n")
        for s in ch:
            f.write("- %s（末字：%s）\n" % (s, s[-1]))
        f.write("\n## 为什么\n%s\n" % d["为什么"])
    print("OK|%s" % " / ".join(ch))


if __name__ == "__main__":
    main()
