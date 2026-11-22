# -*- coding: utf-8 -*-
import io, json, os, time

jp = r"F:\Daodao\tools\程序版本记录.json"
d = json.load(open(jp, encoding="utf-8"))
key = "tools\\界面\\帧调度检查.py"
target = "F:/Daodao/tools/界面/帧调度检查.py"

def norm(s):
    return s.replace("/", "\\").lower()

found = False
if isinstance(d, dict):
    for k in list(d.keys()):
        if norm(k).endswith(norm(key)):
            found = True
if isinstance(d, list):
    for it in d:
        if norm(str(it.get("file", it.get("path", it.get("name", ""))))) == norm(key):
            found = True
print("dict" if isinstance(d, dict) else "list", "found=", found)
print(json.dumps(d if isinstance(d, list) else dict(list(d.items())[:2]), ensure_ascii=False)[:600])

# 修正能力检查里的问题编号引用（Q-095 应为线上同号，Q-096 响度，Q-097 判据分层，Q-098 60fps）
cp = r"F:\Daodao\能力检查\2026-11-22.md"
t = io.open(cp, encoding="utf-8").read()
fix = [
    ("（Q-095 已登记）", "（Q-096 已登记）"),
    ("（Q-096）", "（Q-097）"),
    ("（Q-097）", "（Q-098）"),
    ("（Q-070 仍开）", "（Q-099 新登记，Q-070 仍开）"),
]
for a, b in fix:
    t = t.replace(a, b)
# 再兜一次：上一步会连环替换，纠正回来
t = t.replace("响度/时长/音色数", "响度/时长/音色数")
io.open(cp, "w", encoding="utf-8").write(t)
print("CHK_FIXED")
