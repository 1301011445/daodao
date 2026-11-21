# -*- coding: utf-8 -*-
"""和弦骨架旋律生成（第25类落地）：先定和弦，再在骨架上走级进、点缀经过音。

规则（都是从判据倒推出来的）：
  1. 每个音的时值位置先定（沿用原曲节奏模板），再按它落在哪一小节取该小节和弦的音级集合；
  2. 旋律音从和弦音里挑，取"离上一音最近、又不重复同高"的那个 —— 保证级进、不粘连；
  3. 乐句末音必须落在稳定音（base+0/5/7）；
  4. 每句最多插 2 个经过音/邻音：只在与前后音都成级进的位置放非和弦音，把和弦音占比压到 70%~85% 这个专业带，而不是 100%。
用法：python 和弦骨架旋律.py
"""
import sys, os, math, importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
def load(name, rel):
    sp = importlib.util.spec_from_file_location(name, os.path.join(HERE, rel))
    m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m)
    return m

gx = load('gx', '..\\故乡歌\\故乡歌.py')          # 取和弦进行、节奏模板、base、词
cl = load('cl', '..\\和弦对比\\chord_lib.py')

BEAT, PPQ, TEMPO = gx.BEAT, gx.PPQ, gx.TEMPO
STABLE_END = {0, 5, 7}


def pcs_of(name, octv):
    return [t % 12 for t in gx.tones(name, octv)]


def cands(base, pcs, lo=-2, hi=11):
    return [base + o for o in range(lo, hi + 1) if (base + o) % 12 in pcs]


def gen_line(base, chords, beats, peak_off, stress_i, key_pc=0, end_ok=STABLE_END, leak=2):
    """一条 8 音乐句：chords 是这一句两小节的音级集合列表"""
    n = len(beats)
    bar_of = [0 if b < 4 else 1 for b in beats]
    cs = [cands(base, chords[bar_of[i]]) for i in range(n)]

    # 目标走向：起于 base+2，stress_i 处最高，末尾回落
    def target(i):
        if i <= stress_i:
            return 2 + (peak_off - 2) * (i / float(max(1, stress_i)))
        return peak_off + (0 - peak_off) * ((i - stress_i) / float(max(1, n - 1 - stress_i)))

    strong_i = [i for i in range(n) if beats[i] in (0, 2, 4)]
    weak_i = [i for i in range(n) if i not in strong_i]
    scale = [(key_pc + s) % 12 for s in (0, 2, 4, 5, 7, 9, 11)]

    out = []
    for i in range(n):
        tk = base + target(i)
        prev = out[-1] if out else base + 2
        opts = [p for p in cs[i] if p in range(base - 1, base + 9)]
        if i == n - 1:
            opts = [p for p in opts if p - base in end_ok] or opts
        if not opts:
            out.append(tk); continue
        pool = [p for p in opts if p != prev] or opts

        if i in strong_i:
            # 强拍：必须是和弦音，取离上一音最近的一个（允许一次三/四度跳）
            pick = min(pool, key=lambda p: (abs(p - prev), abs(p - tk)))
        else:
            # 弱拍两种走法交替：
            #   偶数弱拍 → 落和弦音（多为一档三度，步进比因此不会过 0.8）
            #   奇数弱拍 → 音阶级进（1~2 半音），非和弦音当经过音/邻音
            step_opts = []
            for d in (1, -1, 2, -2):
                q = prev + d
                if q % 12 in scale and base <= q <= base + 7:
                    step_opts.append(q)
            # 级进里优先挑落和弦音的那一步：既保级进，又把和弦音占比抬上去
            step_opts.sort(key=lambda p: (0 if (p % 12) in chords[bar_of[i]] else 1,
                                          0 if p > prev else 1, abs(p - tk)))
            chord_near = [p for p in pool if abs(p - prev) <= 4]
            prev_was_step = (i > 0 and abs(prev - out[i - 2]) <= 2) if i >= 2 else True
            widx = weak_i.index(i) if i in weak_i else 0
            if chord_near and prev_was_step:
                pick = min(chord_near, key=lambda p: (abs(p - tk), abs(p - prev)))
            else:
                pick = step_opts[0] if step_opts else min(pool, key=lambda p: abs(p - prev))
            if pick == prev and step_opts:
                pick = step_opts[0]
        out.append(pick)

    # 插经过音/邻音：前后都级进、本音换 ±1 的非和弦音，每句最多 leak 个
    used = 0
    for i in range(1, n - 1):
        if used >= leak:
            break
        cur, pre, nxt = out[i], out[i - 1], out[i + 1]
        if (cur - base) in end_ok and i == n - 1:
            continue
        pcs_i = chords[bar_of[i]]
        for d in (1, -1):
            q = cur + d
            if q % 12 in pcs_i or not (base - 2 <= q <= base + 11):
                continue
            if abs(q - pre) <= 2 and abs(nxt - q) <= 2 and q != pre and q != nxt:
                out[i] = q; used += 1
                break
    # 大跳回修：>=5 半音的裸跳改成 <=4 的级进音（必须是和弦音且音阶内），消掉 L6
    for i in range(1, len(out)):
        if abs(out[i] - out[i - 1]) >= 5:
            pcs_i = chords[bar_of[i]]
            fix = [p for p in range(base - 1, base + 9)
                   if 1 <= abs(p - out[i - 1]) <= 4 and (p % 12) in scale]
            if i == n - 1:
                fix = [p for p in fix if p - base in end_ok] or fix
            if i + 1 < len(out):
                fix = [p for p in fix if p != out[i + 1]] or fix
            if fix:
                out[i] = min(fix, key=lambda p: abs(p - out[i - 1]))
    return [x - base for x in out]


