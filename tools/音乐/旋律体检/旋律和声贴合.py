# -*- coding: utf-8 -*-
"""第29类 旋律与和声的贴合 + 节奏多样性（2026-11-21）

为什么做这个：用户说"作的曲真难听"。难听不是形容词能解决的，得能算。
本脚本量四件事：
  L7  和弦音占比        —— 旋律音踩在当前和弦上的比例（Hooktheory 实测流行歌 70%~74%）
  L8  时值（起音间隔）种类 —— 全是同一个时值=念经（上音《谈音乐创作》点名的毛病）
  L9  最长同音连续      —— 同音反复超过 2 次听着像卡带
  L10 最长同时值连跑    —— 连续 8 个以上同长度音符=节奏呆板

用法：python 旋律和声贴合.py <mid1> [mid2 ...]
输出同目录 旋律和声贴合.json；有任何 FAIL 时退出码 1。
"""
import sys, os, json, io
from importlib.util import spec_from_file_location, module_from_spec

_p = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '前奏钩子', '前奏钩子检查.py')
_spec = spec_from_file_location('hook', _p)
_hook = module_from_spec(_spec); _spec.loader.exec_module(_hook)


def load(mid):
    fmt, div, tracks = _hook.read_mid(mid)
    ev = []
    for tr in tracks:
        e, _t = _hook.parse_track(tr)
        ev += e
    ons = [x for x in ev if x[0] == 'on' and x[2] != 9]   # 9=打击乐，不参与和声
    chans = {}
    for _k, t, ch, n in ons:
        chans.setdefault(ch, []).append((t, n))
    for c in chans:
        chans[c].sort()
    return div, chans


def pick_melody(chans):
    """旋律通道：音符 >=30 且音域 <=20 半音的通道里编号最小的（本项目 ch0=人声旋律）"""
    cand = [c for c, v in chans.items()
            if len(v) >= 30 and (max(n for _, n in v) - min(n for _, n in v)) <= 20]
    if cand:
        return min(cand)
    return max(chans, key=lambda c: len(chans[c]))


def analyze(mid):
    div, chans = load(mid)
    mel = pick_melody(chans)
    notes = chans[mel]

    # 和弦时间线：把其余通道里"同一 tick 起音"的音聚成一个和弦
    groups = {}
    for c in chans:
        if c == mel:
            continue
        for t, n in chans[c]:
            groups.setdefault(t, set()).add(n % 12)
    chords = sorted((t, s) for t, s in groups.items() if len(s) >= 2)

    # L7 和弦音占比：每个旋律音，取"不晚于它的最近一次和弦起音"作为当前和弦
    hit = 0; tot = 0
    if chords:
        ci = 0
        for t, n in notes:
            while ci + 1 < len(chords) and chords[ci + 1][0] <= t:
                ci += 1
            if chords[ci][0] > t:
                continue          # 第一个和弦出现之前的音不计
            tot += 1
            if n % 12 in chords[ci][1]:
                hit += 1
    ratio = (hit / float(tot)) if tot else 0.0

    # L8 时值（起音间隔，单位拍）
    ios = [round((notes[i + 1][0] - notes[i][0]) / float(div), 2) for i in range(len(notes) - 1)]
    kinds = sorted(set(ios))

    # L9 最长同音连续
    mx_same = 1; cur = 1
    for i in range(1, len(notes)):
        if notes[i][1] == notes[i - 1][1]:
            cur += 1
            mx_same = max(mx_same, cur)
        else:
            cur = 1

    # L10 最长同时值连跑
    mx_run = 1; cur = 1
    for i in range(1, len(ios)):
        if ios[i] == ios[i - 1]:
            cur += 1
            mx_run = max(mx_run, cur)
        else:
            cur = 1

    return dict(
        旋律通道=mel, 音符数=len(notes), 和弦窗口数=len(chords),
        和弦音命中=hit, 占比基准=tot, 和弦音占比=round(ratio, 3),
        时值种类=len(kinds), 时值清单=kinds[:10],
        最长同音连续=mx_same, 最长同时值连跑=mx_run,
        L7_和弦音占比='PASS' if ratio >= 0.60 else 'FAIL',
        L8_时值种类='PASS' if len(kinds) >= 3 else 'FAIL',
        L9_同音连续='PASS' if mx_same <= 2 else 'FAIL',
        L10_同时值连跑='PASS' if mx_run <= 8 else 'FAIL',
    )


def main(files):
    out = {}
    fail_any = False
    for f in files:
        if not os.path.exists(f):
            out[os.path.basename(f)] = '文件不存在'
            print(os.path.basename(f), '文件不存在')
            continue
        r = analyze(f)
        out[os.path.basename(f)] = r
        fails = [k for k in r if k[:2] in ('L7', 'L8', 'L9', 'L10') and r[k] == 'FAIL']
        if fails:
            fail_any = True
        print('%-18s 和弦音 %5.1f%%(%d/%d) | 时值 %d 种 %s | 最长同音 %d | 最长同值连跑 %d | %s'
              % (os.path.basename(f), r['和弦音占比'] * 100, r['和弦音命中'], r['占比基准'],
                 r['时值种类'], r['时值清单'], r['最长同音连续'], r['最长同时值连跑'],
                 ('待改：' + ','.join(f[:2] for f in fails)) if fails else '全过'))
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), '旋律和声贴合.json')
    io.open(p, 'w', encoding='utf-8').write(json.dumps(out, ensure_ascii=False, indent=2))
    print('写入', p)
    return 1 if fail_any else 0


if __name__ == '__main__':
    if len(sys.argv) > 1:
        sys.exit(main(sys.argv[1:]))
    sys.exit(main([
        r'F:\Daodao\tools\音乐\故乡歌\out\归途的月光.mid',
        r'F:\Daodao\tools\音乐\打工人歌\out\把好日子扛在肩上.mid',
        r'F:\Daodao\tools\音乐\少年歌\out\少年模样.mid',
    ]))
