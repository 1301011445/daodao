# -*- coding: utf-8 -*-
"""把 v15 的缓存片段按生成顺序拼成完整试听，过一道 biquad 人声滤镜再出 wav/mp3"""
import glob, os, sys
import numpy as np, soundfile as sf, lameenc

sys.path.insert(0, r"F:\Daodao\tools\语音")
from 人声滤镜_biquad import apply_chain

CACHE = r"F:\Daodao\OpenUtau\_x\Cache"
OUT = r"F:\Daodao\曲库\麦子熟的时候_试听"


def main():
    files = sorted(glob.glob(CACHE + r"\wdl-v10-*.wav"), key=os.path.getmtime)[-8:]
    parts = []
    sr = None
    for f in files:
        x, s = sf.read(f, dtype='float32')
        sr = s or sr
        if x.ndim > 1:
            x = x.mean(1)
        parts.append(x)
    x = np.concatenate(parts)
    peak = float(np.abs(x).max())
    if peak > 0.99:
        x = x / peak * 0.95
    y = apply_chain(x, sr)
    peak2 = float(np.abs(y).max())
    if peak2 > 0.95:
        y = y / peak2 * 0.92
    sf.write(OUT + '.wav', y, sr, subtype='PCM_16')
    pcm = (np.clip(y, -1, 1) * 32767).astype(np.int16).tobytes()
    enc = lameenc.Encoder()
    enc.set_bit_rate(192); enc.set_channels(1); enc.set_in_sample_rate(sr); enc.set_quality(2)
    open(OUT + '.mp3', 'wb').write(enc.encode(pcm) + enc.flush())

    def harsh(a):
        X = np.abs(np.fft.rfft(a * np.hanning(len(a))))
        f = np.fft.rfftfreq(len(a), 1 / sr)
        return X[(f >= 3200) & (f <= 8000)].mean() / X[(f >= 300) & (f <= 3200)].mean()

    rms = 20 * np.log10(np.sqrt((y ** 2).mean()) + 1e-12)
    # 数一数有声段（应接近音符数）
    env = np.abs(y)
    n = int(sr * 0.02)
    frames = env[:len(env) // n * n].reshape(-1, n).max(1)
    thr = frames.max() * 0.12
    voiced = int(((frames > thr) * 1).sum())
    print('SONG|dur=%.2fs|harsh=%.3f|rms=%.1fdB|peak=%.2f|voiced_frames=%d/%d'
          % (len(y) / sr, harsh(y), rms, float(np.abs(y).max()), voiced, len(frames)))
    print('chunks=%d' % len(files))


if __name__ == '__main__':
    main()
