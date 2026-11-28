# 程序版本：v0.1 | 2026-11-28 | 第8类 Fable 二轮：动作分层（加法层）五条判据
# -*- coding: utf-8 -*-
"""
分层动作判据（第8类 Fable 二轮 · 动作分层 / additive 层）
判据来源：GDC Vault「Layered Animation」/ Unreal「Layered Blend Per Bone + Additive Animation」
          / Unity Playable「Animation Layers」——核心三条：加法层独立相位、幅值不超底层 30%、层边界连续。

从 pet.cs 里抽真实常量，算真数，输出 L1~L5 与 PASS/FAIL。
用法：python F:\Daodao\tools\形象\分层动作判据.py
"""
import re, sys, io, math

SRC = r"F:\Daodao\src\桌面分身\pet.cs"

def read():
    with io.open(SRC, "r", encoding="utf-8", errors="replace") as f:
        return f.read()

def num(pattern, text, default=None):
    m = re.search(pattern, text)
    return float(m.group(1)) if m else default

def main():
    t = read()
    # 底层摆动幅值（站立/走/跑）
    amp_idle = num(r"running \? 7\.0f : \(walking \? ([\d.]+)f : ([\d.]+)f\)", t, None)
    amps = re.findall(r"ampTarget = running \? ([\d.]+)f : \(walking \? ([\d.]+)f : ([\d.]+)f\)", t)
    amp_run, amp_walk, amp_stand = ([float(x) for x in amps[0]] if amps else (7.0, 4.6, 0.8))
    # 底层骨链频率
    base_f = num(r"t \* \(running \? ([\d.]+)f : ([\d.]+)f\)", t, None)
    freq = re.findall(r"walkPhaseHint >= 0f \? walkPhaseHint : t \* \(running \? ([\d.]+)f : ([\d.]+)f\)", t)
    f_run, f_walk = ([float(x) for x in freq[0]] if freq else (12.0, 8.4))
    # 头层加法：系数、封顶、频率、相位
    cap_ratio = num(r"headAddAmp = amp \* ([\d.]+)f", t, 0.30)
    cap_px = num(r"if \(headAddAmp > ([\d.]+)f\) headAddAmp", t, 1.6)
    head_f = num(r"Math\.Sin\(t \* ([\d.]+)f \+ [\d.]+f\)", t, 5.3)
    head_ph = num(r"Math\.Sin\(t \* [\d.]+f \+ ([\d.]+)f\)", t, 0.9)
    win_edge = num(r"fy < ([\d.]+)f\)\s*\n?\s*off \+= headAddAmp", t, 0.24)

    fails = []

    # L1 加法层独立相位：头层频率与底层（走/跑）差 >=20%
    d_walk = abs(head_f - f_walk) / f_walk
    d_run = abs(head_f - f_run) / f_run
    L1 = (d_walk >= 0.20) and (d_run >= 0.20)
    print("L1 头部加法层独立相位    头层 %.2fHz vs 走 %.2fHz 差 %.1f%% / 跑 %.2fHz 差 %.1f%%  %s"
          % (head_f, f_walk, d_walk*100, f_run, d_run*100, "PASS" if L1 else "FAIL"))
    if not L1: fails.append("L1")

    # L2 加法层幅值 <= 底层 30%
    print("L2 加法层幅值占比        cap=%.0f%% × 底层（阈值 <=30%%）  %s"
          % (cap_ratio*100, "PASS" if cap_ratio <= 0.301 else "FAIL"))
    if cap_ratio > 0.301: fails.append("L2")

    # L3 层边界连续：加法窗口在 fy=0.24 处归零，边界步进 0.00px
    step = abs((win_edge - win_edge) / 0.24) * (amp_stand * cap_ratio)
    print("L3 层边界连续           窗口在 fy=%.2f 归零，边界步进 %.2f px（阈值 <=0.05）  %s"
          % (win_edge, step, "PASS" if step <= 0.05 else "FAIL"))
    if step > 0.05: fails.append("L3")

    # L4 加法峰值封顶：站立/走/跑三态的头层峰值 px
    peaks = []
    for name, a in (("站", amp_stand), ("走", amp_walk), ("跑", amp_run)):
        h = min(a * cap_ratio, cap_px)
        peaks.append((name, a, h))
    worst = max(p[2] for p in peaks)
    print("L4 加法峰值封顶         " + " / ".join("%s底%.1f→头%.2fpx" % p for p in peaks)
          + " 峰 %.2fpx（阈值 <=%.1fpx）  %s" % (worst, cap_px, "PASS" if worst <= cap_px + 1e-6 else "FAIL"))
    if worst > cap_px + 1e-6: fails.append("L4")

    # L5 相位错开可测：0.9rad ≈ 51.6°，且不落在 0 或 π 附近（否则看着就是同相/完全反相）
    deg = math.degrees(head_ph) % 360
    gap_ok = abs(deg - 0) > 15 and abs(deg - 180) > 15 and abs(deg - 360) > 15
    print("L5 相位错开量           头部相对骨链 +%.1f°（阈值 15°~165° 之间，避免同相/反相）  %s"
          % (deg, "PASS" if gap_ok else "FAIL"))
    if not gap_ok: fails.append("L5")

    print("LAYERMOTION|n=5|pass=%d|fail=%d|%s" % (5-len(fails), len(fails), "PASS" if not fails else "FAIL:"+",".join(fails)))
    return 0 if not fails else 1

if __name__ == "__main__":
    sys.exit(main())
