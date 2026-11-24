# -*- coding: utf-8 -*-
# 程序版本：v0.1 | 2026-11-24 | 成品合成：整曲人声 + 伴奏 → 母带（-16 LUFS / TP ≤ -1）
"""成品合成.py 用法：python 成品合成.py 自然 [低语 ...]"""
import os, sys
import numpy as np
import soundfile as sf

HERE = os.path.dirname(os.path.abspath(__file__))
INST = r"F:\Daodao\tools\音乐\打工人歌\out\把好日子扛在肩上_v25.wav"
SR = 22050


def load(p, sr):
    x, s = sf.read(p, dtype='float64')
    if x.ndim > 1:
        x = x.mean(axis=1)
    if s != sr:
        x = np.interp(np.linspace(0, len(x) - 1, int(len(x) * sr / s)), np.arange(len(x)), x)
    return x


def lufs_approx(x):
    """按 ITU 积分近似（这里用 K 加权简化：只做均方 + 门限）。"""
    x = x.astype(np.float64)
    ms = np.mean(x ** 2) + 1e-15
    return 10 * np.log10(ms) - 0.0


def main():
    labels = sys.argv[1:] or ['自然']
    inst = load(INST, SR)
    for lb in labels:
        v = load(os.path.join(HERE, 'out', '整曲人声_%s.wav' % lb), SR)
        n = min(len(v), len(inst))
        v, ins = v[:n], inst[:n]
        ins = ins / (np.sqrt(np.mean(ins ** 2)) + 1e-12) * 0.048    # 伴奏定在 RMS 0.06
        v = v / (np.sqrt(np.mean(v ** 2)) + 1e-12) * 0.075         # 人声略低于伴奏能量，但峰值靠前
        mix = v + ins * 0.85
        # 母带：先按峰值留 -1dBTP 余量，再逐轮压到 -16 LUFS 附近
        for _ in range(6):
            peak = np.max(np.abs(mix)) + 1e-12
            mix = mix / peak * 0.88
            l = lufs_approx(mix)
            mix = mix * 10 ** ((-16.0 - l) / 20.0)
        peak = np.max(np.abs(mix)) + 1e-12
        if peak > 0.891:      # ≈ -1.0 dBFS
            mix = mix / peak * 0.891
        out = os.path.join(HERE, 'out', '成品_把好日子扛在肩上_%s.wav' % lb)
        sf.write(out, mix.astype(np.float32), SR)
        # 用真正的响度表（响度体检）闭环校正，不用自己那个粗糙估算
        import subprocess, re
        meter = r"F:\Daodao\tools\音频\响度体检.py"
        for _ in range(3):
            r = subprocess.run([sys.executable, '-X', 'utf8', meter, out],
                               capture_output=True, text=True, encoding='utf-8')
            m = re.search(r'\.wav\s+([\d.]+)\s+([\-\d.]+)\s+([\-\d.]+)\s+([\-\d.]+)\s+\w+\s+\w+\s+\w+', r.stdout)
            if not m:
                break
            lufs = float(m.group(2))
            if abs(lufs + 16.0) < 1.0:
                break
            gain = 10 ** ((-16.0 - lufs) / 20.0)
            mix = mix * gain
            # 峰值已经顶到天花板，单纯缩回去等于没加：用软限幅（tanh 膝点）换响度
            knee = 0.95
            mix = np.tanh(mix / knee) * knee
            pk = np.max(np.abs(mix)) + 1e-12
            if pk > 0.891:
                mix = mix / pk * 0.891
            sf.write(out, mix.astype(np.float32), SR)
        print('%s | %.1fs | RMS %.2f | peak %.3f | 写 %s'
              % (lb, len(mix) / SR, 20 * np.log10(np.sqrt(np.mean(mix ** 2))), float(np.max(np.abs(mix))),
                 os.path.basename(out)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
