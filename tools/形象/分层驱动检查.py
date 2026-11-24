# -*- coding: utf-8 -*-
# 程序版本：v0.1 | 2026-11-24 | 第3类 Live2D/Spine 分层驱动与二次动作判据（新建）
"""分层驱动 + 二次动作判据（第3类 Live2D Cubism 摆锤 / Spine PhysicsConstraints 落地）

数据来源：F:\\Daodao\\src\\桌面分身\\pet.cs 里的骨架表与余摆参数。
判据（全部可算）：
  L1 骨链节点数 >= 5             —— 分层数量够，别一根正弦推整张图
  L2 头顶滞后 - 胯滞后 >= 1.0 rad —— 越靠上越晚，符合摆锤多段
  L3 幅值权重随高度单调不减      —— 越靠上叠得越多
  L4 Σ rigW 与 rigSum 偏差 <= 5% —— 归一化，防止摆幅超过 1 倍过冲
  L5 发尾滞后 - 头滞后 >= 0.5 rad —— 二次动作必须比主动骨再晚一档
  L6 余摆阻尼系数 ∈ [0.80,0.95] 且代码里有 0.02 的归零阈值 —— 停步后余摆两下再收，不硬停
"""
import io
import re
import sys

SRC = r"F:\Daodao\src\桌面分身\pet.cs"


def arr(text, name):
    m = re.search(name + r"\s*=\s*\{([^}]*)\}", text)
    if not m:
        raise SystemExit("找不到数组 " + name)
    return [float(x.replace("f", "").strip()) for x in m.group(1).split(",") if x.strip()]


def main():
    txt = io.open(SRC, encoding="utf-8").read()
    rigY, rigW, rigL = arr(txt, "rigY"), arr(txt, "rigW"), arr(txt, "rigL")
    m = re.search(r"rigSum\s*=\s*([0-9.]+)f", txt)
    rigSum = float(m.group(1)) if m else None
    m2 = re.search(r"SwayTailDamp\s*=\s*([0-9.]+)f", txt)
    damp = float(m2.group(1)) if m2 else None

    results = []

    def chk(code, ok, detail):
        results.append((code, bool(ok), detail))

    chk("L1 骨链节点数>=5", len(rigY) >= 5, "节点 %d 个" % len(rigY))
    lag = rigL[-1] - rigL[0]
    chk("L2 头顶滞后-胯滞后>=1.0rad", lag >= 1.0, "%.2f rad（%.0f→%.0f）" % (lag, rigL[0], rigL[-1]))
    mono = all(rigW[i + 1] >= rigW[i] for i in range(len(rigW) - 1))
    chk("L3 幅值随高度单调不减", mono, "权重 " + "/".join("%.2f" % w for w in rigW))
    if rigSum:
        calc = sum(rigW)
        err = abs(calc - rigSum) / rigSum
        chk("L4 归一化偏差<=5%", err <= 0.05, "算得 %.4f / 表里 %.2f，偏差 %.3f" % (calc, rigSum, err))
    else:
        chk("L4 归一化偏差<=5%", False, "没找到 rigSum")
    tail_lag = rigL[-1] - rigL[-2] if len(rigL) >= 2 else 0
    chk("L5 发尾-头滞后>=0.5rad", tail_lag >= 0.5, "%.2f rad" % tail_lag)
    has_floor = ("swayTailA < 0.02f" in txt) and ("swayTailA" in txt)
    ok6 = (damp is not None) and (0.80 <= damp <= 0.95) and has_floor
    chk("L6 余摆阻尼0.80-0.95且有归零阈值", ok6,
        "damp=%s 归零阈值=%s" % (damp, "有" if has_floor else "无"))

    for code, ok, detail in results:
        print(("PASS | " if ok else "FAIL | ") + code + " | " + detail)
    n_fail = sum(1 for _, ok, _ in results if not ok)
    print("汇总：%d 项判据 | 过 %d | 未过 %d | %s" % (len(results), len(results) - n_fail, n_fail,
                                                    "PASS" if n_fail == 0 else "FAIL"))
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
