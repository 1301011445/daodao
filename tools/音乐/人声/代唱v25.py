# -*- coding: utf-8 -*-
"""给 v25 新旋律配「代唱人声」：edge-tts 逐词组取声 -> 拆两字 -> 变时/变调贴谱 -> 混轨。

产出：
  out\代唱_v25_人声.wav   （只有人声）
  out\代唱_v25_混音.wav   （人声 + v25 伴奏）
  out\代唱_v25_时间轴.json（每句每字的时间点、音高，供真人重录对着走）
"""
import asyncio, importlib.util, json, math, os, sys
import numpy as np
import soundfile as sf
import edge_tts

SR = 22050
HERE = os.path.dirname(os.path.abspath(__file__))
BEAT = 480

spec = importlib.util.spec_from_file_location(
    'g25', os.path.join(HERE, '..', '打工人歌', '打工人歌_v25.py'))
g25 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g25)

VOICE_MALE = 'zh-CN-YunxiNeural'
VOICE_FEMALE = 'zh-CN-XiaoyiNeural'
BASE_HZ = {VOICE_MALE: 150.0, VOICE_FEMALE: 235.0}


def trim(x, thr=0.05):
    if len(x) == 0:
        return x
    m = np.abs(x)
    thr = max(thr, m.max() * 0.05)
    idx = np.where(m > thr)[0]
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
    """把一个两字词的音频拆成两声。找中间一段能量最低处；找不到明显谷就一分为二。"""
    x = trim(x)
    env = rms_env(x, sr)
    n = len(env)
    lo, hi = int(n * 0.28), int(n * 0.72)
    if hi - lo < 2:
        mid = len(x) // 2
        return x[:mid], x[mid:]
    seg = env[lo:hi]
    k = int(np.argmin(seg)) + lo
    cut = int(k * sr * 0.005)
    # 谷太浅（<35% 峰值）就退回中点，避免把气口当字缝
    if env[lo:hi].max() > 0 and env[k] / max(1e-9, env[lo:hi].max()) > 0.7:
        cut = len(x) // 2
    cut = max(int(sr * 0.08), min(len(x) - int(sr * 0.08), cut))
    return trim(x[:cut]), trim(x[cut:])


def est_f0(x, sr):
    """自相关估一遍基频；只取有声帧的中位数。"""
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
    """重叠相加把长度拉到 target（不改音高）。"""
    win = int(sr * frame_ms / 1000.0); hop = int(sr * hop_ms / 1000.0)
    if len(x) < win or target <= 0:
        return np.zeros(max(1, target))
    s = target / float(len(x))
    out = np.zeros(target + win + 2)
    w = np.hanning(win)
    nfr = 1 + int((len(x) - win) / hop)
    acc = np.zeros(len(out))
    for k in range(nfr):
        src = k * hop
        dst = int(round(k * hop * s))
        if dst + win >= len(out):
            break
        out[dst:dst + win] += x[src:src + win] * w
        acc[dst:dst + win] += w
    acc[acc < 1e-6] = 1.0
    out = out / acc
    return out[:target]


