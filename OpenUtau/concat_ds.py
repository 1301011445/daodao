# -*- coding: utf-8 -*-
"""把 OpenUtau 逐段渲出的 DiffSinger 片段按时间顺序拼成整首，边界 10ms 交叉淡化，再出 wav/mp3。"""
import glob
import os
import sys

import numpy as np
import soundfile as sf

CACHE = r"F:\Daodao\OpenUtau\_x\Cache"
OUT_WAV = r"F:\Daodao\曲库\麦子熟的时候_绮萱试听.wav"
OUT_MP3 = r"F:\Daodao\曲库\麦子熟的时候_绮萱试听.mp3"
SKIP = int(sys.argv[1]) if len(sys.argv) > 1 else 2  # 跳过最早的前 N 段（那是单句试音，不属于本曲）

parts = sorted(glob.glob(os.path.join(CACHE, "ds-*-depth0.60-steps20.wav")), key=os.path.getmtime)
parts = parts[SKIP:]
print("候选片段 %d 个" % len(parts))

clips, sr = [], None
for p in parts:
    d, s = sf.read(p, dtype="float32")
    if d.ndim > 1:
        d = d.mean(axis=1)
    sr = s
    clips.append(d)
    print("  %-42s %.2fs" % (os.path.basename(p), len(d) / s))

if len(clips) < 2:
    raise SystemExit("片段不足")

fade = int(sr * 0.010)
acc = clips[0].copy()
for c in clips[1:]:
    n = min(fade, len(acc), len(c))
    w = np.linspace(0, 1, n, dtype="float32")
    acc = np.concatenate([acc[:len(acc) - n], acc[len(acc) - n:] * (1 - w) + c[:n] * w, c[n:]])

peak = float(np.max(np.abs(acc))) or 1.0
acc = acc / peak * 0.9
sf.write(OUT_WAV, acc, sr)
print("合成 %.2fs，峰值归一后写入 %s" % (len(acc) / sr, OUT_WAV))

try:
    import lameenc
    enc = lameenc.Encoder()
    enc.set_bit_rate(192)
    enc.set_in_sample_rate(sr)
    enc.set_channels(1)
    enc.set_quality(2)
    pcm = (acc * 32767).astype("<i2").tobytes()
    open(OUT_MP3, "wb").write(enc.encode(pcm) + enc.flush())
    print("mp3 %s %.1f KB" % (OUT_MP3, os.path.getsize(OUT_MP3) / 1024))
except Exception as e:
    print("mp3 失败：", e)
