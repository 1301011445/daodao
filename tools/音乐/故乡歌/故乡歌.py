# -*- coding: utf-8 -*-
"""《归途的月光》——乡愁/故乡题材，民谣向 92BPM，C 调，时长按 3 分钟档做。

与职场版《把好日子扛在肩上》刻意区分：
  题材：乡愁（婉转/深沉底色，不做喊口号式励志）
  曲风：民谣，I-V-vi-IV 循环，鼓更轻，副歌靠旋律抬而不是靠堆音量
  旋律：副歌钩子 G-B-D-B-G-A-B-D 落地后回落，第 3 句复用钩子

结构（72 小节 = 187.8 秒）：
  前奏8 → 主歌一8 → 副歌一8 → 间奏A8 → 主歌二8 → 副歌二8 → 桥段8 → 副歌三8 → 尾奏8
"""
import importlib.util, math, os, struct, wave

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(
    'arr', os.path.join(HERE, '..', '编配对比', '编配层次.py'))
arr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(arr)

BEAT, PPQ, TEMPO = 480, 480, 92
NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
def p(n):
    return 12 * (int(n[-1]) + 1) + NAMES.index(n[:-1])
def tones(name, octv):
    r = p(name + str(octv))
    return [r, r + 3, r + 7] if name in ('A', 'E', 'D') else [r, r + 4, r + 7]

# ── 词：8 字一句、4+4 断句；主歌押 ie/ang 松散，副歌回旋钩子
VERSES = [
    ('村口老树又添新叶', [0, 2, 5, 4, 2, 4, 2, 0]),
    ('谁家炊烟飘过山缺', [2, 4, 5, 4, 2, 4, 2, 0]),
    ('我在城里走了很远', [0, 2, 5, 4, 4, 2, 4, 0]),
    ('梦里还是那条老街', [5, 4, 2, 0, 0, 2, 0, 0]),
]
VERSES2 = [
    ('电话里说家里都好', [0, 2, 5, 4, 5, 4, 2, 0]),
    ('放下碗筷又想起家', [2, 4, 5, 4, 5, 2, 0, 0]),
    ('这些年跑得太匆忙', [0, 2, 5, 4, 5, 4, 0, 0]),
    ('欠了家里好多句话', [2, 4, 5, 0, 0, 2, 0, 0]),
]
CHORUS = [
    ('故乡的月光照着我', [0, 2, 4, 5, 7, 5, 2, 0]),
    ('一碗热汤暖到心窝', [2, 4, 5, 4, 7, 5, 4, 0]),
    ('走多远都记得回头', [0, 2, 4, 5, 7, 5, 2, 0]),
    ('家在心上不曾远走', [5, 4, 0, 2, 5, 2, 0, 0]),
]
# 副歌二：前三句不动（保住钩子），第 4 句不回落，抬到 7 交给桥段
CHORUS2 = [
    ('故乡的月光照着我', [0, 2, 4, 5, 7, 5, 2, 0]),
    ('一碗热汤暖到心窝', [2, 4, 5, 4, 7, 5, 4, 0]),
    ('走多远都记得回头', [0, 2, 4, 5, 7, 5, 2, 0]),
    ('家在心上不曾远走', [5, 4, 2, 0, 5, 7, 5, 7]),
]
# 副歌三：整段升 2 个半音（转 D）作全曲最高潮，第 4 句仍悬在 7 上收
CHORUS3 = [
    ('故乡的月光照着我', [0, 2, 4, 5, 7, 5, 2, 0]),
    ('一碗热汤暖到心窝', [2, 4, 5, 4, 7, 5, 4, 0]),
    ('走多远都记得回头', [0, 2, 4, 5, 7, 5, 2, 0]),
    ('家在心上不曾远走', [5, 4, 2, 0, 5, 7, 5, 7]),
]
BRIDGE = [
    ('老屋门前的石板路', [0, 4, 5, 4, 5, 4, 2, 0]),
    ('记着我光脚的模样', [0, 2, 4, 5, 5, 2, 0, 0]),
    ('走得再远也是故乡', [2, 4, 5, 2, 5, 0, 2, 0]),
    ('一年更比一年想家', [0, 2, 4, 0, 5, 2, 0, 0]),
]
# 每句的情感重音字（0 起算）：必须落在强拍、且音高在句子的上半区
STRESS = {'V': [2, 2, 2, 0], 'V2': [4, 4, 2, 2], 'C': [4, 4, 4, 0], 'B': [4, 4, 4, 4]}

