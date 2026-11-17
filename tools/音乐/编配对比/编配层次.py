# -*- coding: utf-8 -*-
"""编配层次实验：同一段旋律，主歌做减法、副歌加层次，看副歌体量是否真的压过主歌。
学到的东西落在这里：
 1) 音区分工：低音 < 和弦 < 旋律，不重叠；
 2) 副歌变化靠"加层"和"下潜"，不是靠把每个音都写得更多；
 3) 主歌要留白，副歌才有对比；
 4) 验收：副歌段 RMS 必须压过主歌段（上一轮反例：比例 1:1.46 反过来）。
"""
import math, os, struct, wave, random

SR = 22050
BEAT = 480
PPQ = 480
TEMPO = 84
rnd = random.Random(7)

NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
def p(name):
    return 12 * (int(name[-1]) + 1) + NAMES.index(name[:-1])

VERSE = [('C', 3), ('A', 2), ('F', 3), ('G', 3)] * 2
CHORUS = [('F', 3), ('G', 3), ('E', 2), ('A', 2), ('D', 3), ('G', 3), ('C', 3), ('C', 3)]

MOTIF_V = ['C4', 'D4', 'E4', 'G4']
MOTIF_C = ['G4', 'A4', 'B4', 'D5']

def chord_tones(name, octv):
    r = p(name + str(octv))
    if name in ('A', 'E', 'D'):
        return [r, r + 3, r + 7]
    return [r, r + 4, r + 7]

def build():
    """每小节 4 拍；主歌 8 小节，副歌 8 小节"""
    notes = []          # {'t','dur','pitch','ch','amp'}
    t = 0
    for bar in range(16):
        chorus = bar >= 8
        m = MOTIF_C if chorus else MOTIF_V
        # 旋律：每小节 2 个音
        for i in range(2):
            notes.append(dict(t=t + i * 2 * BEAT, dur=2 * BEAT, pitch=p(m[i]), ch=0,
                              amp=0.24 if not chorus else 0.38))
        prog = CHORUS[bar - 8] if chorus else VERSE[bar % 8]
        tones = chord_tones(prog[0], prog[1])          # 和弦放中低区（C3 一带）
        for q in tones:
            notes.append(dict(t=t, dur=4 * BEAT, pitch=q, ch=2, amp=0.06 if not chorus else 0.13))
        # 低音：主歌一小节一个根音，副歌一小节两个（下潜 + 加密）
        root = p(prog[0] + str(prog[1]))
        notes.append(dict(t=t, dur=4 * BEAT, pitch=root, ch=1, amp=0.11 if not chorus else 0.24))
        if chorus:
            notes.append(dict(t=t + 2 * BEAT, dur=2 * BEAT, pitch=root, ch=1, amp=0.14))
        # 鼓：只有副歌进来（主歌留白）
        if chorus:
            for b, kind in [(0, 'k'), (1, 's'), (2, 'k'), (3, 's')]:
                notes.append(dict(t=t + b * BEAT, dur=int(0.25 * BEAT), pitch=0, ch=3,
                                  amp={'k': 0.62, 's': 0.34}[kind], kind=kind))
            for hb in (0.5, 1.5, 2.5, 3.5):
                notes.append(dict(t=t + int(hb * BEAT), dur=int(0.12 * BEAT), pitch=0,
                                  ch=3, amp=0.14, kind='h'))
            # 副歌加第三层和弦（高八度的第二声部，只做根音+五度，别糊）
            if bar % 2 == 0:
                for q in (tones[0] + 12, tones[2] + 12):
                    notes.append(dict(t=t, dur=4 * BEAT, pitch=q, ch=2, amp=0.05))
        t += 4 * BEAT
    return notes

def render(notes, path):
    sec_tick = (60.0 / TEMPO) / PPQ
    total = max(n['t'] + n['dur'] for n in notes)
    length = int(total * sec_tick * SR) + SR // 5
    buf = [0.0] * length
    for n in notes:
        st = int(n['t'] * sec_tick * SR)
        ln = max(1, int(n['dur'] * sec_tick * SR))
        if n['ch'] == 3:                     # 打击乐：噪/低频脉冲
            kind = n['kind']
            for i in range(min(ln, length - st)):
                tt = i / float(SR)
                if kind == 'k':
                    f = 120 * math.exp(-tt / 0.03) + 40
                    v = math.sin(2 * math.pi * f * tt) * math.exp(-tt / 0.09)
                elif kind == 's':
                    v = (rnd.uniform(-1, 1) * 0.8 + math.sin(2 * math.pi * 200 * tt) * 0.2) * math.exp(-tt / 0.06)
                else:
                    v = rnd.uniform(-1, 1) * math.exp(-tt / 0.02)
                buf[st + i] += n['amp'] * v
            continue
        f = 440.0 * (2.0 ** ((n['pitch'] - 69) / 12.0))
        harm = 0.28 if n['ch'] == 0 else 0.18
        for i in range(min(ln, length - st)):
            tt = i / float(SR)
            env = min(1.0, i / 200.0) * min(1.0, (ln - i) / 400.0)
            buf[st + i] += n['amp'] * env * (math.sin(2 * math.pi * f * tt) +
                                            harm * math.sin(4 * math.pi * f * tt))
    peak = max(1e-9, max(abs(x) for x in buf))
    g = 0.92 / peak if peak > 1 else 1.0
    w = wave.open(path, 'wb'); w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes(b''.join(struct.pack('<h', int(max(-1, min(1, x * g)) * 32767)) for x in buf))
    w.close()
    return length, g

def rms_of(path):
    w = wave.open(path, 'rb'); n = w.getnframes()
    s = struct.unpack('<%dh' % n, w.readframes(n)); w.close()
    return s, n

def main():
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out')
    os.makedirs(out, exist_ok=True)
    ns = build()
    wav = os.path.join(out, '编配对比.wav')
    length, g = render(ns, wav)
    s, n = rms_of(wav)
    half = n // 2
    def rms(a, b):
        seg = s[a:b]
        return math.sqrt(sum(x * x for x in seg) / max(1, len(seg)))
    rv = rms(0, half)
    rc = rms(half, n)
    print('WAV %.2f 秒，增益 %.2f' % (n / float(SR), g))
    print('音符 %d（旋律 %d / 低音 %d / 和弦 %d / 鼓 %d）'
          % (len(ns), sum(1 for x in ns if x['ch'] == 0), sum(1 for x in ns if x['ch'] == 1),
             sum(1 for x in ns if x['ch'] == 2), sum(1 for x in ns if x['ch'] == 3)))
    print('主歌段 RMS %.0f | 副歌段 RMS %.0f | 比值 %.2f' % (rv, rc, rc / rv))
    assert rc > rv * 1.2, '副歌没压过主歌，编配失败'
    # 音区分工自检
    mel = [x['pitch'] for x in ns if x['ch'] == 0]
    bas = [x['pitch'] for x in ns if x['ch'] == 1]
    chr = [x['pitch'] for x in ns if x['ch'] == 2]
    ab = sum(bas) / float(len(bas)); ac = sum(chr) / float(len(chr)); am = sum(mel) / float(len(mel))
    print('音区：低音 %d~%d(均%.1f) / 和弦 %d~%d(均%.1f) / 旋律 %d~%d(均%.1f)'
          % (min(bas), max(bas), ab, min(chr), max(chr), ac, min(mel), max(mel), am))
    assert ab < ac < am, '三层中心音区没有递增'
    print('自校验通过：副歌压过主歌（%.2f 倍）、三层中心音区递增 %.1f < %.1f < %.1f' % (rc / rv, ab, ac, am))

if __name__ == '__main__':
    main()
