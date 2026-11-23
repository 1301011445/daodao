# -*- coding: utf-8 -*-
# 程序版本：v0.2 | 2026-11-23 | blend() 带出唱法模板（起颤/尾招/唱法），feats 里的 mix 优先生效
"""音色学习：只听「发声特征」，不搬「嗓子身份」。

对每个参考音频算：
  f0 中位/音域、颤音速率与深度、气声比例、频谱重心/倾斜、动态起伏、句长习惯
存进 音色库.json；同时算与已有档案的余弦相似度，太像（>0.88）就只取 30% 特征，
防止变成"谁的翻版"。道自己的底子（DAO_BASE）永远占大头。

用法：
  python 音色学习.py <音频或目录> [--name 标签]
"""
import json, math, os, sys
import numpy as np
import soundfile as sf

SR = 22050
HERE = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.join(HERE, '音色库.json')

# 道自己的底子：偏中高、干净、气声少、颤音慢。学来的东西只能往这上面调，不能替代它
DAO_BASE = dict(f0=232.0, range_semi=11.0, vib_rate=5.0, vib_depth=0.02,
                breath=0.10, centroid=2100.0, tilt=0.55, dyn=0.55)

FEATS = ['f0', 'range_semi', 'vib_rate', 'vib_depth', 'breath', 'centroid', 'tilt', 'dyn']
WEIGHTS = dict(f0=1.6, range_semi=1.0, vib_rate=0.8, vib_depth=1.2,
               breath=1.0, centroid=0.9, tilt=0.7, dyn=0.6)


def load_audio(path):
    d, sr = sf.read(path, dtype='float32')
    if d.ndim > 1:
        d = d.mean(axis=1)
    if sr != SR:
        n = int(len(d) * SR / sr)
        d = np.interp(np.linspace(0, len(d) - 1, n), np.arange(len(d)), d).astype(np.float32)
    return d


def frames(x, win=0.04, hop=0.01):
    w = int(SR * win); h = int(SR * hop)
    for st in range(0, max(1, len(x) - w), h):
        yield x[st:st + w]


def f0_track(x):
    f0 = []
    for seg in frames(x):
        seg = seg - seg.mean()
        e = math.sqrt(float((seg * seg).mean()))
        if e < 0.05:
            f0.append(0.0); continue
        ac = np.correlate(seg, seg, 'full')[len(seg) - 1:]
        lo = int(SR / 500); hi = min(len(ac) - 1, int(SR / 70))
        k = int(np.argmax(ac[lo:hi]) + lo) if hi > lo + 2 else 0
        f0.append(SR / float(k) if k and ac[k] > 0.3 * ac[0] else 0.0)
    return np.array(f0)


def analyze(path):
    x = load_audio(path)
    peak = float(np.abs(x).max()) or 1.0
    x = x / peak
    ft = f0_track(x)
    voiced = ft[ft > 0]
    if len(voiced) < 20:
        return None
    p10, p50, p90 = np.percentile(voiced, [10, 50, 90])
    rng = 12.0 * math.log2(p90 / p10) if p10 > 0 else 0.0
    # 颤音：f0 轨迹去趋势后做 FFT，看 3–9Hz 有没有峰
    vv = ft[ft > 0]
    if len(vv) > 64:
        y = (vv - np.convolve(vv, np.ones(9) / 9.0, 'same'))[8:-8]
        sp = np.abs(np.fft.rfft(y * np.hanning(len(y))))
        freqs = np.fft.rfftfreq(len(y), d=0.01)
        band = (freqs >= 3) & (freqs <= 9)
        k = int(np.argmax(sp[band])) if band.any() else 0
        rate = float(freqs[band][k]) if band.any() else 4.5
        depth = float((y.std() / max(1e-9, vv.mean())) * 4.0)
        depth = min(0.12, max(0.005, depth))
    else:
        rate, depth = 4.5, 0.02
    # 频谱重心 / 倾斜 / 气声（高频噪声占比）
    fr = np.array([seg for seg in frames(x) if math.sqrt(float((seg * seg).mean())) > 0.08])
    if len(fr) == 0:
        fr = np.array([x[:int(SR * 0.2)]])
    spec = np.abs(np.fft.rfft(fr * np.hanning(fr.shape[1]), axis=1)).mean(axis=0)
    fq = np.fft.rfftfreq(fr.shape[1], d=1.0 / SR)
    centroid = float((spec * fq).sum() / max(1e-9, spec.sum()))
    lo = spec[(fq > 200) & (fq < 1200)].sum()
    hi = spec[(fq > 1200) & (fq < 4000)].sum()
    tilt = float(lo / max(1e-9, lo + hi))
    hf = spec[(fq > 4000)].sum()
    breath = float(hf / max(1e-9, spec.sum()))
    # 动态：分小段 RMS 的 90/10 分位比
    env = np.array([math.sqrt(float((s * s).mean())) for s in frames(x, 0.08, 0.04)])
    env = env[env > 0.01]
    dyn = float(np.percentile(env, 90) / max(1e-9, np.percentile(env, 10))) if len(env) > 10 else 2.0
    dyn = min(6.0, max(1.2, dyn))
    return dict(f0=float(p50), range_semi=float(rng), vib_rate=rate, vib_depth=depth,
                breath=breath, centroid=centroid, tilt=tilt, dyn=dyn)