BASE = {'V': 60, 'V2': 60, 'C1': 67, 'C2': 67, 'C3': 69, 'B': 64}

# 民谣循环：主歌 I-V-vi-IV；副歌 下属开场再回主音；桥段 vi-IV-I-V
PROG_V = [('C', 3), ('G', 3), ('A', 3), ('F', 3)] * 2
PROG_C = [('F', 3), ('G', 3), ('C', 4), ('A', 3), ('F', 3), ('G', 3), ('C', 4), ('C', 4)]
PROG_B = [('A', 3), ('F', 3), ('C', 4), ('G', 3)] * 2
PROG_I = [('C', 3), ('G', 3), ('A', 3), ('F', 3), ('C', 3), ('G', 3), ('F', 3), ('G', 3)]
PROG_O = [('F', 3), ('G', 3), ('C', 4), ('C', 4), ('C', 4), ('C', 4), ('C', 4), ('C', 4)]

def trans(name, octv, n):
    """和弦名整体上移 n 个半音，跨八度自动进位。"""
    idx = NAMES.index(name) + n
    return NAMES[idx % 12], octv + idx // 12

def trans_prog(prog, n):
    return [trans(nm, oc, n) for (nm, oc) in prog]

PROG_C3 = trans_prog(PROG_C, 2)      # 副歌三：整段升 2 半音到 D 调

# 节奏模板：(落拍位置, 时值)，每句 8 字
RHY = {
    'R1': ([0, 1, 2, 3, 4, 5, 5.5, 6], [1, 1, 1, 0.5, 1, 1, 0.5, 2]),
    'R2': ([0, 0.5, 1, 1.5, 2, 3.5, 4.5, 6], [0.5, 0.5, 0.5, 0.25, 1.5, 1, 1, 2]),
    'R3': ([0, 1, 2, 2.5, 4, 4.5, 5.5, 6.5], [1, 1, 0.5, 0.5, 0.5, 1, 1, 1.5]),
    'R4': ([0, 1, 2, 3, 4, 5, 5.5, 6], [1, 1, 1, 0.6, 1, 1, 0.5, 1]),
    'R5': ([0, 1, 2, 3, 4, 5, 5.5, 6], [1, 1, 1, 0.6, 1, 1, 0.5, 2]),   # 同 R4 的附点推进，末音留 2 拍（非段末句用）
}
VAR_RHY = {'V': 'R1', 'V2': 'R5', 'B': 'R2'}

def phrase_notes(base, contour, t0, short_end=False, rhythm='R1'):
    """8 字一句，按节奏模板落拍；段末句末音收 1 拍留白。"""
    beats, dur = RHY[rhythm]
    dur = list(dur)
    if short_end:
        dur[-1] = 1
    out = []
    for i, off in enumerate(contour):
        out.append((t0 + int(beats[i] * BEAT), int(dur[i] * BEAT), base + off))
    return out

# ── 伴奏：和弦 / 低音 / 分解和弦一首歌共用，按 level 决定厚度
LEVEL_AMP = {'intro': 0.80, 'light': 0.5, 'verse': 0.95, 'chorus': 1.75, 'bridge': 1.3, 'mid': 1.15,
             'build': 1.45, 'fadeout': 0.7}

