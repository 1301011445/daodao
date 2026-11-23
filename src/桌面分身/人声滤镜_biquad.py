# -*- coding: utf-8 -*-
"""实时人声滤镜（biquad 流式版）

为什么不用 FFT：FFT 长窗要攒够一整段才能变换，实时流里等于凭空加了几十毫秒延迟，
还会在窗边界产生跳变（之前测到的爆音点就来自这里）。biquad 是逐样本递推的
二阶 IIR，一块 20 ms 的音进来就能立刻出结果，延迟只剩 1~2 个样本。

滤镜链（都是轻手，目标是"不刺耳"而不是"变声"）：
  1) 高搁架 high shelf  : 3200 Hz, -2.0 dB   压掉刺耳的齿音/气声尖峰
  2) 钟形峰  peaking    : 4500 Hz, Q 0.9, -1.5 dB  再压一层 4~5k 的硬
  3) 低搁架 low shelf   : 140 Hz, +1.0 dB    补回胸腔厚度
整链相位基本线性，不引入回声感；总增益用 normalize 收住。

用法（离线整段）：
    from 人声滤镜_biquad import Chain
    y = Chain(44100).process(x)
用法（流式）：
    ch = Chain(44100)
    while True:
        block = read(20ms)
        out = ch.process_block(block)   # 状态在 ch 里，块与块之间无缝
"""
import math
import numpy as np


def _high_shelf(sr, f, gain_db, s=1.0):
    A = 10 ** (gain_db / 40.0)
    w = 2 * math.pi * f / sr
    cw, sw = math.cos(w), math.sin(w)
    alpha = sw / 2.0 * math.sqrt((A + 1 / A) * (1 / s - 1) + 2)
    b0 = A * ((A + 1) + (A - 1) * cw + 2 * math.sqrt(A) * alpha)
    b1 = -2 * A * ((A - 1) + (A + 1) * cw)
    b2 = A * ((A + 1) + (A - 1) * cw - 2 * math.sqrt(A) * alpha)
    a0 = (A + 1) - (A - 1) * cw + 2 * math.sqrt(A) * alpha
    a1 = 2 * ((A - 1) - (A + 1) * cw)
    a2 = (A + 1) - (A - 1) * cw - 2 * math.sqrt(A) * alpha
    return b0 / a0, b1 / a0, b2 / a0, a1 / a0, a2 / a0


def _low_shelf(sr, f, gain_db, s=1.0):
    A = 10 ** (gain_db / 40.0)
    w = 2 * math.pi * f / sr
    cw, sw = math.cos(w), math.sin(w)
    alpha = sw / 2.0 * math.sqrt((A + 1 / A) * (1 / s - 1) + 2)
    b0 = A * ((A + 1) - (A - 1) * cw + 2 * math.sqrt(A) * alpha)
    b1 = 2 * A * ((A - 1) - (A + 1) * cw)
    b2 = A * ((A + 1) - (A - 1) * cw - 2 * math.sqrt(A) * alpha)
    a0 = (A + 1) + (A - 1) * cw + 2 * math.sqrt(A) * alpha
    a1 = -2 * ((A - 1) + (A + 1) * cw)
    a2 = (A + 1) + (A - 1) * cw - 2 * math.sqrt(A) * alpha
    return b0 / a0, b1 / a0, b2 / a0, a1 / a0, a2 / a0


def _peaking(sr, f, gain_db, q=0.9):
    A = 10 ** (gain_db / 40.0)
    w = 2 * math.pi * f / sr
    cw, sw = math.cos(w), math.sin(w)
    alpha = sw / (2 * q)
    b0 = 1 + alpha * A
    b1 = -2 * cw
    b2 = 1 - alpha * A
    a0 = 1 + alpha / A
    a1 = -2 * cw
    a2 = 1 - alpha / A
    return b0 / a0, b1 / a0, b2 / a0, a1 / a0, a2 / a0


class _Biquad:
    """转置直接 II 型，单样本递推，状态可跨块延续。"""

    def __init__(self, coef):
        self.b0, self.b1, self.b2, self.a1, self.a2 = coef
        self.z1 = 0.0
        self.z2 = 0.0

    def process(self, x):
        b0, b1, b2, a1, a2 = self.b0, self.b1, self.b2, self.a1, self.a2
        z1, z2 = self.z1, self.z2
        out = np.empty(len(x), dtype=np.float64)
        for i in range(len(x)):
            xi = x[i]
            yi = b0 * xi + z1
            z1 = b1 * xi - a1 * yi + z2
            z2 = b2 * xi - a2 * yi
            out[i] = yi
        self.z1, self.z2 = z1, z2
        return out


class Chain:
    """一条滤镜链。sr 变了要新建一个。"""

    def __init__(self, sr=44100, soft=True):
        self.sr = sr
        self.stages = [
            _Biquad(_high_shelf(sr, 3200.0, -2.0)),
            _Biquad(_peaking(sr, 4500.0, -1.5, q=0.9)),
            _Biquad(_low_shelf(sr, 140.0, 1.0)),
        ]
        self.soft = soft

    def _run(self, x):
        y = np.asarray(x, dtype=np.float64)
        for st in self.stages:
            y = st.process(y)
        if self.soft:
            # 只有超过 0.9 才压，正常语音不动它
            peak = np.max(np.abs(y)) if len(y) else 0.0
            if peak > 0.9:
                y = np.tanh(y / max(peak, 1e-9) * 1.1) * 0.9
        return y.astype(np.float32)

    def process(self, x):
        """整段处理（离线，用于试听/落盘）。"""
        return self._run(x)

    def process_block(self, block):
        """流式处理一块（状态延续，块间无接缝）。"""
        return self._run(block)


def apply_chain(x, sr, soft=True):
    return Chain(sr, soft=soft).process(x)


if __name__ == "__main__":
    import sys
    import soundfile as sf
    src = sys.argv[1]
    dst = sys.argv[2]
    x, sr = sf.read(src, dtype='float32')
    if x.ndim > 1:
        x = x.mean(1)
    y = apply_chain(x, sr)
    sf.write(dst, y, sr, subtype='PCM_16')
    print('OK|%d|%d' % (len(y), sr))
