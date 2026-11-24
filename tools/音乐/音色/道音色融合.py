# -*- coding: utf-8 -*-
"""道音色融合后处理：在神经声库底子上，加「道」自己的音色特征。
只做线性/缓变处理（EQ、动态、归一），不使用任何音高量化、金属化、镶边类效果，
所以不会引入电音味。参数与理由见 音色总结.md「七、道自己的音色」。
"""
import os
import sys
import io
import json
import numpy as np
import soundfile as sf

sys.path.insert(0, r"F:\Daodao\tools\语音")


def _biquad(x, sr, kind, f0, gain_db=0.0, q=0.7071):
    w0 = 2.0 * np.pi * f0 / sr
    cw, sw = np.cos(w0), np.sin(w0)
    alpha = sw / (2.0 * q)
    A = 10 ** (gain_db / 40.0)
    if kind == "lowshelf":
        b0 = A * ((A + 1) - (A - 1) * cw + 2 * np.sqrt(A) * alpha)
        b1 = 2 * A * ((A - 1) - (A + 1) * cw)
        b2 = A * ((A + 1) - (A - 1) * cw - 2 * np.sqrt(A) * alpha)
        a0 = (A + 1) + (A - 1) * cw + 2 * np.sqrt(A) * alpha
        a1 = -2 * ((A - 1) + (A + 1) * cw)
        a2 = (A + 1) + (A - 1) * cw - 2 * np.sqrt(A) * alpha
    elif kind == "highshelf":
        b0 = A * ((A + 1) + (A - 1) * cw + 2 * np.sqrt(A) * alpha)
        b1 = -2 * A * ((A - 1) + (A + 1) * cw)
        b2 = A * ((A + 1) + (A - 1) * cw - 2 * np.sqrt(A) * alpha)
        a0 = (A + 1) - (A - 1) * cw + 2 * np.sqrt(A) * alpha
        a1 = 2 * ((A - 1) - (A + 1) * cw)
        a2 = (A + 1) - (A - 1) * cw - 2 * np.sqrt(A) * alpha
    elif kind == "peaking":
        b0 = 1 + alpha * A
        b1 = -2 * cw
        b2 = 1 - alpha * A
        a0 = 1 + alpha / A
        a1 = -2 * cw
        a2 = 1 - alpha / A
    else:  # highpass
        b0 = (1 + cw) / 2.0
        b1 = -(1 + cw)
        b2 = (1 + cw) / 2.0
        a0 = 1 + alpha
        a1 = -2 * cw
        a2 = 1 - alpha
    b = np.array([b0, b1, b2]) / a0
    a = np.array([1.0, a1 / a0, a2 / a0])
    return b, a


CHAINS = {
    "v1": [
        ("highpass", 90.0, 0.0, 0.7071),      # 去掉次声轰鸣
        ("lowshelf", 230.0, 1.2, 0.70),       # 胸腔共鸣 +1.2dB，补「有厚度但不闷」
        ("peaking", 620.0, -0.8, 1.0),        # 收掉童声鼻音共鸣
        ("highshelf", 3200.0, -0.9, 0.7071),  # 去锯齿/去毛刺，压电音感
        ("peaking", 4500.0, -0.8, 0.9),       # 齿音收敛
        ("highshelf", 9000.0, -0.6, 0.7071),  # 高频柔化，避免合成感发亮
    ],
    # v2（2026-11-24 用户「音色全换」后）：更暗、更厚、少亮少细
    "v2": [
        ("highpass", 80.0, 0.0, 0.7071),
        ("lowshelf", 160.0, 2.0, 0.60),       # 胸声再往下托，补低频厚度
        ("lowshelf", 300.0, 1.0, 0.70),
        ("peaking", 900.0, -1.5, 0.80),       # 收箱音/鼻音，去「细嗓子」
        ("peaking", 2600.0, -1.0, 0.90),      # 压中高频的刺
        ("highshelf", 5000.0, -2.0, 0.7071),  # 砍亮：这是「听起来不像人」的主因
        ("highshelf", 11000.0, -1.2, 0.7071),
    ],
}


def apply_eq(x, sr, chain_name="v1"):
    """道自己的音色链：胸声托底、齿音收敛、气声保留但不糊。"""
    chain = CHAINS.get(chain_name, CHAINS["v1"])
    y = x.astype(np.float64)
    for kind, f, g, q in chain:
        b, a = _biquad(y, sr, kind, f, g, q)
        # 直接 II 型转置，逐样本（长度约 8M，可接受）
        y = _lfilter(b, a, y)
    return y


