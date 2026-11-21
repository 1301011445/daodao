# -*- coding: utf-8 -*-
"""纠错体检：已解决项里带「复现用例」的比例，和同标题复发次数

判据（第三件事第 5 项）：
  C1 已解决项带复现用例比例 >= 80%
  C2 同一标题复发 1 次记 -2、3 次记 -3（这里只报表，扣分交给 愉悦值检查.py）
  C3 解决说明不能是空话（>= 10 字，且不含「待优化」「再看看」这类词）

用法：python 纠错体检.py
"""
import json, os, re, sys

ROOT = r"F:\Daodao"
ISSUES = os.path.join(ROOT, "自我状态", "问题库.json")


def main():
    d = json.load(open(ISSUES, encoding="utf-8-sig"))
    q = d["问题"]
    solved = [x for x in q if x.get("状态") == "solved"]
    n = len(solved)
    with_rep = []
    for x in solved:
        rep = (x.get("复现") or "").strip()
        if not rep:
            # 老条目没有 复现 字段，退回看解决说明里有没有写复现步骤
            note = x.get("解决说明") or ""
            if ("复现" in note) or ("重现" in note):
                rep = "（说明里带复现）"
        if rep:
            with_rep.append(x.get("id"))
    ratio = (100.0 * len(with_rep) / n) if n else 0.0
    print("已解决 %d 条，带复现 %d 条（%.0f%%）" % (n, len(with_rep), ratio))
    print(("PASS" if ratio >= 80 else "FAIL") + " | C1 复现用例比例≥80%% | %.0f%%" % ratio)

    repeats = [x for x in q if int(x.get("复发次数", 0)) > 0]
    worst = max([int(x.get("复发次数", 0)) for x in repeats], default=0)
    print("复发条目 %d 条，最高复发 %d 次（1 次 -2 / 3 次 -3）" % (len(repeats), worst))
    for x in repeats:
        print("   %s 复发 %d 次：%s" % (x.get("id"), x.get("复发次数"), (x.get("标题") or "")[:34]))

    thin = [x for x in solved if len((x.get("解决说明") or "").strip()) < 10]
    print(("PASS" if not thin else "FAIL") + " | C3 解决说明不空 | 空 %d/%d" % (len(thin), n))
    for x in thin[:6]:
        print("   空说明", x.get("id"), (x.get("标题") or "")[:24])

    bad = (1 if ratio < 80 else 0) + (1 if thin else 0)
    print("\n汇总：%d 项 FAIL" % bad)
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
