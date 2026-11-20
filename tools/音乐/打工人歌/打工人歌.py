# -*- coding: utf-8 -*-
"""《把好日子扛在肩上》——职场题材，轻快 112BPM，C 调，时长按 3 分钟做。

规矩全部来自已学的格子：
  第14类 副歌音区 ≥ +7 半音、句尾指向强拍、大跳后反向级进
  第15类 主歌 I-vi-IV-V / 副歌 IV-V-iii-vi-ii-V-I（下属开场）
  第16类 主歌减配、副歌加层；副歌前撤一拍；副歌 RMS ≥ 主歌 1.2 倍
  第17类 副歌 classic pop、桥段 half-time
  词曲协同 字=音、词组起头（第1、5字）落强拍、句末长音收强拍

结构（84 小节 = 180.0 秒）：
  前奏8 → 主歌一8 → 副歌一8 → 间奏A8 → 主歌二8 → 副歌二8 → 桥段8 → 间奏B12(渐强) → 副歌三8 → 尾奏8
"""
import importlib.util, math, os, struct, wave

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(
    'arr', os.path.join(HERE, '..', '编配对比', '编配层次.py'))
arr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(arr)

BEAT, PPQ, TEMPO = 480, 480, 112
NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
def p(n):
    return 12 * (int(n[-1]) + 1) + NAMES.index(n[:-1])
def tones(name, octv):
    r = p(name + str(octv))
    return [r, r + 3, r + 7] if name in ('A', 'E', 'D') else [r, r + 4, r + 7]

# ── 词：8 字一句、4+4 断句；主歌押遥条(ao)、副歌/桥段押江阳(ang)
VERSES = [
    ('清早出门天刚放亮', [0, 2, 4, 2, 5, 4, 2, 0]),
    ('一路小跑心里敞亮', [2, 4, 5, 4, 2, 4, 2, 0]),
    ('活再琐碎也做成样', [0, 2, 4, 5, 4, 2, 4, 2]),
    ('抬头笑说今天照常', [2, 0, 2, 0, 0, 2, 0, 0]),
]
VERSES2 = [
    ('下班路上街灯正亮', [0, 2, 5, 4, 2, 4, 2, 0]),
    ('手里的活做得漂亮', [2, 4, 5, 4, 2, 2, 0, 2]),
    ('累了想想家里灯光', [0, 4, 2, 4, 5, 4, 2, 4]),
    ('明天还有新的太阳', [2, 0, 2, 0, 0, 2, 0, 0]),
]
CHORUS = [
    ('好日子就在我肩上', [0, 4, 7, 4, 0, 2, 4, 7]),
    ('一步一寸也是成长', [2, 5, 7, 5, 2, 0, 2, 5]),
    ('风大雨急心不慌忙', [0, 4, 7, 4, 0, 2, 4, 7]),
    ('一盏小灯自己点亮', [4, 7, 5, 2, 0, 2, 5, 5]),
]
BRIDGE = [
    ('平常人自有他的光', [0, 2, 4, 5, 4, 2, 0, 0]),
    ('地铁末班照样赶上', [0, 2, 4, 5, 4, 7, 4, 2]),
    ('工牌一别腰杆更壮', [2, 4, 5, 4, 2, 2, 0, 0]),
    ('一天更比一天更强', [0, 2, 4, 5, 7, 5, 2, 0]),
]
BASE = {'V': 60, 'V2': 60, 'C': 67, 'B': 64}
BASE['C1'], BASE['C2'], BASE['C3'] = 65, 67, 69   # 三遍副歌逐遍抬 2 度：峰 72/74/76（第30类）   # 主歌 C4 / 副歌 G4 / 桥段 E4

PROG_V = [('C', 3), ('A', 3), ('F', 3), ('G', 3)] * 2
PROG_C = [('F', 3), ('G', 3), ('E', 3), ('A', 3), ('D', 3), ('G', 3), ('C', 4), ('C', 4)]
PROG_B = [('A', 3), ('F', 3), ('C', 4), ('G', 3)] * 2
PROG_I = [('C', 3), ('G', 3), ('A', 3), ('F', 3), ('C', 3), ('G', 3), ('F', 3), ('G', 3)]   # 前奏/间奏
PROG_O = [('F', 3), ('G', 3), ('C', 4), ('C', 4), ('C', 4), ('C', 4), ('C', 4), ('C', 4)]   # 尾奏

