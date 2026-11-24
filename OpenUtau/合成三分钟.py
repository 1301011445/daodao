# -*- coding: utf-8 -*-
"""把 shiyin_v17.ustx 渲出的 ds-*.wav 片段拼成三分钟档，再过「道音色融合」后处理。"""
import glob
import os
import sys

import numpy as np
import soundfile as sf

sys.path.insert(0, r"F:\Daodao\tools\音乐\音色")
from 道音色融合 import process as timbre_process   # noqa: E402

CACHE = r"F:\Daodao\OpenUtau\_x\Cache"
OUT_WAV = r"F:\Daodao\曲库\麦子熟的时候_道演唱_三分钟.wav"
OUT_MP3 = r"F:\Daodao\曲库\麦子熟的时候_道演唱_三分钟.mp3"

parts = sorted(glob.glob(os.path.join(CACHE, "ds-*-depth0.60-steps20.wav")), key=os.path.getmtime)
print("片段 %d 个" % len(parts))

clips, sr = [], None
for p in parts:
    d, s = sf.read(p, dtype="float32")
    if d.ndim > 1:
        d = d.mean(axis=1)
    sr = s
    clips.append(d)

fade = int(sr * 0.010)
acc = clips[0].copy()
for c in clips[1:]:
    n = min(fade, len(acc), len(c))
    w = np.linspace(0, 1, n, dtype="float32")
    acc = np.concatenate([acc[:len(acc) - n], acc[len(acc) - n:] * (1 - w) + c[:n] * w, c[n:]])

print("拼接 %.2f 秒，尝试后处理…" % (len(acc) / sr), flush=True)
sf.write(CACHE + r"\_concat_raw.wav", acc, sr)
b, a = timbre_process(CACHE + r"\_concat_raw.wav", OUT_WAV, target_peak=0.92)
print("处理前", b)
print("处理后", a)

try:
    import lameenc
    y, _ = sf.read(OUT_WAV, dtype="float32")
    enc = lameenc.Encoder()
    enc.set_bit_rate(192)
    enc.set_in_sample_rate(sr)
    enc.set_channels(1)
    enc.set_quality(2)
    pcm = (y * 32767).astype("<i2").tobytes()
    open(OUT_MP3, "wb").write(enc.encode(pcm) + enc.flush())
    print("mp3 %s %.0f KB" % (OUT_MP3, os.path.getsize(OUT_MP3) / 1024))
except Exception as e:
    print("mp3 失败：", e)
