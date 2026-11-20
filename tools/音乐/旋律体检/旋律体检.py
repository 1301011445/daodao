# -*- coding: utf-8 -*-
"""第28类 旋律体检：量步进比 / 音域 / 细胞重复 / 最高音次数 / 钩子公式。
用法：python 旋律体检.py <mid1> [mid2 ...]
输出同目录 旋律体检.json 与 stdout 表格。
"""
import sys, os, json, io
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '前奏钩子'))
from importlib.util import spec_from_file_location, module_from_spec

_p = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '前奏钩子', '前奏钩子检查.py')
_spec = spec_from_file_location('hook', _p)
_hook = module_from_spec(_spec); _spec.loader.exec_module(_hook)

def melody_notes(mid):
    fmt, div, tracks = _hook.read_mid(mid)
    ev, tp = [], []
    for tr in tracks:
        e, t2 = _hook.parse_track(tr); ev += e; tp += t2
    tp.sort()
    ons = [e for e in ev if e[0] == 'on' and e[2] != 9]
    # 主旋律通道：取音域 ≤20 半音、音符 ≥30 的通道里编号最小的那个
    # （本项目 ch0 = 人声旋律，ch1 = 和声铺底音域 45 半音，按音符数挑会挑错）
    st = {}
    for e in ons:
        st.setdefault(e[2], [0, 128, 0])
        st[e[2]][0] += 1
        st[e[2]][1] = min(st[e[2]][1], e[3])
        st[e[2]][2] = max(st[e[2]][2], e[3])
    cand = [ch for ch, v in st.items() if v[0] >= 30 and (v[2] - v[1]) <= 20]
    mel = min(cand) if cand else (max(st, key=lambda c: st[c][0]) if st else None)
    seq = [(e[1], e[3]) for e in ons if e[2] == mel]
    seq.sort()
    return [n for (_, n) in seq]

def analyze(notes):
    ivs = [notes[i+1] - notes[i] for i in range(len(notes)-1)]
    steps = sum(1 for d in ivs if abs(d) <= 2)
    leaps = sum(1 for d in ivs if abs(d) >= 3)
    rng = max(notes) - min(notes) if notes else 0
    # 3 音细胞重复
    cells = {}
    for i in range(len(notes)-2):
        c = tuple(notes[i:i+3])
        cells[c] = cells.get(c, 0) + 1
    top_cell, top_n = (None, 0)
    if cells:
        top_cell, top_n = max(cells.items(), key=lambda kv: kv[1])
    peak = max(notes) if notes else None
    peak_n = notes.count(peak) if notes else 0
    # 钩子公式：连续上行 >=3 音到局部最高，随后下落 >=7
    hits = 0
    for i in range(len(notes)-3):
        up = 0
        j = i
        while j+1 < len(notes) and notes[j+1] > notes[j]:
            up += 1; j += 1
        if up >= 3 and j-i+1 >= 4:
            hi = notes[j]
            # 找之后的下落
            k = j+1
            if k < len(notes) and (hi - notes[k]) >= 7:
                hits += 1
    # 大跳后接级进
    bad_big = 0
    for idx, d in enumerate(ivs):
        if abs(d) >= 5:
            nxt = ivs[idx+1] if idx+1 < len(ivs) else None
            if nxt is None or abs(nxt) > 2:
                bad_big += 1
    ratio = steps / len(ivs) if ivs else 0
    return dict(
        音符数=len(notes),
        步进比=round(ratio, 3),
        跳进数=leaps,
        音域半音=rng,
        三音细胞重复=int(top_n),
        最高音次数=int(peak_n),
        钩子公式命中=hits,
        大跳未接级进=bad_big,
        L1_步进比判定='PASS' if 0.6 <= ratio <= 0.8 else 'FAIL',
        L2_音域判定='PASS' if 0 <= rng <= 12 else 'FAIL',
        L3_细胞重复判定='PASS' if top_n >= 3 else 'FAIL',
        L4_最高音判定='PASS' if 0 < peak_n <= 3 else 'FAIL',
        L5_钩子公式判定='PASS' if hits >= 1 else 'FAIL',
        L6_大跳接级进判定='PASS' if bad_big == 0 else 'FAIL',
    )

def main(files):
    out = {}
    for f in files:
        if not os.path.exists(f):
            out[os.path.basename(f)] = '文件不存在'; continue
        out[os.path.basename(f)] = analyze(melody_notes(f))
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), '旋律体检.json')
    io.open(p, 'w', encoding='utf-8').write(json.dumps(out, ensure_ascii=False, indent=2))
    for k, v in out.items():
        if isinstance(v, str):
            print(k, v); continue
        fails = [x for x in v if x.startswith('L') and v[x] == 'FAIL']
        print(k, '| 步进比 %s | 音域 %s | 细胞 %s | 最高音 %s次 | 钩子 %s | 大跳裸 %s | %s'
              % (v['步进比'], v['音域半音'], v['三音细胞重复'], v['最高音次数'], v['钩子公式命中'],
                 v['大跳未接级进'], ('待改：' + ','.join(f[:2] for f in fails)) if fails else '全过'))
    print('写入', p)

if __name__ == '__main__':
    if len(sys.argv) > 1:
        main(sys.argv[1:])
    else:
        main([r'F:\Daodao\tools\音乐\故乡歌\out\归途的月光.mid',
              r'F:\Daodao\tools\音乐\打工人歌\out\打工人歌.mid'])
