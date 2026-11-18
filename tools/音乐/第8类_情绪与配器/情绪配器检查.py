# -*- coding: utf-8 -*-
"""情绪配器检查：拿一首歌的元数据，对照第 8 类学习里那张判据表，逐条判合格与否。

用法：
    python 情绪配器检查.py               # 跑内置样例（自检）
    python 情绪配器检查.py meta.json     # 判定一首歌，json 形如
        {"mood":"深夜思乡","bpm":70,"mode":"小调","has_solo":true,"has_fill":false,
         "intro_motif":true,"has_inst_section":false,"vocal_on_top":true}

设计原则：规则写死在这张表里（和 md 文档同源），不接外部库，纯标准库可跑。
不合格的项逐条打出，最后一行给 PASS/FAIL，方便巡检和写歌前卡口。
"""

import json
import sys

# (情绪, BPM 下限, 上限, 允许调式集合, 附加判据键)
RULES = [
    ("深夜思乡", 62, 78, {"小调", "Dorian"}, ["intro_motif"]),
    ("温情/亲情", 72, 92, {"大调", "混合利底亚"}, []),
    ("职场疲惫", 84, 100, {"小调"}, []),
    ("轻快打工", 104, 120, {"大调"}, ["has_fill"]),
    ("热血/动漫", 138, 168, {"小调"}, []),
    ("古风", 68, 88, {"五声"}, []),
    ("摇滚", 120, 150, {"小调"}, ["has_inst_section"]),
    ("说唱", 82, 96, {"小调"}, ["vocal_on_top"]),
]

REQUIRED = ["intro_motif", "has_fill", "has_inst_section", "vocal_on_top"]


def check(meta):
    mood = str(meta.get("mood", "")).strip()
    rule = next((r for r in RULES if r[0] == mood), None)
    if rule is None:
        return ["情绪「%s」不在判据表里，先补规则再写歌" % mood], 0
    _, lo, hi, modes, extra = rule
    problems = []
    bpm = meta.get("bpm")
    if not isinstance(bpm, (int, float)):
        problems.append("没填 bpm")
    elif not (lo <= bpm <= hi):
        problems.append("bpm=%s 不在 %d–%d" % (bpm, lo, hi))
    mode = str(meta.get("mode", "")).strip()
    if mode not in modes:
        problems.append("调式「%s」不属于 %s" % (mode, "、".join(sorted(modes))))
    for k in extra:
        if not meta.get(k):
            problems.append("缺少判据：%s" % k)
    # 通用：人声不能被鼓/低频盖住（说唱之外也同样适用）
    if meta.get("vocal_on_top") is False:
        problems.append("人声被伴奏盖住（vocal_on_top=false）")
    return problems, len(problems)


def demo():
    samples = [
        {"mood": "深夜思乡", "bpm": 70, "mode": "小调", "intro_motif": True, "vocal_on_top": True},
        {"mood": "轻快打工", "bpm": 98, "mode": "大调", "has_fill": False, "vocal_on_top": True},
        {"mood": "热血/动漫", "bpm": 152, "mode": "多利亚", "vocal_on_top": True},
    ]
    for s in samples:
        ps, n = check(s)
        print("[%s] %s bpm=%s mode=%s -> %s" % (
            s["mood"], s["mood"], s.get("bpm"), s.get("mode"),
            "PASS" if n == 0 else "FAIL"))
        for p in ps:
            print("   - " + p)


def main():
    if len(sys.argv) < 2:
        demo()
        return 0
    with open(sys.argv[1], encoding="utf-8") as f:
        meta = json.load(f)
    problems, n = check(meta)
    for p in problems:
        print("- " + p)
    print("PASS" if n == 0 else "FAIL")
    return 0 if n == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
