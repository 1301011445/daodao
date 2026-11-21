# -*- coding: utf-8 -*-
"""第25类 旋律生成器改造 v2：先和弦骨架，后装饰音（2026-11-21）

v1 的问题（实测）：8 音一句 + 只用纯三和弦，逼着"既级进又踩和弦音"，结果
和弦音 53.4%、步进比 0.86 越界、音域 15。根因不是算法不够花，是**和弦音的可选面太窄**。

v2 依据（三条硬规则，都来自公开教材与曲例实测）：
  1. 强拍（0/2/4 拍）必须是和弦音，且优先 根/三/五；非和弦音只准出现在弱拍或弱位
     —— produc.ing《Chord Tones & Passing Tones》、chordlookup《Writing Melodies and Phrases》
  2. 弱拍上的非和弦音只有三种合法身份：经过音（夹在两个和弦音之间、级进）、
     邻音（离开再回到同一个和弦音）、先现音（提前一拍落到下一个和弦音）
     —— 抖音百科「和弦外音」条目：经过音发生在弱拍/弱位、时值不长于两侧和弦音
  3. 和弦要扩到 add9 / 七和弦：流行歌里 add9、7th 本来就是和弦音的合法成员（Hooktheory 的
     Chord Complexity 就是量这个）。三和弦只有 3 个音级，add9 一加，2 度也成了和弦音，
     "级进"和"踩和弦音"就不再打架——这正是 v1 的死结
  4. 和弦音占比落点：Hooktheory 曲例实测 60%~74%（The Beatles《Help》70%、NotaGen 74%、
     John Cale 60%、Mandelbrot Set 66%），本项目判据取 ≥60%，目标带 65%~74%
  5. 乐句末音落稳定音（base+0/5/7），全句音域 ≤12 半音、最高音出现 1~3 次、三音细胞重复 ≥3
     （钩子要能被认出来），大跳（≥5）后必须接级进 —— 与 旋律体检.py 的 L1~L6 同口径

做法：每个位置先按规则生成候选音（强拍=和弦音、弱拍=和弦音或合法外音），
再用判据打分做一轮受限随机搜索（不违反规则的前提下挑参数），最后写成 MIDI。

用法：python 和弦骨架旋律v2.py [试跑次数]
"""
import sys, os, random, importlib.util, io, json

HERE = os.path.dirname(os.path.abspath(__file__))


def load(name, rel):
    sp = importlib.util.spec_from_file_location(name, os.path.join(HERE, rel))
    m = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m)
    return m


gx = load('gx', os.path.join('..', '故乡歌', '故乡歌.py'))
cl = load('cl', os.path.join('..', '和弦对比', 'chord_lib.py'))
hook = load('hook', os.path.join('..', '前奏钩子', '前奏钩子检查.py'))

BEAT, PPQ, TEMPO = gx.BEAT, gx.PPQ, gx.TEMPO
STABLE = {0, 5, 7}

# 音区重排：三段只差 5 半音，单句幅度压到 5，全曲音域才落进 12
BASE2 = {'V': 62, 'V2': 62, 'PC': 62, 'C1': 65, 'C2': 65, 'C3': 67, 'B': 62}   # 62/65/67 都是调内音，跨段只差 5 半音
PLAN = [
    ('V',  gx.PROG_V,  gx.VERSES,     0),
    ('PC', gx.PROG_PC, gx.PRECHORUS,  0),
    ('C1', gx.PROG_C,  gx.CHORUS,     0),
    ('V2', gx.PROG_V,  gx.VERSES2,    0),
    ('C2', gx.PROG_C,  gx.CHORUS2,    0),
    ('B',  gx.PROG_B,  gx.BRIDGE,     0),
    ('C3', gx.PROG_C3, gx.CHORUS3,    2),
]