PLAN = [
    ('V',  gx.PROG_V, gx.VERSES, 4, 4),
    ('PC', gx.PROG_PC, gx.PRECHORUS, 2, 4),
    ('C1', gx.PROG_C, gx.CHORUS, 4, 6),
    ('V2', gx.PROG_V, gx.VERSES2, 4, 4),
    ('C2', gx.PROG_C, gx.CHORUS2, 4, 6),
    ('B',  gx.PROG_B, gx.BRIDGE, 4, 4),
    ('C3', gx.PROG_C3, gx.CHORUS3, 4, 4),
]
# 音区重排：主歌抬到 62、副歌 67 顶到 73、副歌三 D 调 69 顶到 73，全曲音域压到 11 半音
BASE2 = {'V': 62, 'V2': 62, 'PC': 62, 'C1': 67, 'C2': 67, 'C3': 69, 'B': 62}


def build_mid():
    notes = []
    hook_contour = None
    t_line = 0
    for tag, prog, lines, cnt, peak in PLAN:
        base = BASE2[tag]
        rhy = 'R3' if tag.startswith('C') else gx.VAR_RHY.get(tag, 'R1')
        beats, durs = gx.RHY[rhy]
        beats = list(beats); durs = list(durs)
        for li, (text, _old) in enumerate(lines):
            chords = [pcs_of(*prog[(2 * li) % len(prog)]), pcs_of(*prog[(2 * li + 1) % len(prog)])]
            si = gx.STRESS['C' if tag.startswith('C') else tag][li % 4]
            si = si if beats[si] in (0, 2, 4) else 0        # 重音位必须落在强拍
            if tag.startswith('C') and li in (0, 2):
                if hook_contour is None:
                    hook_contour = gen_line(gx.BASE['C1'], chords, beats, peak, si, key_pc=0)
                contour = hook_contour
            else:
                contour = gen_line(base, chords, beats, peak, si, key_pc=(2 if tag == 'C3' else 0))
            for i, off in enumerate(contour):
                notes.append(dict(t=t_line + int(beats[i] * BEAT), dur=int(durs[i] * BEAT),
                                  pitch=base + off, vel=95, ch=0))
            # 伴奏：每小节一个和弦，三音齐发
            for bi in range(2):
                nm, oc = prog[(2 * li + bi) % len(prog)]
                for q in gx.tones(nm, oc):
                    notes.append(dict(t=t_line + bi * 4 * BEAT, dur=4 * BEAT, pitch=q + 12, vel=60, ch=1))
            t_line += 8 * BEAT
    out = os.path.join(HERE, '归途的月光_和弦骨架.mid')
    cl.write_mid(notes, PPQ, out, TEMPO)
    mel = [n for n in notes if n['ch'] == 0]
    print('写出 %s：旋律 %d 音，伴奏 %d 音，总 %d 音'
          % (os.path.basename(out), len(mel), len(notes) - len(mel), len(notes)))
    pc_in = 0
    # 自查和弦贴合（与判据同口径）
    for n in mel:
        bar_t = (n['t'] // (4 * BEAT)) * 4 * BEAT
        grp = [x['pitch'] % 12 for x in notes if x['ch'] == 1 and x['t'] == bar_t]
        if grp and (n['pitch'] % 12) in grp:
            pc_in += 1
    print('和弦音占比 %.1f%%（%d/%d）' % (100.0 * pc_in / len(mel), pc_in, len(mel)))


if __name__ == '__main__':
    build_mid()