# 节奏模板：(落拍位置, 时值)，每句 8 字
RHY = {
    'R1': ([0, 1, 2, 3, 4, 5, 5.5, 6], [1, 1, 1, 1, 1, 1, 0.5, 2]),
    'R2': ([0, 0.5, 1, 1.5, 2, 3.5, 4.5, 6], [0.5, 0.5, 0.5, 0.5, 1.5, 1, 1, 2]),
    'R3': ([0, 1, 2, 2.5, 4, 4.5, 5.5, 6.5], [1, 1, 0.5, 1.5, 0.5, 1, 1, 1.5]),
    'R4': ([0, 1, 2, 3, 4, 5, 5.5, 6], [1, 1, 1, 1, 1, 1, 0.5, 1]),
}
VAR_RHY = {'V': 'R2', 'V2': 'R2', 'B': 'R1'}

# 双音色分工（每首 >=2 音色：主歌自然声、副歌少年声）
VOICE = {'V': 4, 'V2': 4, 'B': 4, 'C1': 0, 'C2': 0, 'C3': 0}
VOCAL_CH = (0, 4)
VOICE_GAIN = 1.02


def phrase_notes(base, contour, t0, short_end=False, rhythm='R1'):
    """8 字一句：7 个整拍音 + 第 7 字半拍切分 + 末字 2 拍。
    short_end=True 只用于段末句（进副歌前）：末字只 1 拍，故意留 1 拍空，
    即第 16 类学到的「最响之前先撤掉」。
    """
    beats, dur = RHY[rhythm]
    dur = list(dur)
    if short_end:
        dur[-1] = 1
    out = []
    for i, off in enumerate(contour):
        out.append((t0 + int(beats[i] * BEAT), int(dur[i] * BEAT), base + off))
    return out

# ── 伴奏：和弦 / 低音 / 分解和弦一首歌共用，按 level 决定厚度
LEVEL_AMP = {'intro': 0.80, 'light': 0.5, 'verse': 1.0, 'chorus': 1.9, 'bridge': 1.4, 'mid': 1.2,
             'build': 1.45, 'fadeout': 0.7}

def add_harmony(notes, t, bars, prog, level, ramp=1.0):
    thick = LEVEL_AMP[level]
    for bi in range(bars):
        ct = t + bi * 4 * BEAT
        nm, oc = prog[bi % len(prog)]
        tr = tones(nm, oc)
        k = ramp if (level == 'build') else 1.0
        if level == 'build':          # 渐强：前 4 小节 mid，后 4 小节抬到副歌
            k = 0.85 + (bi / float(bars - 1)) * 0.45
        bass = 0.24 if level in ('chorus', 'build') else (0.12 if level == 'mid' else 0.09)
        notes.append(dict(t=ct, dur=4 * BEAT, pitch=tr[0], ch=1, amp=bass * k, kind='bass'))
        if level in ('chorus', 'build', 'mid'):
            notes.append(dict(t=ct + 2 * BEAT, dur=2 * BEAT, pitch=tr[0], ch=1, amp=bass * 0.62 * k, kind='bass'))
        for q in tr:
            notes.append(dict(t=ct, dur=4 * BEAT, pitch=q + 12, ch=2, amp=0.12 * thick * k))
        if level in ('chorus', 'build') and bi % 2 == 0:
            notes.append(dict(t=ct, dur=4 * BEAT, pitch=tr[2] + 24, ch=2, amp=0.05 * k))
        # 间奏/前奏/尾奏用分解和弦把空出来的旋律位填上（不抢人声位置，只在中高区轻点）
        if level in ('intro', 'light', 'mid', 'build', 'fadeout'):
            for bi2, idx in enumerate((0, 1, 2, 0)):
                notes.append(dict(t=ct + bi2 * BEAT, dur=int(0.9 * BEAT), pitch=tr[idx] + (24 if bi2 == 3 else 12),
                                  ch=2, amp=0.055 * thick * k))
    return notes

def add_drums(notes, t, bars, level):
    for bi in range(bars):
        ct = t + bi * 4 * BEAT
        k = 1.0
        if level == 'build':
            k = 0.55 + (bi / float(bars - 1)) * 0.40
        if level == 'fadeout':
            k = max(0.0, 0.6 - bi / float(bars - 1) * 0.7)
        def hit(b, kind, amp):
            if k <= 0:
                return
            notes.append(dict(t=ct + int(b * BEAT), dur=int(0.25 * BEAT), pitch=0, ch=3,
                              amp=amp * k, kind=kind))
        if level in ('chorus', 'build', 'mid'):
            hit(0, 'k', 0.60); hit(1, 's', 0.34); hit(2, 'k', 0.52); hit(3, 's', 0.34)
        elif level == 'bridge':                      # half-time：军鼓只在第 3 拍
            hit(0, 'k', 0.55); hit(2, 's', 0.36)
        elif level == 'verse':
            hit(0, 'k', 0.26)
        elif level == 'intro':                    # 前奏：四拍底鼓 + 反拍军鼓，先把律动立起来
            hit(0, 'k', 0.34); hit(1, 's', 0.18); hit(2, 'k', 0.30); hit(3, 's', 0.18)
        elif level == 'light':
            hit(0, 'k', 0.30); hit(2, 'k', 0.30)
        for hb in (0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5):
            if level in ('chorus', 'mid', 'build'):
                hit(hb, 'h', 0.14)
            elif level in ('bridge', 'verse', 'fadeout', 'light', 'intro'):
                if hb in (0.0, 2.0):
                    hit(hb, 'h', 0.06 if level != 'bridge' else 0.10)
    return notes

