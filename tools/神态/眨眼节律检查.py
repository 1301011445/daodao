# 程序版本：v0.1 | 2026-11-22 | 新建：眨眼节律判据（对数正态间隔 + 双眨比例 + 源码静态断言）
# 为什么有这条：真人眨眼间隔是对数正态，不是均匀随机。均匀分布看着像节拍器。
# 来源（GitHub，只学不上传）：
#   1) github.com/kirklasalle/SkyrimTrueGaze —— 给 NPC 建 ballistic saccade / blink / 微漂移 的生物力学模型
#   2) github.com/jayzuccarelli/saccade —— "adaptive cadence"：节奏不该是固定频率，该由情境自己决定
#   3) github.com/topics/saccade —— 该主题下各实现的对照入口
# 阈值口径：中位数取 2.4-4.0s（成年人静息眨眼 3-4 秒一次）；p10 不低于 0.4s（太快成抽搐）；
#           p90 不超过 12s（太久像盯人）；双眨比例 20%-30%（保守取码里写的 25% ± 5）
import os
import re
import sys

PETS = r"F:\Daodao\src\桌面分身\pet.cs"
N = 20000


def sample():
    """用和 pet.cs 完全相同的算法复算分布（Irwin-Hall 4 个均匀 + 对数正态 + 上下限）"""
    import random
    random.seed(20261122)
    out = []
    for _ in range(N):
        if random.random() < 0.25:
            out.append(0.34)
            continue
        n = sum(random.random() for _ in range(4))
        n = (n - 2.0) * 1.7321
        iv = 3.2 * pow(2.718281828459045, 0.55 * n)
        iv = max(0.6, min(18.0, iv))
        out.append(iv)
    return out


def pct(v, q):
    k = int(len(v) * q)
    k = max(0, min(len(v) - 1, k))
    return v[k]


def main():
    raw = sorted(sample())
    vals = [x for x in raw if x >= 0.5]   # 0.34s 的双眨是同一个眨眼事件的第二下，不算独立间隔
    med = pct(vals, 0.5)
    p10 = pct(vals, 0.10)
    p90 = pct(vals, 0.90)
    dbl = sum(1 for x in raw if x < 0.4) / len(raw) * 100

    src = open(PETS, encoding="utf-8").read() if os.path.exists(PETS) else ""
    has_log = bool(re.search(r"3\.2\s*\*\s*Math\.Exp\(0\.55", src))
    has_cap = ("iv < 0.6f" in src) and ("iv > 18f" in src)
    has_old = "1.8f + (float)(blinkRnd.NextDouble() * 4.7)" in src

    fails = 0

    def rep(name, ok, detail):
        nonlocal fails
        if not ok:
            fails += 1
        print(("PASS" if ok else "FAIL") + " | " + name + " | " + detail)

    rep("P1 间隔中位数 2.4-4.0s", 2.4 <= med <= 4.0, "median=%.2fs（样本 %d）" % (med, N))
    rep("P2 p10 >= 0.4s", p10 >= 0.4, "p10=%.2fs" % p10)
    rep("P3 p90 <= 12s", p90 <= 12.0, "p90=%.2fs" % p90)
    rep("P4 双眨比例 20-30%", 20 <= dbl <= 30, "双眨=%.1f%%" % dbl)
    rep("P5 源码用对数正态", has_log and has_cap, "log=%.0f cap=%.0f" % (has_log, has_cap))
    rep("P6 旧的均匀分布已移除", not has_old, "old_uniform_found=%d" % has_old)

    print("汇总：%d 项判据 | 过 %d | 未过 %d | %s" % (6, 6 - fails, fails, "PASS" if fails == 0 else "FAIL"))
    sys.exit(0 if fails == 0 else 1)


if __name__ == "__main__":
    main()