def _lfilter(b, a, x):
    n = len(x)
    y = np.empty(n, dtype=np.float64)
    x1 = x2 = y1 = y2 = 0.0
    b0, b1, b2 = b
    a1, a2 = a[1], a[2]
    for i in range(n):
        xi = x[i]
        yi = b0 * xi + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2
        x2, x1 = x1, xi
        y2, y1 = y1, yi
        y[i] = yi
    return y


def soft_deess(x, sr):
    """轻度动态高频收敛：只在瞬态尖峰时压，不整体变闷。"""
    # 一阶差分近似高频能量，10ms 窗口包络
    d = np.diff(x, prepend=x[0])
    win = int(sr * 0.010)
    env = np.abs(d)
    k = np.ones(win) / win
    sm = np.convolve(env, k, mode="same")
    thr = np.percentile(sm, 92) * 0.9 + 1e-9
    g = np.ones_like(sm)
    hi = sm > thr
    g[hi] = (thr / sm[hi]) ** 0.35
    g = np.convolve(g, k, mode="same")
    return x * g


def metrics(x, sr):
    x = x.astype(np.float64)
    peak = float(np.max(np.abs(x)))
    rms = float(np.sqrt(np.mean(x ** 2)) + 1e-12)
    # 频谱重心
    n = min(len(x), 1 << 18)
    seg = x[:n]
    spec = np.abs(np.fft.rfft(seg * np.hanning(n)))
    freqs = np.fft.rfftfreq(n, 1.0 / sr)
    cen = float((spec * freqs).sum() / (spec.sum() + 1e-12))
    # 谐波/非谐波能量比（气声越多越低）
    f0 = 0
    try:
        # 自相关估基频
        seg2 = x[int(0.2 * sr):int(0.2 * sr) + 4096]
        ac = np.correlate(seg2, seg2, "full")[len(seg2) - 1:]
        lo, hi = int(sr / 800), int(sr / 80)
        lag = lo + int(np.argmax(ac[lo:hi]))
        f0 = sr / lag
    except Exception:
        pass
    harm = 0.0
    total = float(np.sum(spec ** 2))
    if f0 > 60:
        for k in range(1, 12):
            idx = int(round(k * f0 / (sr / n)))
            if 1 <= idx < len(spec) - 1:
                harm += float(np.sum(spec[idx - 1:idx + 2] ** 2))
    hnr_db = 10 * np.log10((harm + 1e-12) / (total - harm + 1e-12))
    # 动态范围：分帧 RMS 的 5%-95% 分位差
    hop = int(sr * 0.05)
    fr = int(sr * 0.10)
    vals = [np.sqrt(np.mean(x[i:i + fr] ** 2)) for i in range(0, len(x) - fr, hop)]
    vals = np.array([v for v in vals if v > 1e-5])
    dyn = 20 * np.log10(np.percentile(vals, 95) / (np.percentile(vals, 5) + 1e-12))
    return {"peak": round(peak, 3), "rms_db": round(20 * np.log10(rms), 1),
            "重心Hz": round(cen), "谐噪比dB": round(float(hnr_db), 1),
            "动态范围dB": round(float(dyn), 1), "f0估Hz": round(f0, 1)}


def process(src, dst, target_peak=0.92, chain_name="v1"):
    x, sr = sf.read(src, dtype="float64")
    if x.ndim > 1:
        x = x.mean(axis=1)
    before = metrics(x, sr)
    y = apply_eq(x, sr, chain_name)
    y = soft_deess(y, sr)
    y = y / (np.max(np.abs(y)) + 1e-12) * target_peak
    after = metrics(y, sr)
    sf.write(dst, y, sr, subtype="PCM_16")
    return before, after


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("用法: 道音色融合.py 输入.wav 输出.wav")
        raise SystemExit(1)
    pk = float(sys.argv[3]) if len(sys.argv) > 3 else 0.92
    cn = sys.argv[4] if len(sys.argv) > 4 else "v1"
    b, a = process(sys.argv[1], sys.argv[2], target_peak=pk, chain_name=cn)
    print(json.dumps({"处理前": b, "处理后": a}, ensure_ascii=False))
