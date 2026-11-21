# -*- coding: utf-8 -*-
"""守旋律、改和声：旋律音高一个字不动，按每段的旋律音重挑伴奏和弦。

为什么这么做：
  直接挪旋律音可以把"和弦音占比"从 39% 拉到 90%，但步进比从 0.796 掉到 0.345、
  裸大跳从 2 处涨到 76 处——旋律骨架被掰坏了，听着更怪。
  真实编曲的顺序是相反的：旋律定了，和弦去配合旋律（re-harmonize）。

判据：每段窗口内，从 24 个大小三和弦里选"覆盖旋律音最多"的那个，
      原和弦命中最多时保留原样，避免无谓改动。
用法：python 守旋律改和声.py <mid> [后缀]
"""
import sys, os, struct
from importlib.util import spec_from_file_location, module_from_spec

_HERE = os.path.dirname(os.path.abspath(__file__))
_CL = os.path.join(_HERE, '..', '和弦对比', 'chord_lib.py')
_s = spec_from_file_location('chordlib', _CL)
cl = module_from_spec(_s); _s.loader.exec_module(cl)


def read_all_notes(path):
    """严格解析，返回 (ppq, tempo, notes[(on,off,ch,note,vel)])"""
    data = open(path, 'rb').read()
    ppq = struct.unpack('>H', data[12:14])[0]
    ntrk = struct.unpack('>H', data[10:12])[0]
    pos = 8 + struct.unpack('>I', data[4:8])[0]
    notes = []; tempo = 120; opening = {}
    for _ in range(ntrk):
        tlen = struct.unpack('>I', data[pos + 4:pos + 8])[0]
        i = pos + 8; end = i + tlen; t = 0; run = 0
        while i < end:
            d0 = data[i]; i += 1; d = d0 & 0x7f
            while d0 & 0x80:
                d0 = data[i]; i += 1; d = (d << 7) | (d0 & 0x7f)
            t += d
            st = data[i]
            if st == 0xFF:
                i += 1; mt = data[i]; i += 1; ln = data[i]; i += 1
                if mt == 0x2F:
                    break
                if mt == 0x51 and ln == 3:
                    tempo = 60000000.0 / int.from_bytes(data[i:i + 3], 'big')
                i += ln; run = 0
            elif st in (0xF0, 0xF7):
                i += 1; ln = data[i]; i += 1 + ln; run = 0
            else:
                if st & 0x80:
                    run = st; i += 1
                else:
                    st = run
                ch = st & 0x0F; kind = st & 0xF0
                if kind in (0x90, 0x80):
                    n = data[i]; v = data[i + 1]
                    if kind == 0x90 and v:
                        opening[(ch, n)] = (t, v)
                    elif (ch, n) in opening:
                        on, vel = opening.pop((ch, n))
                        notes.append((on, t, ch, n, vel))
                    i += 2
                elif kind in (0xA0, 0xB0, 0xE0):
                    i += 2
                else:
                    i += 1
        pos = end
    return ppq, tempo, notes


def pick_melody(notes):
    chans = {}
    for on, off, ch, n, v in notes:
        if ch != 9:
            chans.setdefault(ch, []).append(n)
    cand = [c for c, v in chans.items() if len(v) >= 30 and (max(v) - min(v)) <= 20]
    return min(cand) if cand else max(chans, key=lambda c: len(chans[c]))


def windows(acc):
    """伴奏里 同 tick 起音且音数>=2 处，作为和弦窗口起点"""
    grp = {}
    for on, off, ch, n, v in acc:
        grp.setdefault(on, []).append(n)
    starts = sorted(t for t, ns in grp.items() if len(ns) >= 2)
    out = []
    for k, st in enumerate(starts):
        en = starts[k + 1] if k + 1 < len(starts) else st + 10 ** 9
        out.append((st, en, grp[st]))
    return out


def triads():
    """三和弦 24 个 + 七和弦（大小调属七），给旋律更多落点"""
    out = []
    for pc in range(12):
        out.append((pc, (pc, (pc + 4) % 12, (pc + 7) % 12)))
        out.append((pc, (pc, (pc + 3) % 12, (pc + 7) % 12)))
        out.append((pc, (pc, (pc + 4) % 12, (pc + 7) % 12, (pc + 10) % 12)))
        out.append((pc, (pc, (pc + 3) % 12, (pc + 7) % 12, (pc + 10) % 12)))
    return out


def chord_of_tick(acc_notes, tick):
    """伴奏在 tick 起的和弦音级集合（取不晚于 tick 的最近一次和弦起音）"""
    grp = {}
    for on, pitch in acc_notes:
        grp.setdefault(on, []).append(pitch % 12)
    starts = sorted(t for t, pcs in grp.items() if len(pcs) >= 2)
    chosen = None
    for st in starts:
        if st <= tick:
            chosen = grp[st]
        else:
            break
    return set(chosen) if chosen and len(chosen) >= 2 else None


