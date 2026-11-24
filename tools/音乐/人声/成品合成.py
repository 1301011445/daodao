# -*- coding: utf-8 -*-
# 程序版本：v0.3 | 2026-11-24 | 成品合成：整曲人声 + 伴奏 -> 母带（人声优先 + -16 LUFS / TP <= -1）
"""成品合成.py 用法：python 成品合成.py 自然 [低语 ...]
环境变量：DAO_INST 伴奏路径 / DAO_NAME 曲名 / DAO_VOCAL 人声轨前缀"""
import os, sys
import numpy as np
import soundfile as sf

HERE = os.path.dirname(os.path.abspath(__file__))
INST = os.environ.get('DAO_INST', r"F:\Daodao\tools\音乐\打工人歌\out\把好日子扛在肩上_v25.wav")
NAME = os.environ.get('DAO_NAME', '把好日子扛在肩上')
VOCAL = os.environ.get('DAO_VOCAL', '整曲人声')
SR = 22050
INST_GAIN = 0.85
VOCAL_BASE = 0.075
INST_BASE = 0.048
TARGET_DB = 10.0
MAX_BOOST_DB = 12.0


def load(p, sr):
    x, s = sf.read(p, dtype='float64')
    if x.ndim > 1:
        x = x.mean(axis=1)
    if s != sr:
        x = np.interp(np.linspace(0, len(x) - 1, int(len(x) * sr / s)), np.arange(len(x)), x)
    return x


def lufs_approx(x):
    x = x.astype(np.float64)
    return 10 * np.log10(np.mean(x ** 2) + 1e-15)


def env_rms(x, sr, win=0.05, hop=0.01):
    n = int(win * sr)
    h = int(hop * sr)
    frames = 1 + max(0, (len(x) - n) // h)
    idx = np.arange(frames) * h
    env = np.sqrt(np.array([np.mean(x[i:i + n] ** 2) for i in idx]) + 1e-18)
    return env, idx


def smooth(v, sr, hop, ms):
    a = np.exp(-hop / float(sr) / (ms / 1000.0))
    out = np.empty_like(v)
    s = v[0]
    for i, val in enumerate(v):
        s = a * s + (1 - a) * val
        out[i] = s
    return out


def vocal_priority(v, inst, sr, target_db=TARGET_DB, max_boost_db=MAX_BOOST_DB):
    """逐帧把人声抬到比伴奏高 target_db（最多抬 max_boost_db），只抬不砍。"""
    ev, idx = env_rms(v, sr)
    ei, _ = env_rms(inst, sr)
    m = min(len(ev), len(ei))
    ev, ei = ev[:m], ei[:m]
    need = (10 ** (target_db / 20.0)) * ei / (ev + 1e-18)
    g = np.clip(need, 1.0, 10 ** (max_boost_db / 20.0))
    g = smooth(g, sr, int(0.01 * sr), 220)
    g_full = np.interp(np.arange(len(v)), idx[:m], g, right=g[-1])
    return v * g_full, float(20 * np.log10(np.mean(g) + 1e-12))


def main():
    labels = sys.argv[1:] or ['自然']
    inst = load(INST, SR)
    for lb in labels:
        v = load(os.path.join(HERE, 'out', '%s_%s.wav' % (VOCAL, lb)), SR)
        n = max(len(v), len(inst))
        v = np.pad(v, (0, n - len(v)))
        ins = np.pad(inst, (0, n - len(inst)))
        ins = ins / (np.sqrt(np.mean(ins ** 2)) + 1e-12) * INST_BASE
        v = v / (np.sqrt(np.mean(v ** 2)) + 1e-12) * VOCAL_BASE
        v, gmean = vocal_priority(v, ins * INST_GAIN, SR)
        print('  人声优先：平均抬 %.1f dB（上限 +%.0f dB，220ms 平滑）' % (gmean, MAX_BOOST_DB))
        mix = v + ins * INST_GAIN
        for _ in range(6):
            peak = np.max(np.abs(mix)) + 1e-12
            mix = mix / peak * 0.88
            l = lufs_approx(mix)
            mix = mix * 10 ** ((-16.0 - l) / 20.0)
        peak = np.max(np.abs(mix)) + 1e-12
        if peak > 0.891:
            mix = mix / peak * 0.891
        out = os.path.join(HERE, 'out', '成品_%s_%s.wav' % (NAME, lb))
        os.makedirs(os.path.dirname(out), exist_ok=True)
        sf.write(out, mix.astype(np.float32), SR)
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
