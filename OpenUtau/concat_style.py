# -*- coding: utf-8 -*-
"""把 OpenUtau 预渲染的缓存片段按无缝顺序拼成完整试音，出 wav/mp3 并量化"""
import glob, os, sys
import numpy as np, soundfile as sf, lameenc

CACHE = r"F:\Daodao\OpenUtau\_x\Cache"
OUTD = r"F:\Daodao\曲库\_试音_声库"


def rd(p):
    x, sr = sf.read(p, dtype='float32')
    if x.ndim > 1:
        x = x.mean(1)
    return x, sr


def boundary_cost(a, b, sr):
    n = max(1, int(sr * 0.01))
    ea = float(np.sqrt((a[-n:] ** 2).mean()))
    eb = float(np.sqrt((b[:n] ** 2).mean()))
    step = abs(ea - eb)
    # 拼接点的样本突变（按峰值的相对量）
    click = abs(float(a[-1]) - float(b[0])) / (max(1e-6, float(np.abs(a).max())))
    return step, click


def build(files, out_base):
    waves = [rd(f) for f in files]
    sr = waves[0][1]
    a, b = waves[0][0], waves[1][0]
    c_ab = boundary_cost(a, b, sr)
    c_ba = boundary_cost(b, a, sr)
    if c_ab <= c_ba:
        x, order = np.concatenate([a, b]), 'A->B'
    else:
        x, order = np.concatenate([b, a]), 'B->A'
    peak = float(np.abs(x).max())
    if peak > 0.99:
        x = x / peak * 0.95
    sf.write(out_base + '.wav', x, sr, subtype='PCM_16')
    pcm = (x * 32767).astype(np.int16).tobytes()
    enc = lameenc.Encoder()
    enc.set_bit_rate(192); enc.set_channels(1); enc.set_in_sample_rate(sr); enc.set_quality(2)
    open(out_base + '.mp3', 'wb').write(enc.encode(pcm) + enc.flush())
    X = np.abs(np.fft.rfft(x * np.hanning(len(x))))
    f = np.fft.rfftfreq(len(x), 1 / sr)
    lo = X[(f >= 300) & (f <= 3200)].mean()
    hi = X[(f >= 3200) & (f <= 8000)].mean()
    rms = 20 * np.log10(np.sqrt((x ** 2).mean()) + 1e-12)
    return dict(dur=len(x) / sr, rms=rms, harsh=hi / lo, peak=float(np.abs(x).max()),
                order=order, cost=(c_ab, c_ba))


files = sorted(glob.glob(CACHE + r"\wdl-v10-*.wav"), key=os.path.getmtime)
tag = sys.argv[1]
sel = files[-4:] if tag == 'pair4' else files[-2:]
if tag in ('wanglihong', 'taylor'):
    sel = files[-4:][:2] if tag == 'wanglihong' else files[-4:][2:]
r = build(sel, os.path.join(OUTD, sys.argv[2]))
print('%s|files=%s|order=%s|dur=%.2fs|rms=%.1fdB|harsh=%.3f|peak=%.2f|cost=%.4f/%.4f'
      % (sys.argv[2], [os.path.basename(p) for p in sel], r['order'], r['dur'], r['rms'], r['harsh'], r['peak'], r['cost'][0][0], r['cost'][1][0]))