def use_song(path):
    """换一首歌：段结构、和弦、词、节奏都从它自己的生成器里取，音区按调内音重排"""
    global GX, BASE2, PLAN, BEAT, PPQ, TEMPO
    GX = load('gxsong', path)
    BEAT, PPQ, TEMPO = GX.BEAT, GX.PPQ, GX.TEMPO
    bv = GX.BASE['V']
    # 主歌与副歌只差 3~5 半音，副歌三句不再往上抬（音域判据 ≤12 不允许三段各抬 2 度）
    BASE2 = {'V': bv, 'V2': bv, 'PC': bv, 'C1': bv + 3, 'C2': bv + 3,
             'C3': bv + 5, 'B': bv}
    if not hasattr(GX, 'STRESS'):
        GX.STRESS = {'V': [4, 4, 2, 2], 'V2': [4, 4, 4, 2], 'C': [4, 4, 4, 2],
                     'B': [4, 4, 4, 4], 'PC': [4, 4, 2, 4]}
    P3 = getattr(GX, 'PROG_C3', GX.PROG_C)
    SH = 2 if hasattr(GX, 'PROG_C3') else 0
    PLAN = [('V', GX.PROG_V, GX.VERSES, 0)]
    if hasattr(GX, 'PRECHORUS'):
        PLAN.append(('PC', getattr(GX, 'PROG_PC', GX.PROG_B), GX.PRECHORUS, 0))
    PLAN += [('C1', GX.PROG_C, GX.CHORUS, 0), ('V2', GX.PROG_V, GX.VERSES2, 0),
             ('C2', GX.PROG_C, getattr(GX, 'CHORUS2', GX.CHORUS), 0),
             ('B', GX.PROG_B, GX.BRIDGE, 0),
             ('C3', P3, getattr(GX, 'CHORUS3', GX.CHORUS), SH)]
    return GX


GX = gx


def scale_pcs(key_pc):
    return [(key_pc + s) % 12 for s in (0, 2, 4, 5, 7, 9, 11)]


def triad_pcs(name, octv):
    return [t % 12 for t in GX.tones(name, octv)]


def ext_pcs(name, octv, key_pc):
    """和弦音集合 = 三和弦 + add9 + 七音（都要落在调内，不然是借来的音，不算和弦音）"""
    t = triad_pcs(name, octv)
    root = t[0]
    sc = scale_pcs(key_pc)
    out = list(t)
    for d in (2, 10, 9):          # add9 / b7 / add6
        p = (root + d) % 12
        if p in sc and p not in out:
            out.append(p)
            break                     # 一个和弦只扩一个，避免铺太厚
    return out


def chords_for(prog, li, key_pc):
    """一句两小节，各给 (强拍和弦音集合, 弱位可用集合)"""
    bars = []
    for bi in (0, 1):
        nm, oc = prog[(2 * li + bi) % len(prog)]
        bars.append((triad_pcs(nm, oc), ext_pcs(nm, oc, key_pc)))
    return bars


def allowed(base, bar, lo=0, hi=7):
    return [(base + o, ('strong' if (base + o) % 12 in bar[0] else 'weak'))
            for o in range(lo, hi + 1)
            if (base + o) % 12 in bar[1]]


