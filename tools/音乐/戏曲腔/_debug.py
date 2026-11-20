# -*- coding: utf-8 -*-
"""调试：检查合成信号的频谱与包络，确认测量仪本身是否准。"""
import importlib.util, os, struct, wave, math
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ARR = os.path.join(HERE, '..', '编配对比', '编配层次.py')

spec = importlib.util.spec_from_file_location('arr', ARR)
arr = importlib.util.module_from_spec(spec); spec.loader.exec_module(arr)

out = os.path.join(HERE, '_vibe_tmp.wav')
notes = [dict(t=0, dur=1920, pitch=76, ch=5, amp=0.8)]
arr.render(notes, out)
w = wave.open(out, 'rb'); n = w.getnframes()
s = np.array(struct.unpack('<%dh' % n, w.readframes(n)), dtype=float) / 32767.0
sr = w.getframerate(); w.close()
print('sr', sr, 'n', n, 'dur', n / sr)

# 高分辨率频谱：中段 8192 点 + 补零到 65536
mid = len(s) // 2
seg = s[mid - 4096: mid + 4096]
sp = np.abs(np.fft.rfft(seg * np.hanning(len(seg)), 65536))
fr = np.fft.rfftfreq(65536, 1.0 / sr)
top = np.argsort(sp)[-8:][::-1]
print('Top peaks:')
for i in top:
    print('  %8.1f Hz  %.1f dB' % (fr[i], 20 * math.log10(sp[i] + 1e-12)))
f0 = fr[top[0]]
print('f0=%.1f  3f=%.1f  5f=%.1f' % (f0, 3 * f0, 5 * f0))
def at(hz):
    i = int(round(hz * 65536 / sr))
    return sp[max(0, min(i, len(sp) - 1))]
a1, a3, a5 = at(f0), at(3 * f0), at(5 * f0)
print('a1=%.1f a3=%.1f a5=%.1f  odd=%.1f dB' % (a1, a3, a5, 20 * math.log10((a3 + a5) / a1)))

# 包络（1ms）
env = np.array([np.mean(np.abs(s[i:i + 44])) for i in range(0, len(s) - 44, 44)])
t = np.arange(len(env)) / 1000.0
pk = env.max()
idx = np.argmax(env >= pk * 0.9)
print('peak=%.3f  90%% at %.1f ms' % (pk, t[idx] * 1000))
print('env[0:60:5]=' + ' '.join('%.2f' % env[i] for i in range(0, 120, 5)))

# 瞬时频率（解析信号）
def analytic(x):
    N = len(x)
    X = np.fft.fft(x)
    h = np.zeros(N)
    h[0] = 1; h[1:N // 2] = 2; h[N // 2] = 1
    return np.fft.ifft(X * h)

a = analytic(s)
ph = np.unwrap(np.angle(a))
fi = np.diff(ph) * sr / (2 * math.pi)
seg = fi[int(sr * 0.4):int(sr * 1.8)]
print('f_inst mean %.1f  min %.1f  max %.1f' % (seg.mean(), seg.min(), seg.max()))
c = 1200 * np.log2(seg / np.median(seg))
print('cents min %.1f max %.1f  halfrange %.1f' % (c.min(), c.max(), (c.max() - c.min()) / 2))
spec_mod = np.abs(np.fft.rfft((c - c.mean()) * np.hanning(len(c))))
frm = np.fft.rfftfreq(len(c), 1 / sr)
band = (frm > 2) & (frm < 14)
print('mod peak %.2f Hz' % frm[band][np.argmax(spec_mod[band])])
