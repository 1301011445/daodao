# -*- coding: utf-8 -*-
# 程序版本：v0.1 | 2026-11-24 | 首建：不装 ffmpeg 也能改声线（降调/升调，时长不变）
"""声线塑造：按半音改基频，保持时长（线性重采样 + WSOLA 时间拉伸）

用法：python 声线塑造.py 输入.wav 输出.wav -4 [预览秒数]
原理：先按比例 r 线性重采样（声音变短 r 倍、音高乘 r），再用 WSOLA 时间拉伸 1/r 倍回到原时长。
不是电音效果：只做重采样 + 重叠相加，不做任何量化/相位随机化，音色只是往低/高走。
"""
import sys, math, array, wave
import numpy as np


def read_wav(path):
    with wave.open(path, 'rb') as w:
        n, ch, sw, sr = w.getnframes(), w.getnchannels(), w.getsampwidth(), w.getframerate()
        raw = w.readframes(n)
    if sw != 2:
        raise SystemExit('只支持 16bit PCM')
    a = np.frombuffer(raw, dtype='<i2').astype(np.float64) / 32768.0
    if ch > 1:
        a = a.reshape(-1, ch).mean(axis=1)
    return a, sr


def write_wav(path, x, sr):
    x = np.clip(x, -1.0, 1.0)
    with wave.open(path, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes((x * 32767).astype('<i2').tobytes())


def resample(x, ratio):
    """ratio>1 变长（音高降），采样点重排；线性插值。"""
    n = len(x)
    m = int(n * ratio)
    pos = np.linspace(0, n - 1, m)
    i = np.floor(pos).astype(int)
    i2 = np.minimum(i + 1, n - 1)
    f = pos - i
    return x[i] * (1 - f) + x[i2] * f


def wsola(x, k, N=1024, Hs=256, search=32):
    """时间缩放 k 倍（k>1 变长），输出帧距固定 Hs，源帧距 Hs/k；重叠相加不改音高。"""
    if abs(k - 1.0) < 1e-3:
        return x.copy()
    src_hop = max(1, int(round(Hs / k)))
    win = np.hanning(N)
    out_len = int(len(x) * k) + 2 * N
    out = np.zeros(out_len)
    wsum = np.zeros(out_len)
    idx = 0
    o = 0
    while idx + N < len(x) and o + N <= out_len:
        if idx >= src_hop and idx - src_hop + N <= len(x):
            cont = x[idx - src_hop:idx - src_hop + N]
        else:
            cont = x[idx:idx + N]
        best, bestd = 0, -1e18
        for d in range(-search, search + 1, 4):
            j = idx + d
            if j < 0 or j + N > len(x):
                continue
            c = float(np.dot(x[j:j + N], cont))
            if c > bestd:
                bestd, best = c, d
        j = max(0, min(len(x) - N, idx + best))
        out[o:o + N] += x[j:j + N] * win
        wsum[o:o + N] += win
        idx += src_hop
        o += Hs
    wsum[wsum < 1e-6] = 1e-6
    return out[:o] / wsum[:o]


def main():
    if len(sys.argv) < 4:
        print('用法: python 声线塑造.py 输入.wav 输出.wav 半音 [预览秒数]')
        return 2
    src, dst = sys.argv[1], sys.argv[2]
    semi = float(sys.argv[3])
    lim = float(sys.argv[4]) if len(sys.argv) > 4 else 0
    x, sr = read_wav(src)
    if lim > 0:
        x = x[:int(lim * sr)]
    r = 2 ** (semi / 12.0)
    # 先把时长拉长 1/r（音高乘 r），再 WSOLA 压回原时长
    y = resample(x, 1.0 / r)
    y = wsola(y, r)
    y = y[:len(x)]
    write_wav(dst, y, sr)
    print('写入 %s | %+.1f 半音 (r=%.3f) | %.2fs' % (dst, semi, r, len(y) / sr))
    return 0


if __name__ == '__main__':
    sys.exit(main())