def gen_line(base, bars, beats, key_pc, peak=5, stress=4, motif=None, rng=None, tries=260, allow_hook=False):
    """一条 8 音：强拍落和弦音，弱位放经过/邻/先现音；带判据打分的受限搜索"""
    rng = rng or random
    n = len(beats)
    bar_of = [0 if beats[i] < 4 else 1 for i in range(n)]
    strong = [i for i in range(n) if int(beats[i]) in (0, 2, 4) and float(beats[i]) == int(beats[i])]
    sc = scale_pcs(base % 12) if False else None

    def target(i):
        if i <= stress:
            return 1.0 + (peak - 1.0) * (i / float(max(1, stress)))
        return peak + (0.0 - peak) * ((i - stress) / float(max(1, n - 1 - stress)))

    best, best_score = None, -1e9
    for _ in range(tries):
        # 1) 强拍：和弦音，逐步挪向目标音高，不重复同音
        out = [None] * n
        prev = base + 1
        for i in strong:
            opts = [p for p, k in allowed(base, bars[bar_of[i]]) if k == 'strong' and p != prev]
            if not opts:
                opts = [p for p, k in allowed(base, bars[bar_of[i]]) if k == 'strong'] or [prev]
            w = []
            for p in opts:
                d = abs(p - prev)
                sc_ = -abs(p - (base + target(i)))
                sc_ += 0.6 if d <= 4 else -3.0          # 别出大跳
                sc_ += 0.4 if d >= 1 else -1.0          # 别同音
                w.append((p, sc_ + rng.uniform(-0.55, 0.55)))
            prev = max(w, key=lambda kv: kv[1])[0]
            out[i] = prev

        # 2) 弱位：优先经过音（夹在两个和弦音之间级进），其次邻音，最后和弦音
        for i in range(n):
            if i in strong:
                continue
            nxt = next((j for j in strong if j > i), None)
            prv = next((j for j in reversed(strong) if j < i), None)
            a = out[prv] if prv is not None else base + 1
            b = out[nxt] if nxt is not None else a
            cand = []
            lo, hi = min(a, b), max(a, b)
            if hi - lo >= 2:                        # 经过音：夹在中间、级进
                for p in range(lo + 1, hi):
                    if p % 12 in scale_pcs(key_pc) and abs(p - a) <= 2 and abs(p - b) <= 2:
                        cand.append((p, 1.0))
            if abs(b - a) <= 2:                     # 邻音：走开一度再回来
                for d in (1, -1, 2, -2):
                    p = a + d
                    if p % 12 in scale_pcs(key_pc) and p != a and p != b and base <= p <= base + 7:
                        cand.append((p, 0.6))
            for p, k in allowed(base, bars[bar_of[i]]):
                if p not in (a,) and base <= p <= base + 7:
                    cand.append((p, 0.3))
            if not cand:
                cand = [(a, 0.2)]
            w = []
            for p, kk in cand:
                score = kk
                score += 0.5 if (p % 12) in bars[bar_of[i]][1] else 0.0   # 尽量落和弦音
                score -= 1.2 if p == (out[i - 1] if i else a) else 0.0      # 防同音
                score -= 1.5 if (i and i + 1 < n and abs(p - out[i - 1]) >= 5) else 0.0
                score -= 0.8 if abs(p - (base + target(i))) > 3 else 0.0
                w.append((p, score + rng.uniform(-0.35, 0.35)))
            out[i] = max(w, key=lambda kv: kv[1])[0]

        # 3) 句末落稳定音
        e = n - 1
        if (out[e] - base) not in STABLE:
            opts = [p for p, k in allowed(base, bars[bar_of[e]]) if (p - base) in STABLE]
            if opts:
                out[e] = min(opts, key=lambda p: (abs(p - out[e]), abs(p - out[e - 1])))
        # 4) 大跳后必接级进
        for i in range(1, n):
            if abs(out[i] - out[i - 1]) >= 5 and i + 1 < n and abs(out[i + 1] - out[i]) > 2:
                pool = [p for p, k in allowed(base, bars[bar_of[i]]) if 1 <= abs(p - out[i - 1]) <= 4]
                if pool:
                    out[i] = min(pool, key=lambda p: abs(p - (base + target(i))))

        m = measure(out, base, bars, bar_of, beats)
        # 5) 钩子补丁：四音连续上行到大跳点、再落七度到稳定音（L5 要的就是这个形状）
        patched = try_hook(out, base, bars, bar_of, beats, key_pc) if allow_hook else None
        if patched:
            mp = measure(patched, base, bars, bar_of, beats)
            if motif:
                mp['motif'] = 1.0 if patched[:3] == motif[:3] else 0.0
            if score_line(mp) > score_line(m):
                out, m = patched, mp
        if motif:
            m['motif'] = 1.0 if out[:3] == motif[:3] else 0.0
        score = score_line(m)
        if score > best_score:
            best_score, best = score, list(out)
    return [p - base for p in best], best_score