def add_hook_tease(notes, t, contour, base=67, amp=0.28):
    """前奏把副歌钩子以器乐形态点一遍（第 18 类 Cursa：tease 1-2 hits of main hook）"""
    for i, off in enumerate(contour):
        notes.append(dict(t=t + i * BEAT, dur=int(0.9 * BEAT), pitch=base + off, ch=0, amp=amp))
    return notes

def build():
    notes, mel_meta, secs = [], [], []
    t = 0
    plan = [
        ('I1', 'inst', PROG_I, 8, 'intro', None),
        ('V',  'lyric', PROG_V, 8, 'verse', VERSES),
        ('C1', 'lyric', PROG_C, 8, 'chorus', CHORUS),
        ('I2', 'inst', PROG_I, 8, 'mid', None),
        ('V2', 'lyric', PROG_V, 8, 'verse', VERSES2),
        ('C2', 'lyric', PROG_C, 8, 'chorus', CHORUS),
        ('B',  'lyric', PROG_B, 8, 'bridge', BRIDGE),
        ('I3', 'inst', PROG_C, 12, 'build', None),
        ('C3', 'lyric', PROG_C, 8, 'chorus', CHORUS),
        ('O',  'inst', PROG_O, 8, 'fadeout', None),
    ]
    for tag, kind, prog, bars, level, lines in plan:
        start = t
        notes = add_harmony(notes, t, bars, prog, level)
        notes = add_drums(notes, t, bars, level)
        if tag == 'I1':                      # 前奏：两小节立律动，再点钩子
            notes = add_hook_tease(notes, t + 2 * 4 * BEAT, CHORUS[0][1])
        if kind == 'lyric':
            chorus = (tag.startswith('C'))
            base = BASE[tag] if tag in BASE else BASE['V' if tag == 'V2' else 'C']
            for li, (text, contour) in enumerate(lines):
                t0 = t + li * 8 * BEAT
                sec_last = (li == len(lines) - 1) and (not chorus)
                rhy = 'R4' if sec_last else ('R3' if chorus else VAR_RHY.get(tag, 'R1'))
                vch = VOICE.get(tag, 0)
                for (nt, nd, pi) in phrase_notes(base, contour, t0, short_end=sec_last, rhythm=rhy):
                    notes.append(dict(t=nt, dur=nd, pitch=pi, ch=vch,
                                      amp=(0.38 if chorus else 0.24) * (VOICE_GAIN if vch == 4 else 1.0)))
                mel_meta.append(dict(text=text, t=t0, base=base, chorus=chorus,
                                     peaks=max(base + o for o in contour)))
        secs.append(dict(tag=tag, kind=kind, level=level, t0=start,
                         t1=t + bars * 4 * BEAT, bars=bars))
        t += bars * 4 * BEAT
    return notes, mel_meta, secs

