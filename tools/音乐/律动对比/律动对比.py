# -*- coding: utf-8 -*-
"""鼓的律动对比：同一段副歌，四种鼓走位，量出差别再判断。
A backbeat（底鼓 1、3 / 军鼓 2、4）
B classic pop（底鼓 1、and-of-2、3 —— 前推力来自那半拍）
C four-on-the-floor（每拍一记底鼓）
D half-time（军鼓只在第 3 拍）
"""
import importlib.util, math, os, struct, wave

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location('arr', os.path.join(HERE, '..', '编配对比', '编配层次.py'))
arr = importlib.util.module_from_spec(spec); spec.loader.exec_module(arr)
arr.TEMPO = 112

BEAT, PPQ = 480, 480
NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
def p(n): return 12 * (int(n[-1]) + 1) + NAMES.index(n[:-1])
def tones(name, octv):
    r = p(name + str(octv))
    return [r, r + 3, r + 7] if name in ('A', 'E', 'D') else [r, r + 4, r + 7]

PROG_C = [('F', 3), ('G', 3), ('E', 3), ('A', 3), ('D', 3), ('G', 3), ('C', 4), ('C', 4)]
HOOK = [0, 2, 4, 2, 7, 9, 4, 2]          # 副歌第一句的旋律轮廓（相对 G4）
RHY = [0, 1, 2, 3, 4, 5, 5.5, 6]        # 8 字一句的起拍
DUR = [1, 1, 1, 1, 1, 1, 0.5, 2]

PATTERNS = {
    'A_backbeat':  dict(kick=[0, 2], snare=[1, 3], hat=[0, 0.5, 1, 1.5, 2, 2.5, 3, 3.5]),
    'B_classicpop': dict(kick=[0, 1.5, 2], snare=[1, 3], hat=[0, 0.5, 1, 1.5, 2, 2.5, 3, 3.5]),
    'C_fourfloor': dict(kick=[0, 1, 2, 3], snare=[1, 3], hat=[0.5, 1.5, 2.5, 3.5]),
    'D_halftime':  dict(kick=[0, 1.5], snare=[2], hat=[0, 0.5, 1, 1.5, 2, 2.5, 3, 3.5]),
}

def build(kind):
    pat = PATTERNS[kind]
    notes = []
    t = 0
    for bar in range(8):
        nm, oc = PROG_C[bar]
        tr = tones(nm, oc)
        notes.append(dict(t=t, dur=4 * BEAT, pitch=tr[0], ch=1, amp=0.24))          # 贝斯
        notes.append(dict(t=t + 2 * BEAT, dur=2 * BEAT, pitch=tr[0], ch=1, amp=0.15))
        for q in tr:
            notes.append(dict(t=t, dur=4 * BEAT, pitch=q + 12, ch=2, amp=0.12))      # 和弦
        for b, d, o in zip(RHY, DUR, HOOK):                                          # 旋律
            notes.append(dict(t=t + int(b * BEAT), dur=int(d * BEAT), pitch=67 + o, ch=0, amp=0.38))
        kick = pat['kick']
        for b in kick:
            notes.append(dict(t=t + int(b * BEAT), dur=int(0.25 * BEAT), pitch=0, ch=3,
                              amp=0.60, kind='k'))
        for b in pat['snare']:
            notes.append(dict(t=t + int(b * BEAT), dur=int(0.25 * BEAT), pitch=0, ch=3,
                              amp=0.34, kind='s'))
        for b in pat['hat']:
            notes.append(dict(t=t + int(b * BEAT), dur=int(0.12 * BEAT), pitch=0, ch=3,
                              amp=0.14, kind='h'))
        t += 4 * BEAT
    return notes

def stats(path):
    w = wave.open(path, 'rb'); n = w.getnframes(); s = struct.unpack('<%dh' % n, w.readframes(n))
    sr = w.getframerate(); w.close()
    rms = math.sqrt(sum(x * x for x in s) / len(s))
    zc = sum(1 for i in range(1, len(s)) if (s[i - 1] >= 0) != (s[i] >= 0))
    zcr = zc / float(len(s))                      # 越高=越偏高频（底鼓多则偏低）
    beat_len = int(sr * 60.0 / 112)
    on = off = 0.0
    bars = len(s) // (4 * beat_len)
    for bar in range(bars):
        base = bar * 4 * beat_len
        for b in range(4):
            seg = s[base + b * beat_len: base + (b + 1) * beat_len]
            on += sum(x * x for x in seg)
            offseg = s[base + b * beat_len + beat_len // 2: base + (b + 1) * beat_len]
            off += sum(x * x for x in offseg)
    # 每半拍的能量剖面（4/4 一小节 8 格），这条才看得出律动
    slot = beat_len // 2
    env = [0.0] * 8
    for bar in range(bars):
        base = bar * 4 * beat_len
        for k in range(8):
            seg = s[base + k * slot: base + (k + 1) * slot]
            env[k] += sum(x * x for x in seg)
    env = [math.sqrt(e / max(1, bars * slot)) for e in env]
    mx = max(env) or 1.0
    env = [e / mx for e in env]
    # 近似低通（4 点滑动平均）后的 RMS，粗看低频体量
    lp = [sum(s[max(0, i - 3):i + 1]) / max(1, min(4, i + 1)) for i in range(len(s))[::4]]
    lp_rms = math.sqrt(sum(x * x for x in lp) / len(lp))
    return dict(sec=len(s) / float(sr), rms=rms, zcr=zcr,
                off_ratio=off / max(1e-9, on), peak=max(abs(x) for x in s),
                env=env, lp=lp_rms)

def main():
    out = os.path.join(HERE, 'out'); os.makedirs(out, exist_ok=True)
    print('走位 | 时长 | RMS | 零交叉率 | 后半拍能量占比 | 峰值 | 底鼓/军鼓位置')
    rows = {}
    for k in PATTERNS:
        ns = build(k)
        wav = os.path.join(out, k + '.wav')
        arr.render(ns, wav)
        st = stats(wav); rows[k] = st
        e = ' '.join('%.2f' % v for v in st['env'])
        print('%s | %.1f 秒 | RMS %5.0f | 低通RMS %5.0f | 峰值 %d | 底鼓%s 军鼓%s\n    8 格能量: %s'
              % (k, st['sec'], st['rms'], st['lp'], st['peak'],
                 PATTERNS[k]['kick'], PATTERNS[k]['snare'], e))
    base = rows['A_backbeat']
    for k, st in rows.items():
        print('%s：RMS %+.0f%%，零交叉 %+.1f%%，后半拍 %+.0f%%（相对 A）'
              % (k, (st['rms'] / base['rms'] - 1) * 100, (st['zcr'] / base['zcr'] - 1) * 100,
                 (st['off_ratio'] / base['off_ratio'] - 1) * 100))

if __name__ == '__main__':
    main()