def add_harmony(notes, t, bars, prog, level, ramp=1.0):
    thick = LEVEL_AMP[level]
    for bi in range(bars):
        ct = t + bi * 4 * BEAT
        nm, oc = prog[bi % len(prog)]
        tr = tones(nm, oc)
        k = 1.0
        bass = 0.24 if level in ('chorus', 'build') else (0.11 if level == 'mid' else 0.08)
        notes.append(dict(t=ct, dur=4 * BEAT, pitch=tr[0], ch=1, amp=bass * k, kind='bass'))
        if level in ('chorus', 'build', 'mid'):
            notes.append(dict(t=ct + 2 * BEAT, dur=2 * BEAT, pitch=tr[0], ch=1, amp=bass * 0.62 * k, kind='bass'))
        for q in tr:
            notes.append(dict(t=ct, dur=4 * BEAT, pitch=q + 12, ch=2, amp=0.12 * thick * k))
        if level in ('chorus', 'build') and bi % 2 == 0:
            notes.append(dict(t=ct, dur=4 * BEAT, pitch=tr[2] + 24, ch=2, amp=0.05 * k))
        if level in ('intro', 'light', 'mid', 'fadeout'):
            for bi2, idx in enumerate((0, 1, 2, 0)):
                notes.append(dict(t=ct + bi2 * BEAT, dur=int(0.9 * BEAT), pitch=tr[idx] + (24 if bi2 == 3 else 12),
                                  ch=2, amp=0.055 * thick * k))
    return notes

def add_drums(notes, t, bars, level):
    for bi in range(bars):
        ct = t + bi * 4 * BEAT
        k = 1.0
        if level == 'fadeout':
            k = max(0.0, 0.6 - bi / float(bars - 1) * 0.7)
        def hit(b, kind, amp):
            if k <= 0:
                return
            notes.append(dict(t=ct + int(b * BEAT), dur=int(0.25 * BEAT), pitch=0, ch=3,
                              amp=amp * k, kind=kind))
        if level in ('chorus', 'mid'):
            hit(0, 'k', 0.48); hit(1, 's', 0.24); hit(2, 'k', 0.42); hit(3, 's', 0.24)
        elif level == 'bridge':
            hit(0, 'k', 0.46); hit(2, 's', 0.28)
        elif level == 'verse':
            hit(0, 'k', 0.22)
        elif level == 'intro':
            hit(0, 'k', 0.28); hit(2, 'k', 0.24)
        elif level == 'light':
            hit(0, 'k', 0.26); hit(2, 'k', 0.26)
        for hb in (0.0, 1.0, 2.0, 3.0):
            if level in ('chorus', 'mid'):
                hit(hb, 'h', 0.10)
            elif level in ('bridge', 'verse', 'fadeout', 'light', 'intro') and hb in (0.0, 2.0):
                hit(hb, 'h', 0.05 if level != 'bridge' else 0.08)
    return notes

def build_intro(notes, t):
    """归途性格的前奏（4 小节 ≈ 10.4 秒）：列车/脚步律动 + 远处汽笛 + 钩子影子 + 上行引子。
    目的：一开口先听到"在路上"，不是空等；4 小节内出现钩子，符合第23/24类判据。
    """
    # ① 列车律动：底鼓 0/2 拍、八分反拍轻 hi-hat 拟"咣当"感，比正式段落薄
    for bi in range(4):
        ct = t + bi * 4 * BEAT
        notes.append(dict(t=ct, dur=int(0.3 * BEAT), pitch=0, ch=3, amp=0.20, kind='k'))
        notes.append(dict(t=ct + 2 * BEAT, dur=int(0.3 * BEAT), pitch=0, ch=3, amp=0.17, kind='k'))
        for hb in (0.5, 1.5, 2.5, 3.5):
            notes.append(dict(t=ct + int(hb * BEAT), dur=int(0.15 * BEAT), pitch=0, ch=3,
                              amp=0.07 + 0.02 * bi, kind='h'))
    # ② 远处汽笛：长音 72(G4) 一记，音量很轻，像站台外的回响
    notes.append(dict(t=t, dur=int(7 * BEAT), pitch=72, ch=2, amp=0.05))
    notes.append(dict(t=t + int(0.5 * BEAT), dur=int(6 * BEAT), pitch=67, ch=2, amp=0.035))
    # ③ 钩子影子：第 2 小节起只点钩子前 4 个音（不整句剧透）
    for i, off in enumerate(CHORUS[0][1][:4]):
        notes.append(dict(t=t + 4 * BEAT + i * BEAT, dur=int(0.9 * BEAT), pitch=67 + off, ch=0, amp=0.20))
    # ④ 上行引子：最后半小节四音爬升，直接接到主歌第一字(C4)
    lead = [60, 62, 64, 67]
    for i, pi in enumerate(lead):
        notes.append(dict(t=t + 3 * 4 * BEAT + int((2 + i * 0.5) * BEAT), dur=int(0.45 * BEAT),
                          pitch=pi, ch=0, amp=0.16))
    return notes