def try_hook(out, base, bars, bar_of, beats, key_pc):
    """在一条乐句里找一个合法位置，塞「四音上行 → 七度下落」的钩子形状。

    这里必须松一档：四个上行音**不必都是和弦音**——弱位上它们是经过音/邻音，
    和弦外音本来就是干这个的（只要级进、只要强拍还落在和弦音上）。
    L5 量的是轮廓形状，L7 量的是全局和弦音占比，两者不冲突。"""
    n = len(out)
    sc = scale_pcs(key_pc)

    def strong(i):
        return int(beats[i]) in (0, 2, 4) and float(beats[i]) == int(beats[i])

    def ok_hard(i, p):      # 强拍：必须是三和弦音
        return (p % 12) in bars[bar_of[i]][0]

    def ok_soft(i, p):      # 弱位：调内音即可（和弦外音当经过音）
        return (p % 12) in sc

    def up_runs(pk):
        res = [[pk]]
        for _ in range(3):
            nxt = []
            for run in res:
                for d in (1, 2):
                    v = run[0] - d
                    if v >= 0:
                        nxt.append([v] + run)
            res = nxt
        return res

    best = None
    for j in range(0, n - 4):
        for pk in (7, 6, 5):
            for run in up_runs(pk):
                seq = [base + v for v in run]
                if any(p > base + 7 for p in seq):
                    continue
                bad = False
                for k, p in enumerate(seq):
                    i = j + k
                    if strong(i) and not ok_hard(i, p):
                        bad = True; break
                    if (not strong(i)) and not ok_soft(i, p):
                        bad = True; break
                if bad:
                    continue
                land = pk - 7
                if land < 0 or land > 7:
                    continue
                if not ok_soft(j + 4, base + land):
                    continue
                if j + 4 == n - 1 and land not in STABLE:
                    continue
                if j > 0 and abs(seq[0] - out[j - 1]) > 4:
                    continue
                if j + 5 < n and abs(out[j + 5] - (base + land)) > 2:
                    continue
                score = sum(1 for k, p in enumerate(seq) if (p % 12) in bars[bar_of[j + k]][1])
                score += 2 if ok_hard(j + 4, base + land) else 0
                cand = out[:j] + seq + [base + land] + out[j + 5:]
                if best is None or score > best[0]:
                    best = (score, cand)
    return best[1] if best else None


def measure(out, base, bars, bar_of, beats):
    ivs = [out[i + 1] - out[i] for i in range(len(out) - 1)]
    ratio = sum(1 for d in ivs if abs(d) <= 2) / float(len(ivs)) if ivs else 0
    chord = 0
    for i, p in enumerate(out):
        # 强拍只认三和弦；弱位认扩展集合（这就是 add9/七音该算的地方）
        target_set = bars[bar_of[i]][0] if (int(beats[i]) in (0, 2, 4) and float(beats[i]) == int(beats[i])) else bars[bar_of[i]][1]
        if p % 12 in target_set:
            chord += 1
    chord_ratio = chord / float(len(out))
    peak_n = out.count(max(out))
    mx_same = 1
    for i in range(1, len(out)):
        mx_same = mx_same + 1 if out[i] == out[i - 1] else 1
    # 钩子公式：连续上行 ≥3 音到局部最高，随后下落 ≥7（旋律体检 L5 同口径）
    hook = 0
    for i in range(len(out) - 1):
        j = i
        while j + 1 < len(out) and out[j + 1] > out[j]:
            j += 1
        if j - i >= 3 and j + 1 < len(out) and out[j] - out[j + 1] >= 7:
            hook += 1
    # 裸大跳：≥5 半音之后没有级进接住（L6 同口径）
    naked = 0
    for i, d in enumerate(ivs):
        if abs(d) >= 5 and (i + 1 >= len(ivs) or abs(ivs[i + 1]) > 2):
            naked += 1
    return dict(chord=chord_ratio, step=ratio, rng=max(out) - min(out),
                peak_n=peak_n, same=mx_same, hook=hook, naked=naked)


def score_line(m):
    s = 0.0
    s += 6.0 if 0.62 <= m['chord'] <= 0.80 else -10.0 * abs(m['chord'] - 0.70)
    s += 5.0 if 0.60 <= m['step'] <= 0.80 else -6.0 * abs(m['step'] - 0.70)
    s += 3.0 if m['rng'] <= 7 else -1.0 * (m['rng'] - 7)
    s += 2.0 if 1 <= m['peak_n'] <= 2 else -3.0
    s += 1.0 if m['same'] <= 2 else -3.0
    s += 4.0 * m['hook'] - 4.0 * m['naked']
    return s


