# -*- coding: utf-8 -*-
"""学习复现日历：按 1/3/7/21 天把学过的类别排进复现日，并核对有没有真复现过

数据来源：
  F:\\Daodao\\学习台账.txt      —— 每条以 [日期] 开头，正文里带「第N类」
  F:\\Daodao\\学习复现台账.txt  —— 复现记录，一行一条：日期|第N类|跑过的脚本|结论

判据：
  R1 每个已学类别都有首次学习日期（台账能解析出日期）
  R2 今天的到期项全部有复现记录（缺一条就是 FAIL）
  R3 复现记录里的脚本路径真实存在
  R4 复现间隔不早于应到日（提前跑不算）
"""
import os, re, sys, datetime

LEDGER = r"F:\Daodao\学习台账.txt"
RECORD = r"F:\Daodao\学习复现台账.txt"
TODAY = datetime.date.today()
OFFSETS = [1, 3, 7, 21]

def parse_ledger():
    text = open(LEDGER, encoding="utf-8").read()
    first = {}
    for m in re.finditer(r"\[(\d{4}-\d{2}-\d{2})[^\]]*\][^\n]*第(\d+)类", text):
        d = datetime.date.fromisoformat(m.group(1))
        n = int(m.group(2))
        if n not in first or d < first[n]:
            first[n] = d
    return first

def parse_record():
    rows = []
    if os.path.exists(RECORD):
        for line in open(RECORD, encoding="utf-8"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("|")
            if len(parts) >= 3:
                try:
                    rows.append((datetime.date.fromisoformat(parts[0].strip()),
                                 int(re.sub(r"[^0-9]", "", parts[1])) , parts[2].strip()))
                except Exception:
                    pass
    return rows

def main():
    first = parse_ledger()
    recs = parse_record()
    print("已学类别 %d 个：%s" % (len(first), ",".join(str(k) for k in sorted(first))))
    fails = 0

    # R1
    if first:
        print("PASS | R1 每类有首次学习日期 | %d/%d" % (len(first), len(first)))
    else:
        print("FAIL | R1 台账解析不出类别")
        fails += 1

    # 到期表（只算今天及以前最近 1 天窗口，避免把陈年到期项都翻出来）
    due = []
    for n, d in sorted(first.items()):
        for off in OFFSETS:
            dd = d + datetime.timedelta(days=off)
            if TODAY - datetime.timedelta(days=3) <= dd <= TODAY:
                due.append((dd, n, off))
    due.sort()
    print("\n今天到期（含前 3 天补做窗口）：%d 项" % len(due))
    missing = []
    for dd, n, off in due:
        hit = [r for r in recs if r[0] >= dd and r[1] == n]
        state = "已复现(%s)" % hit[0][0] if hit else "没复现"
        print("  %s 第%d类 +%d天  %s" % (dd.isoformat(), n, off, state))
        if not hit:
            missing.append((dd, n, off))

    # R2
    if not missing:
        print("PASS | R2 到期项全部复现 | 缺 0")
    else:
        print("FAIL | R2 到期项全部复现 | 缺 %d：%s" % (len(missing), ",".join("第%d类+%d" % (n, off) for _, n, off in missing)))
        fails += 1

    # R3
    bad = [r for r in recs if r[2] and not os.path.exists(r[2])]
    print(("PASS" if not bad else "FAIL") + " | R3 复现脚本存在 | 坏 %d/%d" % (len(bad), len(recs)))
    if bad:
        fails += 1
        for r in bad:
            print("    缺文件", r[2])

    # R4
    early = []
    for r in recs:
        d0 = first.get(r[1])
        if not d0:
            continue
        if (r[0] - d0).days not in OFFSETS:
            early.append(r)
    print(("PASS" if not early else "FAIL") + " | R4 复现落在 1/3/7/21 天 | 越界 %d" % len(early))
    if early:
        fails += 1

    print("\n汇总：%d 项 FAIL" % fails)
    return 0 if fails == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