def add_hook_tease(notes, t, contour, base=67, amp=0.26):
    """前奏把副歌钩子以器乐形态点一遍"""
    for i, off in enumerate(contour):
        notes.append(dict(t=t + i * BEAT, dur=int(0.9 * BEAT), pitch=base + off, ch=0, amp=amp))
    return notes

def build():
    notes, mel_meta, secs = [], [], []
    t = 0
    plan = [
        ('I1', 'inst', PROG_I, 4, 'intro', None),
        ('V',  'lyric', PROG_V, 8, 'verse', VERSES),
        ('C1', 'lyric', PROG_C, 8, 'chorus', CHORUS),
        ('I2', 'inst', PROG_I, 8, 'mid', None),
        ('V2', 'lyric', PROG_V, 8, 'verse', VERSES2),
        ('C2', 'lyric', PROG_C, 8, 'chorus', CHORUS2),
        ('B',  'lyric', PROG_B, 8, 'bridge', BRIDGE),
        ('C3', 'lyric', PROG_C3, 8, 'chorus', CHORUS3),
        ('O',  'inst', PROG_O, 8, 'fadeout', None),
    ]
    for tag, kind, prog, bars, level, lines in plan:
        start = t
        notes = add_harmony(notes, t, bars, prog, level)
        notes = add_drums(notes, t, bars, level)
        if tag == 'I1':
            notes = build_intro(notes, t)
        if kind == 'lyric':
            chorus = (tag.startswith('C'))
            base = BASE.get(tag, BASE['C1'])
            for li, (text, contour) in enumerate(lines):
                t0 = t + li * 8 * BEAT
                sec_last = (li == len(lines) - 1) and (not chorus)
                rhy = 'R4' if sec_last else ('R3' if chorus else VAR_RHY.get(tag, 'R1'))
                for (nt, nd, pi) in phrase_notes(base, contour, t0, short_end=sec_last, rhythm=rhy):
                    notes.append(dict(t=nt, dur=nd, pitch=pi, ch=0,
                                      amp=0.36 if chorus else 0.26))
                mel_meta.append(dict(text=text, t=t0, base=base, chorus=chorus, tag=tag,
                                     peaks=max(base + o for o in contour)))
        secs.append(dict(tag=tag, kind=kind, level=level, t0=start,
                         t1=t + bars * 4 * BEAT, bars=bars))
        t += bars * 4 * BEAT
    return notes, mel_meta, secs

STRONG_BEATS = (0, 2, 4)
STABLE_END = {0, 5, 7}

def verify_lyric_fit(notes, mel, sec_tags):
    """词曲适配：曲调顺着词走，而不是把同一套音高套在所有句子上。"""
    ok = True
    print('══ 词曲适配 ══')
    for i, m in enumerate(mel):
        ph = sorted([x for x in notes if x['ch'] == 0 and m['t'] <= x['t'] < m['t'] + 8 * BEAT],
                    key=lambda x: x['t'])
        tg = sec_tags[i]
        key = 'C' if tg.startswith('C') else tg      # C1/C2/C3 统一按副歌的适配表
        tag = key
        si = STRESS[key][i % 4]
        beat4 = (ph[3]['t'] - m['t']) / float(BEAT) + ph[3]['dur'] / float(BEAT)
        beat5 = (ph[4]['t'] - m['t']) / float(BEAT)
        gap = beat5 - beat4
        keybeat = (ph[si]['t'] - m['t']) / float(BEAT)
        keypitch = ph[si]['pitch'] - m['base']
        endoff = ph[-1]['pitch'] - m['base']
        ok_gap = gap >= 0.25
        ok_stress = (keybeat in STRONG_BEATS) and keypitch >= 4
        ok_end = endoff in STABLE_END
        print('%2d「%s」 断句空档%.2f拍%s 重音字%d 落拍%.0f 高%d%s 末音%d%s'
              % (i, m['text'], gap, '✓' if ok_gap else '✗', si + 1, keybeat, keypitch,
                 '✓' if ok_stress else '✗', endoff, '✓' if ok_end else '✗'))
        ok = ok and ok_gap and ok_stress and ok_end
    return ok