def global_fix(melody, key_pc):
    """整体收口：最高音不超过 3 次（L4）、大跳后一律级进（L6）。
    只做最小挪动（1~2 半音、调内），不动和弦骨架。"""
    sc = scale_pcs(key_pc)
    mx = max(melody)
    idxs = [i for i, p in enumerate(melody) if p == mx]
    keep = idxs[:3]
    for i in idxs[3:]:
        for d in (-1, -2, 1, 2):
            q = mx + d
            if q % 12 in sc and q < mx:
                if (i > 0 and abs(q - melody[i - 1]) <= 4) or i == 0:
                    melody[i] = q
                    break
    for i in range(len(melody) - 1):
        if abs(melody[i + 1] - melody[i]) >= 5:
            j = i + 2
            if j < len(melody) and abs(melody[j] - melody[i + 1]) > 2:
                # 把大跳后面那个音挪到紧贴大跳落点的级进位置
                target = melody[i + 1]
                opts = [target + d for d in (-2, -1, 1, 2)
                        if (target + d) % 12 in sc and target + d != target]
                if opts and (j + 1 >= len(melody) or abs(melody[j + 1] - opts[0]) <= 5):
                    melody[j] = min(opts, key=lambda q: abs(q - melody[j]))
    # 同音连跑：任何地方出现第三个连续同音，就把这一个挪一度（L9 判据：最长同音 ≤2）
    for _ in range(6):
        fixed = False
        for k in range(2, len(melody)):
            if melody[k] == melody[k - 1] == melody[k - 2]:
                p = melody[k]
                for d in (1, -1, 2, -2):
                    q = p + d
                    if q % 12 not in sc or q == p:
                        continue
                    if k + 1 < len(melody) and abs(melody[k + 1] - q) > 5:
                        continue
                    if q == melody[k - 1]:
                        continue
                    melody[k] = q
                    fixed = True
                    break
        if not fixed:
            break
    return melody


def build(seed=11, tries=260):
    rng = random.Random(seed)
    notes = []
    melody = []
    hook_motif = None
    hook_done = False
    t_line = 0
    last_pitch = None
    for tag, prog, lines, key_pc in PLAN:
        base = BASE2[tag]
        rhy = 'R3' if tag.startswith('C') else GX.VAR_RHY.get(tag, 'R1')
        beats, durs = GX.RHY[rhy]
        beats = list(beats); durs = list(durs)
        for li, (text, _old) in enumerate(lines):
            bars = chords_for(prog, li, key_pc)
            si = GX.STRESS['C' if tag.startswith('C') else tag][li % 4]
            si = si if beats[si] in (0, 2, 4) else 0
            motif = None
            if tag.startswith('C') and li in (0, 1, 2):
                motif = hook_motif       # 副歌三句共用开头三音，钩子才认得出来
            peak = 4                       # 顶音压到 base+4，把唯一的最高点留给钩子那句
            offs, sc = gen_line(base, bars, beats, key_pc, peak=peak, stress=si,
                                motif=motif, rng=rng, tries=tries,
                                allow_hook=not hook_done)
            mb = measure([base + o for o in offs], base, bars,
                         [0 if beats[i] < 4 else 1 for i in range(len(beats))], beats)
            if mb['hook'] >= 1 and mb['naked'] == 0:
                hook_done = True     # 一首歌只放一个钩子形状，放多了最高音会被反复顶到
            # 乐句之间的大跳：让下一句第二音接住级进（L6 要求大跳后必须级进）
            if last_pitch is not None and abs(offs[0] + base - last_pitch) >= 5:
                p1 = base + offs[1]
                if abs(p1 - (base + offs[0])) > 2:
                    sc_pcs = scale_pcs(key_pc)
                    p0 = base + offs[0]
                    opts = [p0 + d for d in (-2, -1, 1, 2)
                            if (p0 + d) % 12 in sc_pcs and p0 + d != p0]
                    if opts:
                        offs[1] = min(opts, key=lambda q: abs(q - p1)) - base
            if tag == 'C1' and li == 0:
                hook_motif = list(offs[:3])
            for i, off in enumerate(offs):
                pv = base + off
                melody.append(pv)
                notes.append(dict(t=t_line + int(beats[i] * BEAT), dur=int(durs[i] * BEAT),
                                  pitch=pv, vel=95, ch=0))
                last_pitch = pv
            for bi in range(2):
                nm, oc = prog[(2 * li + bi) % len(prog)]
                pcs = ext_pcs(nm, oc, key_pc)      # 伴奏也铺 add9/七音，和弦音集合才对得上
                tri = triad_pcs(nm, oc)
                for pc in tri:
                    notes.append(dict(t=t_line + bi * 4 * BEAT, dur=4 * BEAT,
                                      pitch=pc + 12 + (12 if pc < 60 else 0), vel=58, ch=1))
                extra = [pc for pc in pcs if pc not in tri]
                for pc in extra[:1]:
                    notes.append(dict(t=t_line + bi * 4 * BEAT, dur=4 * BEAT,
                                      pitch=pc + 24, vel=52, ch=1))
            t_line += 8 * BEAT
    return notes, melody