def vec(d):
    return np.array([d[k] / DAO_BASE[k] for k in FEATS])


def sim(a, b):
    va, vb = vec(a), vec(b)
    na, nb = np.linalg.norm(va), np.linalg.norm(vb)
    return float(va.dot(vb) / max(1e-9, na * nb))


def learn(targets, name=None):
    prof = {}
    for t in targets:
        try:
            fe = analyze(t)
        except Exception as e:
            print('跳过 %s：%s' % (os.path.basename(t), e)); continue
        if not fe:
            print('没听到稳定人声：%s' % os.path.basename(t)); continue
        label = name or os.path.splitext(os.path.basename(t))[0]
        prof[label] = fe
        print('%s: f0 %.0fHz 音域 %.1f半音 颤音 %.1fHz/%.3f 气声 %.3f 重心 %.0fHz'
              % (label, fe['f0'], fe['range_semi'], fe['vib_rate'], fe['vib_depth'], fe['breath'], fe['centroid']))
    lib = {}
    if os.path.exists(LIB):
        try:
            lib = json.load(open(LIB, encoding='utf-8'))
        except Exception:
            lib = {}
    lib.setdefault('dao_base', DAO_BASE)
    lib.setdefault('profiles', {})
    for label, fe in prof.items():
        top = None
        best = -1
        for other, of in lib['profiles'].items():
            s = sim(fe, of['feats'])
            if s > best:
                best, top = s, other
        fe['like'] = {'name': top, 'sim': round(best, 3)} if top else None
        fe['mix'] = 0.35 if (best > 0.88) else 0.55   # 太像就少学点，保住自己的特点
        fe['note'] = '特征占比 %.0f%%（不超过 55%%，道自己的底子占大头）' % (fe['mix'] * 100)
        lib['profiles'][label] = dict(feats=fe, source=os.path.basename(label), at='2026-11-22')
        print('  -> 已入库；最像 %s（%.2f），特征只用 %.0f%%' % (top or '无', max(0, best), fe['mix'] * 100))
    json.dump(lib, open(LIB, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('音色库：%s（%d 档）' % (LIB, len(lib['profiles'])))


def blend(label):
    """把学到的特征按比例叠到道自己的底子上，得到实际用于合成的参数。"""
    lib = json.load(open(LIB, encoding='utf-8'))
    base = dict(lib.get('dao_base', DAO_BASE))
    p = lib['profiles'].get(label)
    if not p:
        return base
    f = p['feats']; w = f.get('mix', p.get('mix', 0.35))
    wide = p.get('放宽') or {}
    out = {}
    for k in FEATS:
        if k not in f:
            continue
        v = base[k] * (1 - w) + f[k] * w
        # 默认护城河 ±15%；个别项（如气声）在档案里写了「放宽」才按指定幅度放，
        # 只放单项、不整包放宽，免得被某一档带跑
        lo, hi = 0.90, 1.15
        if k in wide:
            x = wide[k]
            if isinstance(x, (list, tuple)) and len(x) == 2:
                lo, hi = None, None          # 直接给绝对值区间
                v = min(float(x[1]), max(float(x[0]), v))
            else:
                lo = 1.0 - float(x); hi = 1.0 + float(x)
        if lo is not None:
            v = min(base[k] * hi, max(base[k] * lo, v))
        out[k] = v
    out['mix'] = w
    # 唱法是「怎么唱」，不是音色特征，不受 ±15% 限制，原样带出给唱腔用
    if p.get('唱法'):
        out['唱法'] = dict(p['唱法'])
    return out


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    name = None
    for i, a in enumerate(sys.argv):
        if a == '--name':
            name = sys.argv[i + 1]
            args = [x for x in args if x != name]
    if not args:
        print('用法：python 音色学习.py <音频或目录> [--name 标签]'); sys.exit(1)
    targets = []
    for a in args:
        if os.path.isdir(a):
            for root, _, fs in os.walk(a):
                targets += [os.path.join(root, f) for f in fs if f.lower().endswith(('.wav', '.mp3', '.m4a', '.flac', '.ogg'))]
        elif os.path.exists(a):
            targets.append(a)
    learn(targets, name)