def verify(notes, mel):
    ok = True
    print('══ 词曲协同 ══')
    for i, m in enumerate(mel):
        line = m['text']
        assert len(line) == 8, '每句必须 8 字：%s' % line
        ph = sorted([x for x in notes if x['ch'] == 0 and m['t'] <= x['t'] < m['t'] + 8 * BEAT],
                    key=lambda x: x['t'])
        assert len(ph) == 8, '%s 音符数不是 8' % line
        beats = [(x['t'] - m['t']) / float(BEAT) for x in ph]
        w1, w5 = beats[0], beats[4]
        ok_word = (abs(w1 % 2) < 1e-9) and abs(w5 % 2) < 1e-9
        end = (ph[-1]['t'] - m['t']) / float(BEAT) + ph[-1]['dur'] / float(BEAT)
        at_junction = (i == 3 or i == 11 or i == 19)
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
    span = max(x['pitch'] for x in notes if x['ch'] == 0) - min(x['pitch'] for x in notes if x['ch'] == 0)
    print('副歌峰值 %d − 主歌峰值 %d = %d 半音（≥7） | 全曲音域 %d 半音（≤16）'
          % (cmax, vmax, cmax - vmax, span))
    return ok and (cmax - vmax >= 7) and span <= 16

def main():
    out = os.path.join(HERE, 'out')
    os.makedirs(out, exist_ok=True)
    notes, mel, secs = build()
    assert verify(notes, mel), '词曲协同不过，不许出片'
    assert verify_lyric_fit(notes, mel, [m['tag'] for m in mel]), '词曲适配不过，不许出片'
    wav = os.path.join(out, '归途的月光.wav')
    mid = os.path.join(out, '归途的月光.mid')
    arr.TEMPO = TEMPO          # 渲染模块用自己的全局 TEMPO，必须覆盖
    length, g = arr.render(notes, wav)
    spec2 = importlib.util.spec_from_file_location(
        'cl', os.path.join(HERE, '..', '和弦对比', 'chord_lib.py'))
    cl = importlib.util.module_from_spec(spec2); spec2.loader.exec_module(cl)
    cl.write_mid([dict(t=x['t'], dur=x['dur'], pitch=x['pitch'], vel=90,
                       ch=0 if x['ch'] == 0 else (1 if x['ch'] in (1, 2) else 2))
                  for x in notes if x['ch'] != 3], PPQ, mid, TEMPO)
    w = wave.open(wav, 'rb'); n = w.getnframes()
    s = struct.unpack('<%dh' % n, w.readframes(n)); w.close()
    sr = w.getframerate()
    sec = n / float(sr)
    bars = sum(x['bars'] for x in secs)
    print('WAV %.2f 秒 %d 字节，增益 %.2f | 小节 %d' % (sec, os.path.getsize(wav), g, bars))
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
    inst_max = max(max(per[k]) for k in ('I1', 'I2', 'O'))
    print('主歌 RMS %.0f | 副歌 RMS %.0f | 比值 %.2f（要求 ≥1.2）'
          % (verse_rms, chorus_rms, chorus_rms / verse_rms))
    print('间奏/前奏/尾奏最大 RMS %.0f（必须低于副歌 %.0f）' % (inst_max, chorus_rms))
    intro_rms = per['I1'][0]
    intro_db = 20 * math.log10(intro_rms / chorus_rms)
    print('前奏 RMS %.0f，比副歌低 %.1f dB（要求 6–12 dB 余量）' % (intro_rms, -intro_db))
    print('时长 %.2f 秒（要求 170–200 秒 ≈ 3 分钟）' % sec)
    assert chorus_rms >= verse_rms * 1.2, '副歌没压过主歌'
    assert inst_max < chorus_rms, '间奏比副歌还响，抢戏了'
    assert 6 <= -intro_db <= 12, '前奏动态余量不在 6–12 dB'
    assert 170 <= sec <= 200, '时长不在 3 分钟档'
    print('自校验全过：3 分钟档 / 副歌压过主歌 / 间奏不抢戏')
    print('峰值 %d (%.0f%%)' % (max(abs(x) for x in s), max(abs(x) for x in s) / 327.67))

if __name__ == '__main__':
    main()
