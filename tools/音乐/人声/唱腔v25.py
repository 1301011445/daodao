# -*- coding: utf-8 -*-
# 程序版本：v0.3 | 2026-11-23 | 尾音改读「尾招」机读字段（弱收/截断/降调），不再靠字符串包含猜
"""唱腔 v25：把代唱人声过一遍「歌唱家唱法」——颤音、连唱、气口、段落起伏。

音色参数来自 音色库.json：道的底子 + 参考音色的发声特征（最多 55%），
所以学的是「怎么唱」，不是把谁的嗓子搬过来。

用法：python 唱腔v25.py [音色标签]
产出：out\唱腔_v25_混音.mp3 / 唱腔_v25_人声.wav
"""
import asyncio, importlib.util, json, math, os, sys
import numpy as np
import soundfile as sf
import edge_tts

SR = 22050
HERE = os.path.dirname(os.path.abspath(__file__))
BEAT = 480
sys.path.insert(0, os.path.dirname(HERE))

spec = importlib.util.spec_from_file_location(
    'g25', os.path.join(HERE, '..', '打工人歌', '打工人歌_v25.py'))
g25 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g25)

sp2 = importlib.util.spec_from_file_location(
    'timbre', os.path.join(HERE, '..', '音色', '音色学习.py'))
timbre = importlib.util.module_from_spec(sp2)
sp2.loader.exec_module(timbre)

sp3 = importlib.util.spec_from_file_location('mt', os.path.join(HERE, '匹配表.py'))
mt = importlib.util.module_from_spec(sp3)
sp3.loader.exec_module(mt)

VOICE_MALE = 'zh-CN-YunxiNeural'
VOICE_FEMALE = 'zh-CN-XiaoyiNeural'
# 音高按谱子的绝对音来，只按嗓音类型整段平移：男声低 5 个半音、女声不动、少年高 2 个
VOICE_SHIFT = {VOICE_MALE: -5.0, VOICE_FEMALE: 0.0}
# 段落到嗓音的微调：主歌二压一点（下班后的松弛），桥段抬（少年沉思偏高），第三遍副歌再抬
TAG_LIFT = {'V': 0.0, 'C1': 0.0, 'V2': -0.6, 'C2': 0.4, 'B': 1.4, 'C3': 1.6}
CACHE = {}
SEM = asyncio.Semaphore(6)


def trim(x, thr=0.05):
    if len(x) == 0:
        return x
    m = np.abs(x)
    idx = np.where(m > max(thr, m.max() * 0.05))[0]
    if len(idx) == 0:
        return x
    return x[max(0, idx[0] - 20): min(len(x), idx[-1] + 20)]


