# -*- coding: utf-8 -*-
# 程序版本：v0.1 | 2026-11-25 | 第4类落地判据：走路步频/摆幅改阻尼弹簧后，曲线是否真按 Flutter 那套收敛
"""动效曲线判据（第4类 Flutter 动画曲线与内插）

判据来源：
  https://api.flutter.dev/flutter/physics/SpringSimulation-class.html   （SpringSimulation / SpringDescription）
  https://docs.flutter.dev/release/breaking-changes/spring-description-underdamped （欠阻尼公式）
  https://m3.material.io/styles/motion/easing-and-duration              （Standard/Emphasized 时长配对）
  https://api.flutter.dev/flutter/animation/Curves-class.html           （easeOutCubic 定义）

判据（与 pet.cs 里 SpringStep 同一套积分，子步 8ms）：
  F1 起步 90% 收敛时间 ∈ [0.18, 0.45] s
  F2 过冲 ≤ 3%（ζ=0.85 理论过冲 e^(-ζπ/√(1-ζ²))≈1.6%）
  F3 停步 90% 收敛时间 ≤ 0.45 s
  F4 阻尼比落在 [0.60, 0.90]，且 pet.cs 里写的 ω/ζ 与判据一致
  F5 摆幅弹簧：开步 0.15s ≥ 目标 60%，停步 0.35s 回到 ≤1.2
  F6 源码里 SpringStep 调用 ≥2 处（步频 + 摆幅）
"""
import re, sys, math

PET = r"F:\Daodao\src\桌面分身\pet.cs"
OMEGA_FPS, ZETA_FPS = 13.4, 0.85
OMEGA_AMP, ZETA_AMP = 16.0, 0.80
DT = 1.0 / 60.0


def spring(x, v, target, dt, omega, zeta):
    if dt <= 0:
        return x, v
    dt = min(dt, 0.1)
    n = max(1, math.ceil(dt / 0.008))
    h = dt / n
    for _ in range(n):
        a = omega * omega * (target - x) - 2 * zeta * omega * v
        v += a * h
        x += v * h
    return x, v


def settle_time(x0, target, omega, zeta, frac=0.9, tmax=2.0):
    x, v, t = x0, 0.0, 0.0
    span = abs(target - x0)
    peak = x0
    t90 = None
    while t < tmax:
        x, v = spring(x, v, target, DT, omega, zeta)
        t += DT
        if abs(x - x0) > abs(peak - x0):
            peak = x
        if t90 is None and span > 1e-6 and abs(x - x0) / span >= frac:
            t90 = t
    overshoot = abs(peak - target) / span * 100 if span > 1e-6 else 0.0
    return t90, overshoot, t


def main():
    src = open(PET, encoding="utf-8", errors="replace").read()
    fails = 0

    # F1 起步：8.5 → 20 fps
    t90, ov, _ = settle_time(8.5, 20.0, OMEGA_FPS, ZETA_FPS)
    ok = t90 is not None and 0.18 <= t90 <= 0.45
    print("%s | F1 起步90%%收敛 ∈[0.18,0.45]s | %.3fs" % ("PASS" if ok else "FAIL", t90 or -1))
    if not ok: fails += 1

    # F2 过冲
    ok = ov <= 3.0
    print("%s | F2 过冲 ≤3%% | %.2f%%" % ("PASS" if ok else "FAIL", ov))
    if not ok: fails += 1

    # F3 停步：20 → 8.5
    t90s, ovs, _ = settle_time(20.0, 8.5, OMEGA_FPS, ZETA_FPS)
    ok = t90s is not None and t90s <= 0.45
    print("%s | F3 停步90%%收敛 ≤0.45s | %.3fs" % ("PASS" if ok else "FAIL", t90s or -1))
    if not ok: fails += 1

    # F4 阻尼比 + 源码数值一致
    zok = 0.60 <= ZETA_FPS <= 0.90 and 0.60 <= ZETA_AMP <= 0.90
    has_num = ("13.4f, 0.85f" in src) and ("16f, 0.8f" in src)
    ok = zok and has_num
    print("%s | F4 阻尼比∈[0.60,0.90] 且源码同值 | fps ζ=%.2f amp ζ=%.2f 源码数值=%s"
          % ("PASS" if ok else "FAIL", ZETA_FPS, ZETA_AMP, has_num))
    if not ok: fails += 1

    # F5 摆幅弹簧：0.8 → 4.6 开步 0.15s 到 60%；4.6 → 0.8 停步 0.35s 回到 ≤1.2
    x, v = 0.8, 0.0
    n = int(0.15 / DT)
    for _ in range(n):
        x, v = spring(x, v, 4.6, DT, OMEGA_AMP, ZETA_AMP)
    speed_val = x
    speed_ok = x >= 0.8 + 0.6 * (4.6 - 0.8)
    x, v = 4.6, 0.0
    n = int(0.35 / DT)
    for _ in range(n):
        x, v = spring(x, v, 0.8, DT, OMEGA_AMP, ZETA_AMP)
    stop_val = x
    stop_ok = x <= 1.2
    ok = speed_ok and stop_ok
    print("%s | F5 摆幅弹簧 开步0.15s≥60%%(≥3.08) / 停步0.35s≤1.2 | %.2f / %.2f"
          % ("PASS" if ok else "FAIL", speed_val, stop_val))
    if not ok: fails += 1

    # F6 调用点数量
    calls = len(re.findall(r"SpringStep\(", src)) - 1  # 减掉函数定义
    ok = calls >= 2
    print("%s | F6 SpringStep 调用 ≥2 处 | %d 处" % ("PASS" if ok else "FAIL", calls))
    if not ok: fails += 1

    print("汇总：6 项判据 | 过 %d | 未过 %d | %s" % (6 - fails, fails, "PASS" if fails == 0 else "FAIL"))
    return 0 if fails == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