def verify(notes, mel):
    ok = True
    print('══ 词曲协同 ══')
    for i, m in enumerate(mel):
        line = m['text']
        assert len(line) == 8, '每句必须 8 字：%s' % line
        ph = sorted([x for x in notes if x['ch'] in VOCAL_CH and m['t'] <= x['t'] < m['t'] + 8 * BEAT],
                    key=lambda x: x['t'])
        assert len(ph) == 8, '%s 音符数不是 8' % line
        beats = [(x['t'] - m['t']) / float(BEAT) for x in ph]
        w1, w5 = beats[0], beats[4]
        ok_word = (abs(w1 % 4) < 1e-9 or abs(w1 % 2) < 1e-9) and abs(w5 % 2) < 1e-9
        end = (ph[-1]['t'] - m['t']) / float(BEAT) + ph[-1]['dur'] / float(BEAT)
        at_junction = (i == 3 or i == 11 or i == 19)     # 段末句，下一段是副歌
        need = 1.0 if at_junction else 1.5
        ok_end = ph[-1]['dur'] / float(BEAT) >= need and (
            abs(end % 2) < 1e-6 if not at_junction else (abs(end - 7) < 1e-6))
        print('%2d %s「%s」 起拍%s 词组%s 末音%.1f拍收%.0f %s'
              % (i, '副' if m['chorus'] else '主', line,
                 '%.1f/%.1f' % (w1, w5), '✓' if ok_word else '✗',
                 ph[-1]['dur'] / float(BEAT), end, '✓' if ok_end else '✗'))
        ok = ok and ok_word and ok_end
    vmax = max(m['peaks'] for m in mel if not m['chorus'] and m['base'] == 60)
    cmax = max(m['peaks'] for m in mel if m['chorus'])
    span = max(x['pitch'] for x in notes if x['ch'] in VOCAL_CH) - min(x['pitch'] for x in notes if x['ch'] in VOCAL_CH)
    print('副歌峰值 %d − 主歌峰值 %d = %d 半音（≥7） | 全曲音域 %d 半音（≤16）'
          % (cmax, vmax, cmax - vmax, span))
    return ok and (cmax - vmax >= 7) and span <= 16

def main():
    out = os.path.join(HERE, 'out')
    os.makedirs(out, exist_ok=True)
    notes, mel, secs = build()
    assert verify(notes, mel), '词曲协同不过，不许出片'
    wav = os.path.join(out, '把好日子扛在肩上.wav')
    mid = os.path.join(out, '把好日子扛在肩上.mid')
    arr.TEMPO = TEMPO          # 渲染模块用自己的全局 TEMPO(84)，必须覆盖成 112
    length, g = arr.render(notes, wav)
    spec2 = importlib.util.spec_from_file_location(
        'cl', os.path.join(HERE, '..', '和弦对比', 'chord_lib.py'))
    cl = importlib.util.module_from_spec(spec2); spec2.loader.exec_module(cl)
    cl.write_mid([dict(t=x['t'], dur=x['dur'], pitch=x['pitch'], vel=90,
                       ch=0 if x['ch'] in VOCAL_CH else (1 if x['ch'] in (1, 2) else 2))
                  for x in notes if x['ch'] != 3], PPQ, mid, TEMPO)
    w = wave.open(wav, 'rb'); n = w.getnframes()
    s = struct.unpack('<%dh' % n, w.readframes(n)); w.close()
    sr = w.getframerate()
    sec = n / float(sr)
    bars = sum(x['bars'] for x in secs)
    print('WAV %.2f 秒 %d 字节，增益 %.2f | 小节 %d' % (sec, os.path.getsize(wav), g, bars))
    # 分段 RMS（按小节边界，绝对可靠；不再依赖"段号换算"）
    def rms_of(a, b):
        seg = s[int(a * 4 * 60.0 / TEMPO * sr):int(b * 4 * 60.0 / TEMPO * sr)]
        return math.sqrt(sum(x * x for x in seg) / max(1, len(seg)))
    per = {}
    bar0 = 0
    for x in secs:
        per.setdefault(x['tag'], []).append(rms_of(bar0, bar0 + x['bars']))
        bar0 += x['bars']
    verse_rms = min(per['V'] + per['V2'])
    chorus_rms = min(per['C1'] + per['C2'] + per['C3'])
    inst_max = max(max(per[k]) for k in ('I1', 'I2', 'I3', 'O'))
    print('主歌 RMS %.0f | 副歌 RMS %.0f | 比值 %.2f（要求 ≥1.2）'
          % (verse_rms, chorus_rms, chorus_rms / verse_rms))
    print('间奏/前奏/尾奏最大 RMS %.0f（必须低于副歌 %.0f）' % (inst_max, chorus_rms))
    intro_rms = per['I1'][0]
    intro_db = 20 * math.log10(intro_rms / chorus_rms)
    print('前奏 RMS %.0f，比副歌低 %.1f dB（要求 6–12 dB 余量）' % (intro_rms, -intro_db))
    print('时长 %.2f 秒（要求 170–200 秒 ≈ 3 分钟）' % sec)
    assert chorus_rms >= verse_rms * 1.2, '副歌没压过主歌'
    assert inst_max < chorus_rms, '间奏比副歌还响，抢戏了'
    assert 6 <= -intro_db <= 12, '前奏动态余量不在 6–12 dB（第18类 C3）'
    assert 170 <= sec <= 200, '时长不在 3 分钟档'
    print('自校验全过：3 分钟档 / 副歌压过主歌 / 间奏不抢戏')
    print('峰值 %d (%.0f%%)' % (max(abs(x) for x in s), max(abs(x) for x in s) / 327.67))

if __name__ == '__main__':
    main()