def micro_snap(new_notes, mel, ppq):
    """旋律里仍落在和弦外的音，只挪 ±1~2 半音（级进级别）。

    三条护栏，防止"和弦贴合了、轮廓散了"：
      1) 原来是级进的关系（|差|<=2）挪完必须仍级进——大跳裸就是这么爆出来的；
      2) 不能和相邻音同高（避免粘连成长串同音）；
      3) 不越出原旋律音域。
    """
    acc = [(n['t'], n['pitch']) for n in new_notes if n['ch'] != mel and n['ch'] != 9]
    mels = sorted([n for n in new_notes if n['ch'] == mel], key=lambda n: n['t'])
    orig = [n['pitch'] for n in mels]
    lo = min(orig); hi = max(orig)
    moved = 0
    for k, n in enumerate(mels):
        pcs = chord_of_tick(acc, n['t'])
        p = n['pitch']
        if not pcs or (p % 12) in pcs:
            continue
        prev_f = mels[k - 1]['pitch'] if k > 0 else None
        prev_o = orig[k - 1] if k > 0 else None
        next_o = orig[k + 1] if k + 1 < len(orig) else None
        pick = None
        for d in (1, -1, 2, -2):
            c = p + d
            if not (lo <= c <= hi and (c % 12) in pcs):
                continue
            if prev_f is not None and c == prev_f:
                continue
            if prev_o is not None and abs(orig[k] - prev_o) <= 2 and abs(c - prev_f) > 2:
                continue
            if next_o is not None and any(m['pitch'] == c for m in mels[k + 1:k + 2]):
                continue
            pick = c; break
        if pick is not None:
            n['pitch'] = pick; moved += 1
    print('旋律级进微调 %d 音（上限 ±2 半音，保级进关系）' % moved)
    return moved


def nearest_with_pcs(note, pcs, lo, hi):
    for d in (0, 1, -1, 2, -2, 3, -3, 4, -4, 5, -5, 6, -6, 7, -7, 8, -8, 9, -9, 10, -10, 11, -11, 12, -12):
        c = note + d
        if lo <= c <= hi and c % 12 in pcs:
            return c
    return note


def reharmonize(path, tag='改和声'):
    ppq, tempo, notes = read_all_notes(path)
    mel = pick_melody(notes)
    acc = [x for x in notes if x[2] != 9 and x[2] != mel]
    meln = [(x[0], x[3]) for x in notes if x[2] == mel]
    meln.sort()
    wins = windows(acc)
    cands = triads()
    print('旋律通道 %d（%d 音），伴奏 %d 音，和弦窗口 %d 段' % (mel, len(meln), len(acc), len(wins)))

    new_notes = []
    kept = 0; changed = 0
    for st, en, ns in wins:
        seg = [n for t, n in meln if st <= t < en]
        orig_pcs = tuple(sorted(set(n % 12 for n in ns)))
        best = None; best_score = -1
        for root, pcs in cands:
            score = sum(1 for n in seg if n % 12 in pcs) * 1.0
            if set(pcs) == set(orig_pcs):
                score += 0.6          # 原和弦优先，能不动就不动
            if score > best_score:
                best_score = score; best = (root, pcs)
        if set(best[1]) == set(orig_pcs) and len(seg) < 2:
            best = (None, orig_pcs)
        root, pcs = best
        if root is None:
            kept += 1
        else:
            changed += 1 if set(pcs) != set(orig_pcs) else 0
        # 改这一窗里伴奏的音高：最低音当根音，其余找最近的弦音
        lo = min(n for _, _, _, n, _ in acc) - 2
        hi = max(n for _, _, _, n, _ in acc) + 2
        in_win = [x for x in acc if x[0] == st]
        order = sorted(in_win, key=lambda x: x[3])
        used = set()
        for idx, item in enumerate(order):
            on, off, ch, n, v = item
            want = n if idx == 0 and root is not None else n
            pcs_use = {root} if (idx == 0 and root is not None) else set(pcs)
            want = nearest_with_pcs(n, pcs_use, lo, hi)
            tries = 0
            while want in used and tries < 40:
                want = nearest_with_pcs(want + 1, pcs_use, lo, hi)
                tries += 1
            used.add(want)
            new_notes.append({'t': on, 'pitch': want, 'dur': off - on, 'vel': v, 'ch': ch})

    for on, off, ch, n, v in notes:
        if ch == mel:
            new_notes.append({'t': on, 'pitch': n, 'dur': off - on, 'vel': v, 'ch': ch})

    micro_snap(new_notes, mel, ppq)

    dst = os.path.join(os.path.dirname(os.path.abspath(path)),
                       os.path.splitext(os.path.basename(path))[0] + '_' + tag + '.mid')
    cl.write_mid(new_notes, ppq, dst, tempo)
    print('换和弦 %d 段，保留 %d 段，写出 %s（%d 音，原 %d 音）'
          % (changed, kept, os.path.basename(dst), len(new_notes), len(notes)))


if __name__ == '__main__':
    if len(sys.argv) > 1:
        reharmonize(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else '改和声')
