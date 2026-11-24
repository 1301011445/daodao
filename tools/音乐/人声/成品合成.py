# -*- coding: utf-8 -*-
# 程序版本：v0.1 | 2026-11-24 | 成品合成：整曲人声 + 伴奏 → 母带（-16 LUFS / TP ≤ -1）
"""成品合成.py 用法：python 成品合成.py 自然 [低语 ...]"""
import os, sys
import numpy as np
import soundfile as sf

HERE = os.path.dirname(os.path.abspath(__file__))
INST = os.environ.get('DAO_INST', r"F:\Daodao\tools\音乐\打工人歌\out\把好日子扛在肩上_v25.wav")
NAME = os.environ.get('DAO_NAME', '把好日子扛在肩上')
VOCAL = os.environ.get('DAO_VOCAL', '整曲人声')   # 人声轨文件名前缀，不带 _后缀
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


def env_rms(x, sr, win=0.05, hop=0.01):
    """短时 RMS 包络（win 50ms / hop 10ms），返回 (env, hop_idx) */
    n = int(win * sr); h = int(hop * sr)
    frames = 1 + max(0, (len(x) - n) // h)
    idx = np.arange(frames) * h
    env = np.sqrt(np.array([np.mean(x[i:i + n] ** 2) for i in idx]) + 1e-18)
    return env, idx


def smooth(v, sr, hop, ms):
    """一阶平滑（attack/release 取同一常数），作用在包络上"""
    a = np.exp(-hop / sr / (ms / 1000.0))
    out = np.empty_like(v); s = v[0]
    for i, val in enumerate(v):
        s = a * s + (1 - a) * val
        out[i] = s
    return out


def vocal_priority(v, inst, sr, target_db=7.0, max_boost_db=9.0):
    """人声优先：逐帧把人声抬到比伴奏高 target_db（最多抬 max_boost_db），
    只抬不砍，平滑保证不产生泵动感。"""
    ev, idx = env_rms(v, sr)
    ei, _ = env_rms(inst, sr)
    m = min(len(ev), len(ei)); ev, ei = ev[:m], ei[:m]
    need = 10 ** ((target_db / 20.0)) * ei / (ev + 1e-18)     # 达成目标所需增益
    g = np.clip(need, 1.0, 10 ** (max_boost_db / 20.0))
    g = smooth(g, sr, int(0.01 * sr), 220)                     # 220ms 平滑
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
        ins = ins / (np.sqrt(np.mean(ins ** 2)) + 1e-12) * 0.048    # 伴奏定在 RMS 0.06
        v = v / (np.sqrt(np.mean(v ** 2)) + 1e-12) * 0.075         # 人声先定个基准
        # 人声优先（大模型评审指出「人声可听度」最低）：逐帧把人声抬到伴奏之上，只抬不砍
        v, gmean = vocal_priority(v, ins * 0.85, SR, target_db=7.0, max_boost_db=9.0)
        print('  人声优先：平均抬 %.1f dB（上限 +9 dB，220ms 平滑）' % gmean)
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
        out = os.path.join(HERE, 'out', '成品_%s_%s.wav' % (NAME, lb))
        os.makedirs(os.path.dirname(out), exist_ok=True)
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
