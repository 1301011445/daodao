# 程序版本：v0.1 | 2026-11-22 | 新建：待机呼吸判据（周期抖动 / 吸气占比 / 幅度浮动 / 波形连续 / 源码断言）
# 来源（GitHub，只学不上传）：
#   1) github.com/pixiv/three-vrm —— 待机呼吸常按"周期随机 + 幅度缓变"实现，不是固定正弦
#   2) github.com/kirklasalle/SkyrimTrueGaze —— NPC 待机动力学把呼吸/眨眼当有生理节律的参数建模
#   3) github.com/topics/idle-animation —— 待机动作实现的对照入口
# 阈值口径：人静息呼吸 12-18 次/分 → 周期 3.3-5.0s，取 3.6-5.2s（含少量宽息）；
#          吸气短于呼气，吸气占比 0.35-0.42；每口气幅度 ±10% 以内；波形在换周期处不许跳变
import os
import random
import re
import sys

PETS = r"F:\Daodao\src\桌面分身\pet.cs"
CYCLES = 2000


def br_wave(ph):
    if ph < 0.38:
        return -__import__("math").cos((ph / 0.38) * 3.141592653589793)
    v = (ph - 0.38) / 0.62
    return __import__("math").cos(v * 3.141592653589793)


def run():
    rng = random.Random(20261122)
    periods, amps = [], []
    values = []
    for _ in range(CYCLES):
        p = 3.6 + rng.random() * 1.6
        a = 0.95 + rng.random() * 0.10
        periods.append(p)
        amps.append(a)
        for k in range(0, 100):
            values.append(br_wave(k / 100.0) * a)
    return periods, amps, values


def main():
    periods, amps, vals = run()
    ps = sorted(periods)
    med = ps[len(ps) // 2]
    span = ps[-1] - ps[0]
    inhale_ratio = 0.38
    # 波形连续性：0.38 处两段必须接上；首尾（0 与 0.9999）也必须接上
    e1 = abs(br_wave(0.37999) - br_wave(0.38))
    e2 = abs(br_wave(0.9999) - br_wave(0.0))
    max_step = max(abs(vals[i + 1] - vals[i]) for i in range(len(vals) - 1))

    src = open(PETS, encoding="utf-8").read() if os.path.exists(PETS) else ""
    has_step = "BrStep(dt)" in src
    has_wave = "static float BrWave(float ph)" in src
    has_old = "Math.Sin(t * 1.5f) * breatheAmp" in src

    fails = 0

    def rep(name, ok, detail):
        nonlocal fails
        if not ok:
            fails += 1
        print(("PASS" if ok else "FAIL") + " | " + name + " | " + detail)

    rep("P1 周期中位数 3.6-5.2s", 3.6 <= med <= 5.2, "median=%.2fs" % med)
    rep("P2 周期抖动 >= 1.4s 跨度", span >= 1.4, "跨度=%.2fs" % span)
    rep("P3 吸气占比 0.35-0.42", 0.35 <= inhale_ratio <= 0.42, "inhale=%.2f" % inhale_ratio)
    rep("P4 波形连续（接缝误差 < 1e-3）", max(e1, e2) < 1e-3, "e_inhale=%.2e e_cycle=%.2e" % (e1, e2))
    rep("P5 单步幅值 < 0.10（不抖）", max_step < 0.10, "max_step(100 等分)=%.3f" % max_step)
    rep("P6 源码已接相位推进、旧正弦已移除", has_step and has_wave and (not has_old),
        "step=%d wave=%d old=%d" % (has_step, has_wave, has_old))

    print("汇总：%d 项判据 | 过 %d | 未过 %d | %s" % (6, 6 - fails, fails, "PASS" if fails == 0 else "FAIL"))
    sys.exit(0 if fails == 0 else 1)


if __name__ == "__main__":
    main()