def report(melody, beats_all):
    ivs = [melody[i + 1] - melody[i] for i in range(len(melody) - 1)]
    step = sum(1 for d in ivs if abs(d) <= 2) / float(len(ivs))
    big = 0
    for i, d in enumerate(ivs):
        if abs(d) >= 5 and (i + 1 >= len(ivs) or abs(ivs[i + 1]) > 2):
            big += 1
    rng_ = max(melody) - min(melody)
    cells = {}
    for i in range(len(melody) - 2):
        c = tuple(melody[i:i + 3])
        cells[c] = cells.get(c, 0) + 1
    top_cell = max(cells.values()) if cells else 0
    peak = max(melody); peak_n = melody.count(peak)
    hookhit = 0
    for i in range(len(melody) - 3):
        j = i
        while j + 1 < len(melody) and melody[j + 1] > melody[j]:
            j += 1
        if j - i >= 3 and j + 1 < len(melody) and melody[j] - melody[j + 1] >= 7:
            hookhit += 1
    return dict(步进比=round(step, 3), 音域=rng_, 三音细胞重复=top_cell,
                最高音次数=peak_n, 钩子=hookhit, 大跳裸=big)


if __name__ == '__main__':
    ntry = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 260
    seed = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else 11
    song = sys.argv[3] if len(sys.argv) > 3 else None     # 可传另一首歌的生成器路径
    name = sys.argv[4] if len(sys.argv) > 4 else '归途的月光_和弦骨架v2'
    if song:
        use_song(os.path.abspath(song))
    notes, melody = build(seed=seed, tries=ntry)
    melody = global_fix(list(melody), 0)
    base_notes = [n for n in notes if n['ch'] == 0]
    for k, n in enumerate(base_notes):          # 收口后的音高回写到谱面（顺序一一对应）
        n['pitch'] = melody[k]
    out = os.path.join(HERE, name + '.mid')
    cl.write_mid(notes, PPQ, out, TEMPO)
    # 和弦音占比自查（与 旋律和声贴合.py 同口径：按伴奏同 tick 的音级集合算）
    mel = [n for n in notes if n['ch'] == 0]
    hit = 0; tot = 0
    for n in mel:
        bar_t = (n['t'] // (4 * BEAT)) * 4 * BEAT
        grp = set(x['pitch'] % 12 for x in notes if x['ch'] == 1 and x['t'] == bar_t)
        if grp:
            tot += 1
            if (n['pitch'] % 12) in grp:
                hit += 1
    print('写出 %s：旋律 %d 音' % (os.path.basename(out), len(mel)))
    print('和弦音占比 %.1f%%（%d/%d）' % (100.0 * hit / tot, hit, tot))
    r = report(melody, None)
    print('步进比 %s | 音域 %d | 细胞重复 %d | 最高音 %d 次 | 钩子 %d | 大跳裸 %d'
          % (r['步进比'], r['音域'], r['三音细胞重复'], r['最高音次数'], r['钩子'], r['大跳裸']))
    io.open(os.path.join(HERE, '和弦骨架v2_自查.json'), 'w', encoding='utf-8').write(
        json.dumps(dict(和弦音占比=round(100.0 * hit / tot, 1), **r), ensure_ascii=False, indent=2))
