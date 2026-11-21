# -*- coding: utf-8 -*-
"""旋律和弦吸附：把落在和弦外音的旋律音，挪到最近的和弦音（最小位移优先）。

为什么：实测三首成品和弦音占比只有 35%~39%，而专业实测流行歌是 70%~74%。
六成音不踩和弦，听感就是"一直在跑调"，这是"难听"的主因之一。

做法：只改动旋律通道的音高字节，其它事件（和弦、鼓、tempo）一个字节不动；
原文件不改，另存 *_和弦修正.mid。
用法：python 旋律修音.py <mid> [输出后缀]
"""
import sys, os, struct
from importlib.util import spec_from_file_location, module_from_spec

_p = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '前奏钩子', '前奏钩子检查.py')
_spec = spec_from_file_location('hook', _p)
_hook = module_from_spec(_spec); _spec.loader.exec_module(_hook)


def chord_timeline(mid, mel):
    fmt, div, tracks = _hook.read_mid(mid)
    groups = {}
    for tr in tracks:
        ev, _t = _hook.parse_track(tr)
        for x in ev:
            if x[0] == 'on' and x[2] != 9 and x[2] != mel:
                groups.setdefault(x[1], set()).add(x[3] % 12)
    return sorted((t, s) for t, s in groups.items() if len(s) >= 2)


def snap_map(mid, mel):
    """返回 {tick: 新音高}，只包含需要动的音。

    两条约束，防止"修好和弦、改坏听感"：
      1) 只挪强拍（拍头/半拍）或长音（>=1.5 拍）上的非和弦音；
         弱拍短音保留下来当经过音——真实流行歌和弦音占比 70%~74%，不是 100%。
      2) 挪完不能和相邻音同高——否则粘连成"卡带"，同音连续会变长。
    """
    _f, div, tracks = _hook.read_mid(mid)
    chords = chord_timeline(mid, mel)
    mapping = {}
    if not chords:
        return mapping
    notes = []
    for tr in tracks:
        ev, _t = _hook.parse_track(tr)
        for x in ev:
            if x[0] == 'on' and x[2] == mel:
                notes.append((x[1], x[3]))
    notes.sort()

    # 先算每个音的"当前和弦"和它本身是不是和弦音
    ci = 0
    pcs_at = []
    base_chord = []
    for t, n in notes:
        while ci + 1 < len(chords) and chords[ci + 1][0] <= t:
            ci += 1
        pcs = chords[ci][1] if chords[ci][0] <= t else None
        pcs_at.append(pcs)
        base_chord.append(bool(pcs) and (n % 12 in pcs))

    final = [n for _, n in notes]
    # 音域锁：不许把旋律撑开，否则体检脚本认不出旋律通道（音域 >20 半音即失配）
    lo = min(final); hi = max(final)
    moved = kept = passing = 0
    for i, (t, n) in enumerate(notes):
        pcs = pcs_at[i]
        if not pcs:
            continue
        if base_chord[i]:
            kept += 1; continue
        nxt = notes[i + 1][0] if i + 1 < len(notes) else t + 2 * div
        ioi = (nxt - t) / float(div)
        # 经过音/邻音：本音短，前后都是和弦音，且前后都是级进（<=2 半音）
        is_passing = (ioi <= 1.5 and i > 0 and i + 1 < len(notes)
                      and base_chord[i - 1] and base_chord[i + 1]
                      and abs(n - notes[i - 1][1]) <= 2
                      and abs(notes[i + 1][1] - n) <= 2)
        if is_passing:
            passing += 1; continue
        pick = None
        for d in (1, -1, 2, -2, 3, -3, 4, -4, 5, -5, 6, -6):
            cand = n + d
            if lo <= cand <= hi and cand % 12 in pcs:
                if i > 0 and cand == final[i - 1]:
                    continue
                if i + 1 < len(notes) and cand == notes[i + 1][1] and not base_chord[i + 1]:
                    continue
                pick = cand; break
        if pick:
            final[i] = pick; moved += 1

    # 第二遍：清掉"3 个以上连着同音高"，把中间那个换成别的和弦音
    fixed_run = 0
    i = 0
    while i < len(final):
        j = i
        while j + 1 < len(final) and final[j + 1] == final[i]:
            j += 1
        if j - i + 1 >= 3:
            for k in range(i + 1, j + 1):
                pcs = pcs_at[k]
                if not pcs:
                    continue
                for d in (1, -1, 2, -2, 3, -3, 4, -4, 5, -5, 6, -6):
                    cand = final[k] + d
                    if lo <= cand <= hi and cand % 12 in pcs and cand != final[k - 1]:
                        if k + 1 < len(final) and cand == final[k + 1]:
                            continue
                        final[k] = cand; fixed_run += 1; break
        i = j + 1

    for i, (t, n) in enumerate(notes):
        if final[i] != n:
            mapping[t] = final[i]
    print('原有和弦音 %d，挪 %d，保留经过音 %d，解粘连 %d' % (kept, moved, passing, fixed_run))
    return mapping


def patch(src, dst, mel, mapping):
    data = bytearray(open(src, 'rb').read())
    ntrk = struct.unpack('>H', data[10:12])[0]
    pos = 8 + struct.unpack('>I', data[4:8])[0]
    for _ in range(ntrk):
        assert data[pos:pos + 4] == b'MTrk'
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
                    if ch == mel and t in mapping:
                        data[i] = mapping[t]
                    i += 2
                elif kind in (0xA0, 0xB0, 0xE0):
                    i += 2
                else:
                    i += 1
        pos = end
    open(dst, 'wb').write(data)


def main(mid, tag='和弦修正'):
    mel = None
    _f, _d, tracks = _hook.read_mid(mid)
    best = -1
    for tr in tracks:
        ev, _t = _hook.parse_track(tr)
        for x in ev:
            if x[0] == 'on' and x[2] != 9:
                if x[2] != best and False:
                    pass
    # 旋律通道挑法与体检脚本一致：音符>=30 且音域<=20 的通道里编号最小
    chans = {}
    for tr in tracks:
        ev, _t = _hook.parse_track(tr)
        for x in ev:
            if x[0] == 'on' and x[2] != 9:
                chans.setdefault(x[2], []).append(x[3])
    cand = [c for c, v in chans.items()
            if len(v) >= 30 and (max(v) - min(v)) <= 20]
    mel = min(cand) if cand else max(chans, key=lambda c: len(chans[c]))
    print('旋律通道 =', mel)

    mapping = snap_map(mid, mel)
    dst = os.path.join(os.path.dirname(os.path.abspath(mid)),
                       os.path.splitext(os.path.basename(mid))[0] + '_' + tag + '.mid')
    patch(mid, dst, mel, mapping)
    # 立刻自检：能否重新解析、音符数是否与原来一致
    _f, _d, tracks2 = _hook.read_mid(dst)
    p1 = sum(1 for tr in tracks for x in _hook.parse_track(tr)[0] if x[0] == 'on' and x[2] == mel)
    p2 = sum(1 for tr in tracks2 for x in _hook.parse_track(tr)[0] if x[0] == 'on' and x[2] == mel)
    print('写出 %s  旋律音符 %d -> %d %s' % (os.path.basename(dst), p1, p2, 'OK' if p1 == p2 else '不一致！'))


if __name__ == '__main__':
    if len(sys.argv) > 1:
        main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else '和弦修正')
    else:
        main(r'F:\Daodao\tools\音乐\故乡歌\out\归途的月光.mid')