def sing_syllable(x, target_hz, target_len, sr):
    """先按 f0 比例重采样改音高，再 OLA 拉到目标时长。"""
    f0 = est_f0(x, sr)
    if f0 <= 0:
        f0 = target_hz
    r = target_hz / f0
    r = max(0.5, min(2.0, r))
    if abs(r - 1.0) > 0.01:
        pos = np.arange(0, len(x) - 1, r)
        y = np.interp(pos, np.arange(len(x)), x)
    else:
        y = x
    y = ola(y, target_len, sr)
    # 首尾各 8ms 淡入淡出，避免拼接爆音
    f = min(int(sr * 0.008), len(y) // 3)
    if f > 0:
        y[:f] *= np.linspace(0, 1, f)
        y[-f:] *= np.linspace(1, 0, f)
    return y


CACHE = {}
SEM = asyncio.Semaphore(6)


async def tts_word(voice, word):
    key = (voice, word)
    if key in CACHE:
        return CACHE[key]
    async with SEM:
        path = os.path.join(HERE, '_tts', '%s_%s.mp3' % (voice.split('-')[2], abs(hash(word)) % 10 ** 8))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        if not os.path.exists(path) or os.path.getsize(path) < 2000:
            c = edge_tts.Communicate(word, voice, rate='-8%')
            await c.save(path)
        d, sr = sf.read(path, dtype='float32')
        if d.ndim > 1:
            d = d.mean(axis=1)
        if sr != SR:
            n = int(len(d) * SR / sr)
            d = np.interp(np.linspace(0, len(d) - 1, n), np.arange(len(d)), d).astype(np.float32)
        CACHE[key] = d
        return d


def line_words(text):
    return [text[i:i + 2] for i in range(0, 8, 2)]


async def main():
    notes, mels, secs = g25.build()
    vocal = [n for n in notes if n['ch'] in (0, 4)]
    sec_per_tick = (60.0 / g25.TEMPO) / g25.PPQ

    # 每段用哪个人声：主歌一/副歌一 = 男，主歌二/副歌二/桥段 = 女，副歌三 = 男女两层
    def voices_for(t0):
        for s in secs:
            if s['t0'] <= t0 < s['t1']:
                tag = s['tag']
                break
        else:
            tag = 'V'
        if tag in ('V', 'C1'):
            return [VOICE_MALE]
        if tag in ('V2', 'C2', 'B'):
            return [VOICE_FEMALE]
        if tag == 'C3':
            return [VOICE_MALE, VOICE_FEMALE]
        return [VOICE_FEMALE]

    total_ticks = max(n['t'] + n['dur'] for n in notes)
    total_samples = int(total_ticks * sec_per_tick * SR) + SR // 5
    vocal_buf = np.zeros(total_samples, dtype=np.float32)
    timeline = []

    jobs = []
    for mi, m in enumerate(mels):
        ph = sorted([x for x in vocal if m['t'] <= x['t'] < m['t'] + 8 * BEAT], key=lambda x: x['t'])
        if len(ph) != 8:
            print('跳过（音符数不是 8）：', m['text']); continue
        words = line_words(m['text'])
        vs = voices_for(m['t'])
        for wi, w in enumerate(words):
            for v in vs:
                jobs.append((mi, wi, w, v))
    print('待合成：%d 个词组' % len(jobs))

    # 并发取词
    await asyncio.gather(*[tts_word(v, w) for (_, _, w, v) in jobs])

    # 逐字贴谱
    for mi, m in enumerate(mels):
        ph = sorted([x for x in vocal if m['t'] <= x['t'] < m['t'] + 8 * BEAT], key=lambda x: x['t'])
        if len(ph) != 8:
            continue
        words = line_words(m['text'])
        vs = voices_for(m['t'])
        seg_infos = []
        for wi, w in enumerate(words):
            for v in vs:
                a = await tts_word(v, w)
                s1, s2 = split_two(a, SR)
                seg_infos.append((wi, v, [s1, s2]))
        # 逐字：找对应 (wi, voice)
        for ci in range(8):
            wi = ci // 2
            t = ph[ci]['t']; dur = ph[ci]['dur']
            tgt_len = max(int(SR * 0.12), int(dur * sec_per_tick * SR * 0.86))
            pitch = ph[ci]['pitch']
            sec_base = m['base']
            semis = pitch - sec_base
            mixes = []
            for (wi2, v, parts) in seg_infos:
                if wi2 != wi:
                    continue
                base_hz = BASE_HZ.get(v, 220.0)
                tgt_hz = base_hz * (2.0 ** (semis / 12.0))
                y = sing_syllable(parts[ci % 2], tgt_hz, tgt_len, SR)
                mixes.append(y)
            if not mixes:
                continue
            n = max(len(y) for y in mixes)
            lay = np.zeros(n, dtype=np.float32)
            for y in mixes:
                lay[:len(y)] += y[:n]
            lay /= max(1, len(mixes))
            st = int(t * sec_per_tick * SR)
            en = min(total_samples, st + n)
            if en > st:
                vocal_buf[st:en] += lay[:en - st]
            timeline.append(dict(line=m['text'], char=m['text'][ci], t=round(t * sec_per_tick, 3),
                                 dur=round(dur * sec_per_tick, 3), midi=pitch))

    # 归一化人声
    peak = float(np.abs(vocal_buf).max())
    if peak > 0:
        vocal_buf *= 0.55 / peak
    out = os.path.join(HERE, 'out'); os.makedirs(out, exist_ok=True)
    sf.write(os.path.join(out, '代唱_v25_人声.wav'), vocal_buf, SR)
    inst, isr = sf.read(os.path.join(HERE, '..', '打工人歌', 'out', '把好日子扛在肩上_v25.wav'), dtype='float32')
    if isr != SR:
        inst = np.interp(np.linspace(0, len(inst) - 1, int(len(inst) * SR / isr)), np.arange(len(inst)), inst).astype(np.float32)
    L = min(len(inst), len(vocal_buf))
    mix = inst[:L] * 0.75 + vocal_buf[:L] * 0.9
    mx = float(np.abs(mix).max())
    if mx > 0.97:
        mix *= 0.97 / mx
    sf.write(os.path.join(out, '代唱_v25_混音.wav'), np.clip(mix, -1, 1), SR)
    sf.write(os.path.join(out, '代唱_v25_混音.mp3'), np.clip(mix, -1, 1), SR, format='MP3')
    with open(os.path.join(out, '代唱_v25_时间轴.json'), 'w', encoding='utf-8') as f:
        json.dump(timeline, f, ensure_ascii=False, indent=1)
    print('完成：人声 %.1f 秒，%.2f MB' % (len(vocal_buf) / SR, os.path.getsize(os.path.join(out, '代唱_v25_人声.wav')) / 1048576.0))


if __name__ == '__main__':
    asyncio.run(main())
