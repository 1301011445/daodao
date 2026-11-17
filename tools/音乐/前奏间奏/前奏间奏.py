# -*- coding: utf-8 -*-
"""第 18 类实测：三版前奏对比，量长度 / 钩子出现时间 / 动态余量(dB) / 层数。
判据见 乐谱学习_第18类_前奏间奏与尾奏.md
"""
import importlib.util, math, os, struct, wave

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(
    'arr', os.path.join(HERE, '..', '编配对比', '编配层次.py'))
arr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(arr)

BEAT, TEMPO = 480, 112
SR = 44100
NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
def p(n): return 12 * (int(n[-1]) + 1) + NAMES.index(n[:-1])
def tones(name, octv):
    r = p(name + str(octv))
    return [r, r + 3, r + 7] if name in ('A', 'E', 'D') else [r, r + 4, r + 7]

PROG = [('C', 3), ('G', 3), ('A', 3), ('F', 3), ('C', 3), ('G', 3), ('F', 3), ('G', 3)]
HOOK = [0, 2, 4, 2, 7, 5, 7, 4]        # 副歌钩子的轮廓（第 14/16 类里定下来的）
BASE_HOOK = 67                          # 副歌 G4

def arp(notes, bars, amp=0.055):
    for bi in range(bars):
        ct = bi * 4 * BEAT
        tr = tones(*PROG[bi % len(PROG)])
        for k, idx in enumerate((0, 1, 2, 0)):
            notes.append(dict(t=ct + k * BEAT, dur=int(0.9 * BEAT), pitch=tr[idx] + (24 if k == 3 else 12),
                              ch=2, amp=amp))
    return notes

def hook_hits(notes, bars, amp=0.30, hits=2):
    """把副歌钩子点 1-2 下（器乐形态），每 8 字点前 4 字"""
    for h in range(hits):
        t0 = h * 4 * BEAT
        for i in range(4):
            notes.append(dict(t=t0 + i * BEAT, dur=int(0.9 * BEAT), pitch=BASE_HOOK + HOOK[i],
                              ch=0, amp=amp))
    return notes

def hats(notes, bars, amp=0.06):
    for bi in range(bars):
        for hb in (0.0, 2.0):
            notes.append(dict(t=bi * 4 * BEAT + int(hb * BEAT), dur=int(0.12 * BEAT), pitch=0,
                              ch=3, amp=amp, kind='h'))
    return notes

def chorus_ref(notes, bars):
    """副歌参照段：满配置（和弦+低音+16分踩镲+底鼓军鼓+旋律钩子两层声部）"""
    t0 = bars * 4 * BEAT
    for bi in range(bars):
        ct = t0 + bi * 4 * BEAT
        tr = tones(*PROG[bi % len(PROG)])
        notes.append(dict(t=ct, dur=4 * BEAT, pitch=tr[0], ch=1, amp=0.24, kind='bass'))
        notes.append(dict(t=ct + 2 * BEAT, dur=2 * BEAT, pitch=tr[0], ch=1, amp=0.15, kind='bass'))
        for q in tr:
            notes.append(dict(t=ct, dur=4 * BEAT, pitch=q + 12, ch=2, amp=0.12))
        for b, kind, amp in [(0, 'k', 0.60), (1, 's', 0.34), (2, 'k', 0.52), (3, 's', 0.34)]:
            notes.append(dict(t=ct + b * BEAT, dur=int(0.25 * BEAT), pitch=0, ch=3, amp=amp, kind=kind))
        for hb in (0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5):
            notes.append(dict(t=ct + int(hb * BEAT), dur=int(0.12 * BEAT), pitch=0, ch=3, amp=0.14, kind='h'))
        for i in range(3):
            notes.append(dict(t=ct + i * BEAT, dur=BEAT, pitch=BASE_HOOK + HOOK[i], ch=0, amp=0.38))
    return notes

def build(variant):
    notes = []
    if variant == 'A':
        bars, layers = 8, 2
        notes = arp(notes, bars)
        notes = hats(notes, bars)
    elif variant == 'B':
        bars, layers = 4, 2
        notes = arp(notes, bars)
        notes = hook_hits(notes, bars, amp=0.30, hits=2)
        notes = hats(notes, bars)
    elif variant == 'C':
        bars, layers = 8, 3
        notes = arp(notes, bars)
        notes = hook_hits(notes, bars, amp=0.30, hits=2)
        notes = hats(notes, bars)
        for bi in range(bars):
            ct = bi * 4 * BEAT
            notes.append(dict(t=ct, dur=int(0.25 * BEAT), pitch=0, ch=3, amp=0.50, kind='k'))
            notes.append(dict(t=ct + 2 * BEAT, dur=int(0.25 * BEAT), pitch=0, ch=3, amp=0.50, kind='k'))
    notes = chorus_ref(notes, 8)
    return notes, bars, layers

def render_measure(variant):
    notes, bars, layers = build(variant)
    arr.TEMPO = TEMPO
    wav = os.path.join(HERE, 'out', '前奏_%s.wav' % variant)
    os.makedirs(os.path.join(HERE, 'out'), exist_ok=True)
    length, g = arr.render(notes, wav)
    w = wave.open(wav, 'rb'); n = w.getnframes()
    s = struct.unpack('<%dh' % n, w.readframes(n)); w.close()
    sr = w.getframerate()
    def rms(a_sec, b_sec):
        seg = s[int(a_sec * sr):int(b_sec * sr)]
        return math.sqrt(sum(x * x for x in seg) / max(1, len(seg))) if seg else 0.0
    intro_sec = bars * 4 * 60.0 / TEMPO
    chorus_sec = 8 * 4 * 60.0 / TEMPO
    intro_rms = rms(0.2, intro_sec)
    chorus_rms = rms(intro_sec + 0.2, intro_sec + chorus_sec)
    db = 20 * math.log10(intro_rms / chorus_rms)
    # 钩子材料第一次出现的秒数（ch0 在间奏段里的第一个音）
    hook_t = min([x['t'] for x in notes if x['ch'] == 0 and x['t'] < bars * 4 * BEAT], default=None)
    hook_sec = None if hook_t is None else hook_t / float(BEAT) * 60.0 / TEMPO
    return dict(variant=variant, bars=bars, layers=layers, intro_rms=intro_rms,
                chorus_rms=chorus_rms, db=db, hook_sec=hook_sec, sec=intro_sec)

if __name__ == '__main__':
    print('版本 | 长度(小节) | 钩子材料首现 | 前奏RMS | 副歌RMS | 相对dB | 层数 | C1 | C2 | C3')
    print('--- | --- | --- | --- | --- | --- | --- | --- | --- | ---')
    for v in ('A', 'B', 'C'):
        r = render_measure(v)
        c1 = '✓' if 4 <= r['bars'] <= 8 else '✗'
        c2 = '✓' if (r['hook_sec'] is not None and r['hook_sec'] <= 8.6) else '✗'
        c3 = '✓' if -12 <= r['db'] <= -6 else '✗'
        print('%s | %d | %s | %d | %d | %.1f dB | %d | %s | %s | %s'
              % (r['variant'], r['bars'],
                 ('%.1f 秒' % r['hook_sec']) if r['hook_sec'] is not None else '无（%.1f 秒才出人声）' % r['sec'],
                 r['intro_rms'], r['chorus_rms'], r['db'], r['layers'], c1, c2, c3))
    print('\n判据来源：MusicProductionWiki（6–12 dB 余量、8 秒内出钩子）、Cursa（tease 1–2 hits）、Plutony（各段有活）')
    print('注：dB 是拿本曲副歌当参照的**相对**值，不是 LUFS 绝对值。')
