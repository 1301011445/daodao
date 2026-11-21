# -*- coding: utf-8 -*-
"""多随机种子跑一遍，看这套生成器是不是「碰巧过」还是稳定过判据。"""
import importlib.util, os, io, json, sys
P = r'F:\Daodao\tools\音乐\旋律体检\和弦骨架旋律v2.py'
CHK1 = r'F:\Daodao\tools\音乐\旋律体检\旋律体检.py'
CHK2 = r'F:\Daodao\tools\音乐\旋律体检\旋律和声贴合.py'

def mod(path, name):
    sp = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m)
    return m

chk1 = mod(CHK1, 'c1'); chk2 = mod(CHK2, 'c2')
v2 = mod(P, 'v2')

rows = []
for seed in (3, 7, 11, 23, 42):
    notes, melody = v2.build(seed=seed, tries=200)
    melody = v2.global_fix(list(melody), 0)
    base_notes = [n for n in notes if n['ch'] == 0]
    for k, n in enumerate(base_notes):
        n['pitch'] = melody[k]
    out = os.path.join(r'F:\Daodao\_tmp_face', 'seed_%d.mid' % seed)
    v2.cl.write_mid(notes, v2.PPQ, out, v2.TEMPO)
    a = chk1.analyze(chk1.melody_notes(out))
    b = chk2.analyze(out)
    fails = [k for k in a if k[:2] in ('L1','L2','L3','L4','L5','L6') and a[k] == 'FAIL']
    fails += [k for k in b if k[:2] in ('L7','L8','L9','L10') and b[k] == 'FAIL']
    rows.append((seed, a['步进比'], a['音域半音'], a['三音细胞重复'], a['最高音次数'],
                 a['钩子公式命中'], a['大跳未接级进'], b['和弦音占比'], b['时值种类'],
                 b['最长同音连续'], b['最长同时值连跑'], fails))
for r in rows:
    print('seed %2d | 步进 %s 音域 %s 细胞 %s 最高音 %s 钩子 %s 裸跳 %s | 和弦 %s%% 时值 %s 同音 %s 连跑 %s | %s'
          % (r[0], r[1], r[2], r[3], r[4], r[5], r[6], round(r[7] * 100, 1), r[8], r[9], r[10],
             ('待改：' + ','.join(f[:2] for f in r[11])) if r[11] else '十项全过'))
ok = sum(1 for r in rows if not r[11])
print('稳定率 %d/%d' % (ok, len(rows)))
io.open(r'F:\Daodao\tools\音乐\旋律体检\和弦骨架v2_多种子.csv', 'w', encoding='utf-8-sig').write(
    '种子,步进比,音域,细胞,最高音,钩子,裸跳,和弦音占比,时值种类,最长同音,同时值连跑,未过项\n' +
    '\n'.join('%d,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s' % (r[0], r[1], r[2], r[3], r[4], r[5], r[6],
              r[7], r[8], r[9], r[10], '；'.join(x[:2] for x in r[11])) for r in rows))
