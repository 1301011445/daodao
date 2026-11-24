# -*- coding: utf-8 -*-
# 临时验证：逐帧 HNR（Praat 思路）对比现判据的整段频带法
import numpy as np, soundfile as sf, sys

def f0_frame(s, sr):
    s = s - s.mean()
    ac = np.correlate(s, s, 'full')[len(s) - 1:]
    lo, hi = int(sr / 700), int(sr / 60)
    if ac[0] <= 0:
        return 0.0
    lag = lo + int(np.argmax(ac[lo:hi]))
    return sr / lag

def hnr_frame(s, sr, f0):
    n = len(s)
    sp = np.abs(np.fft.rfft(s * np.hanning(n)))
    fq = np.fft.rfftfreq(n, 1.0 / sr)
    tot = float(np.sum(sp ** 2)) + 1e-12
    binw = sr / n
    half = max(0.03 * f0, 2.0 * binw)     # 汉宁窗主瓣约 4 个 bin，带宽必须容得下泄漏
    h = 0.0
    for k in range(1, 20):
        c = k * f0
        if c >= fq[-1]:
            break
        band = (fq > c - half) & (fq < c + half)
        h += float(np.sum(sp[band] ** 2))
    return 10 * np.log10((h + 1e-12) / max(1e-12, tot - h))

def run(p):
    x, sr = sf.read(p, dtype='float64')
    if x.ndim > 1: x = x.mean(axis=1)
    w, h = int(sr * 0.04), int(sr * 0.01)
    vals = []
    for i in range(0, len(x) - w, h):
        s = x[i:i + w]
        if np.sqrt(np.mean(s ** 2)) < 0.02:
            continue
        f0 = f0_frame(s, sr)
        if f0 < 60:
            continue
        vals.append(hnr_frame(s, sr, f0))
    vals = np.array(vals)
    print('%s | 帧数 %d | HNR 中位 %.1f dB | P25 %.1f | P75 %.1f'
          % (p.split('\\')[-1], len(vals), np.median(vals), np.percentile(vals, 25), np.percentile(vals, 75)))

for p in [r"F:\Daodao\tools\音乐\音色\out\_判据基准_220.wav",
          r"F:\Daodao\tools\音乐\人声\out\_tts_自然.mp3",
          r"F:\Daodao\tools\音乐\人声\out\_tts_少年.mp3",
          r"F:\Daodao\tools\音乐\人声\out\人声_自然.wav"]:
    run(p)