def rms_env(x, sr, frame=0.01, hop=0.005):
    f = int(sr * frame); h = int(sr * hop)
    n = 1 + max(0, (len(x) - f) // h)
    out = np.zeros(n)
    for i in range(n):
        seg = x[i * h:i * h + f]
        out[i] = math.sqrt(float((seg * seg).mean())) if len(seg) else 0.0
    return out


def split_two(x, sr):
    x = trim(x)
    env = rms_env(x, sr)
    n = len(env)
    lo, hi = int(n * 0.28), int(n * 0.72)
    if hi - lo < 2:
        mid = len(x) // 2
        return x[:mid], x[mid:]
    k = int(np.argmin(env[lo:hi])) + lo
    cut = int(k * sr * 0.005)
    if env[lo:hi].max() > 0 and env[k] / max(1e-9, env[lo:hi].max()) > 0.7:
        cut = len(x) // 2
    cut = max(int(sr * 0.08), min(len(x) - int(sr * 0.08), cut))
    return trim(x[:cut]), trim(x[cut:])


def est_f0(x, sr):
    f0s = []
    win = int(sr * 0.04); hop = int(sr * 0.01)
    for st in range(0, max(1, len(x) - win), hop):
        seg = x[st:st + win]
        if len(seg) < win:
            break
        seg = seg - seg.mean()
        if math.sqrt(float((seg * seg).mean())) < 0.05:
            continue
        ac = np.correlate(seg, seg, 'full')[win - 1:]
        lo = int(sr / 400); hi = min(len(ac) - 1, int(sr / 70))
        if hi <= lo + 2:
            continue
        k = int(np.argmax(ac[lo:hi]) + lo)
        if ac[k] > 0.3 * ac[0]:
            f0s.append(sr / float(k))
    return float(np.median(f0s)) if f0s else 0.0


def ola(x, target, sr, frame_ms=30, hop_ms=10):
    win = int(sr * frame_ms / 1000.0); hop = int(sr * hop_ms / 1000.0)
    if len(x) < win or target <= 0:
        return np.zeros(max(1, target))
    s = target / float(len(x))
    out = np.zeros(target + win + 2)
    acc = np.zeros(len(out))
    w = np.hanning(win)
    nfr = 1 + int((len(x) - win) / hop)
    for k in range(nfr):
        src = k * hop
        dst = int(round(k * hop * s))
        if dst + win >= len(out):
            break
        out[dst:dst + win] += x[src:src + win] * w
        acc[dst:dst + win] += w
    acc[acc < 1e-6] = 1.0
    return (out / acc)[:target]


def vibrato(y, sr, rate, depth):
    """按正弦改瞬时速度 → 音高上下走，长度不变。"""
    if depth <= 0 or len(y) < 64:
        return y
    t = np.arange(len(y)) / float(sr)
    step = 1.0 / (1.0 + depth * np.sin(2 * math.pi * rate * t))
    pos = np.cumsum(step)
    pos = pos / pos[-1] * (len(y) - 1)
    return np.interp(pos, np.arange(len(y)), y).astype(np.float32)


def vibrato_delayed(y, sr, rate, depth, onset=0.55):
    """延迟起颤：前 onset 比例的音符走直音，之后才进入颤音。
    王菲/那英那类「先稳后颤」靠这条包络，不是整颗音符抖到底。"""
    if depth <= 0 or len(y) < 64:
        return y
    t = np.arange(len(y)) / float(sr)
    u = np.clip((t / max(1e-6, t[-1]) - onset) / max(1e-6, 1.0 - onset), 0.0, 1.0)
    u = u * u * (3 - 2 * u)                      # smoothstep，颤音渐入不突兀
    step = 1.0 / (1.0 + depth * u * np.sin(2 * math.pi * rate * t))
    pos = np.cumsum(step)
    pos = pos / pos[-1] * (len(y) - 1)
    return np.interp(pos, np.arange(len(y)), y).astype(np.float32)


def breath_noise(n, sr, level):
    if level <= 0 or n <= 0:
        return np.zeros(n, dtype=np.float32)
    rnd = np.random.default_rng(7)
    nz = rnd.standard_normal(n).astype(np.float32)
    # 一阶高通，让气声贴在高频，不糊住字
    nz = np.diff(nz, prepend=0.0)
    env = np.exp(-np.arange(n) / (sr * 0.05))
    return nz * env * level


def bright_shelf(y, sr, db):
    """一阶高通补一点亮度：把 1.2kHz 以上的部分抬 db。"""
    if db <= 0 or len(y) < 32:
        return y
    a = math.exp(-2 * math.pi * 1200.0 / sr)
    lp = np.zeros(len(y), dtype=np.float32)
    acc = 0.0
    for i in range(len(y)):
        acc = a * acc + (1 - a) * y[i]
        lp[i] = acc
    hi = y - lp
    return (y + (10 ** (db / 20.0) - 1.0) * hi).astype(np.float32)


def sing(x, target_hz, target_len, sr, prof, gain=1.0, fix=None):
    fix = fix or dict(bright_db=0.0, breath=1.0, vib=1.0)
    f0 = est_f0(x, sr) or target_hz
    r = max(0.5, min(2.0, target_hz / f0))
    if abs(r - 1.0) > 0.01:
        y = np.interp(np.arange(0, len(x) - 1, r), np.arange(len(x)), x)
    else:
        y = x
    y = ola(y, target_len, sr)
    # 有唱法模板就用它：延迟起颤（王菲/那英「先稳后颤」），没有模板还是老样子抖到底
    style = (prof.get('唱法') or {})
    onset = float(style.get('起颤', 0.0))
    if onset > 0.0:
        y = vibrato_delayed(y, sr, prof['vib_rate'], min(0.05, prof['vib_depth'] * fix['vib']), onset)
    else:
        y = vibrato(y, sr, prof['vib_rate'], min(0.05, prof['vib_depth'] * fix['vib']))
    y = y * gain
    n = min(len(y), int(sr * 0.07))
    y[:n] += breath_noise(n, sr, prof['breath'] * fix['breath'] * 0.5)
    y = bright_shelf(y, sr, fix['bright_db'])
    f = int(sr * 0.008)
    if f > 0 and len(y) > 3 * f:
        y[:f] *= np.linspace(0, 1, f)
        y[-f:] *= np.linspace(1, 0, f)
    # 尾音收法：机读字段「尾招」为准（弱收 / 截断 / 降调 / 气不散 / 稳后颤）
    tail = style.get('尾招') or ''
    if len(y) > int(sr * 0.18):
        if tail == '弱收':
            m = int(sr * 0.09)
            y[-m:] *= np.linspace(1, 0.25, m)     # 收到 0.25 而不是 0，气还在
        elif tail == '截断':
            m = int(sr * 0.012)
            y[-m:] *= np.linspace(1, 0, m)
        elif tail == '降调':
            m = int(sr * 0.30)
            y[-m:] *= np.linspace(1, 0.6, m)      # 近似"降调"：音量收、基频由 OLA 外不另做
    return y


async def tts_word(voice, word):
    key = (voice, word)
    if key in CACHE:
        return CACHE[key]
    async with SEM:
        d = os.path.join(HERE, '_tts'); os.makedirs(d, exist_ok=True)
        path = os.path.join(d, '%s_%s.mp3' % (voice.split('-')[2], abs(hash(word)) % 10 ** 8))
        if not os.path.exists(path) or os.path.getsize(path) < 2000:
            for attempt in range(4):
                try:
                    await edge_tts.Communicate(word, voice, rate='-8%').save(path)
                    if os.path.getsize(path) > 2000:
                        break
                except Exception as e:
                    print('重试 %s（%d/4）：%s' % (word, attempt + 1, type(e).__name__))
                    await asyncio.sleep(1.5 + attempt * 2)
        a, sr = sf.read(path, dtype='float32')
        if a.ndim > 1:
            a = a.mean(axis=1)
        if sr != SR:
            a = np.interp(np.linspace(0, len(a) - 1, int(len(a) * SR / sr)), np.arange(len(a)), a).astype(np.float32)
        CACHE[key] = a
        return a


async def main():
    label = sys.argv[1] if len(sys.argv) > 1 else '旧演唱版'
    prof = timbre.blend(label)
    print('音色：%s | 颤音 %.1fHz/%.3f 气声 %.2f 特征占比 %.0f%%'
          % (label, prof['vib_rate'], prof['vib_depth'], prof['breath'], prof.get('mix', 0) * 100))

    notes, mels, secs = g25.build()
    vocal = [n for n in notes if n['ch'] in (0, 4)]
    spt = (60.0 / g25.TEMPO) / g25.PPQ

    def tag_for(t0):
        for s in secs:
            if s['t0'] <= t0 < s['t1']:
                return s['tag']
        return 'V'

    def voices_for(t0):
        tag = tag_for(t0)
        if tag in ('V', 'C1'):
            return [VOICE_MALE]
        if tag in ('V2', 'C2', 'B'):
            return [VOICE_FEMALE]
        if tag == 'C3':
            return [VOICE_MALE, VOICE_FEMALE]
        return [VOICE_FEMALE]

    total = int(max(n['t'] + n['dur'] for n in notes) * spt * SR) + SR // 5
    buf = np.zeros(total, dtype=np.float32)
    jobs = []
    for m in mels:
        ph = sorted([x for x in vocal if m['t'] <= x['t'] < m['t'] + 8 * BEAT], key=lambda x: x['t'])
        if len(ph) != 8:
            continue
        for wi in range(4):
            for v in voices_for(m['t']):
                jobs.append((m['text'][wi * 2:wi * 2 + 2], v))
    print('待合成词组 %d' % len(jobs))
    await asyncio.gather(*[tts_word(v, w) for w, v in jobs])

    for m in mels:
        ph = sorted([x for x in vocal if m['t'] <= x['t'] < m['t'] + 8 * BEAT], key=lambda x: x['t'])
        if len(ph) != 8:
            continue
        vs = voices_for(m['t'])
        tag = tag_for(m['t'])
        fix = mt.TAG_FIX.get(tag, dict(bright_db=0.0, breath=1.0, vib=1.0))
        chorus = m['chorus']
        parts = {}
        for wi in range(4):
            for v in vs:
                a = await tts_word(v, m['text'][wi * 2:wi * 2 + 2])
                parts[(wi, v)] = split_two(a, SR)
        for ci in range(8):
            wi = ci // 2
            t, dur, pitch = ph[ci]['t'], ph[ci]['dur'], ph[ci]['pitch']
            tgt = max(int(SR * 0.12), int(dur * spt * SR * (0.99 if chorus else 0.92)))  # 副歌连唱，咬字之间不留缝
            gain = 1.25 if chorus else 1.0
            lays = []
            for v in vs:
                lift = TAG_LIFT.get(tag_for(m['t']), 0.0)
                hz = 440.0 * (2.0 ** ((pitch - 69 + VOICE_SHIFT.get(v, 0.0) + lift) / 12.0))
                lays.append(sing(parts[(wi, v)][ci % 2], hz, tgt, SR, prof, gain, fix))
            n = max(len(y) for y in lays)
            lay = np.zeros(n, dtype=np.float32)
            for y in lays:
                lay[:len(y)] += y
            lay /= len(lays)
            st = int(t * spt * SR); en = min(total, st + n)
            if en > st:
                buf[st:en] += lay[:en - st]

    peak = float(np.abs(buf).max()) or 1.0
    buf *= 0.5 / peak
    out = os.path.join(HERE, 'out'); os.makedirs(out, exist_ok=True)
    sf.write(os.path.join(out, '唱腔_v25_人声.wav'), buf, SR)
    inst, isr = sf.read(os.path.join(HERE, '..', '打工人歌', 'out', '把好日子扛在肩上_v25.wav'), dtype='float32')
    if isr != SR:
        inst = np.interp(np.linspace(0, len(inst) - 1, int(len(inst) * SR / isr)), np.arange(len(inst)), inst).astype(np.float32)
    L = min(len(inst), len(buf))
    mix = inst[:L] * 0.72 + buf[:L] * 0.85
    mx = float(np.abs(mix).max())
    if mx > 0.97:
        mix *= 0.97 / mx
    sf.write(os.path.join(out, '唱腔_v25_混音.mp3'), np.clip(mix, -1, 1), SR, format='MP3')
    sf.write(os.path.join(out, '唱腔_v25_混音.wav'), np.clip(mix, -1, 1), SR)
    print('完成：%.1f 秒' % (len(buf) / SR))


if __name__ == '__main__':
    asyncio.run(main())
