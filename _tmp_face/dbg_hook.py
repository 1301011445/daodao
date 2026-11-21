# -*- coding: utf-8 -*-
import importlib.util, os, sys
p = r'F:\Daodao\tools\音乐\旋律体检\和弦骨架旋律v2.py'
sp = importlib.util.spec_from_file_location('v2', p)
v2 = importlib.util.module_from_spec(sp); sp.loader.exec_module(v2)
gx, PLAN, BASE2 = v2.gx, v2.PLAN, v2.BASE2

for tag, prog, lines, key_pc in PLAN:
    base = BASE2[tag]
    rhy = 'R3' if tag.startswith('C') else gx.VAR_RHY.get(tag, 'R1')
    beats = list(gx.RHY[rhy][0])
    bars = v2.chords_for(prog, 0, key_pc)
    print(tag, 'base', base, 'beats', beats)
    print('  bar0 triad/ext', bars[0][0], bars[0][1], ' bar1', bars[1][0], bars[1][1])
    # 可行的 (offset -> 是否和弦音) 表
    for o in range(8):
        pv = base + o
        s = 'S' if (pv % 12) in bars[0][0] else ('w' if (pv % 12) in bars[0][1] else '.')
        t = 'S' if (pv % 12) in bars[1][0] else ('w' if (pv % 12) in bars[1][1] else '.')
        print('   off %d pitch %d pc %d | bar0 %s bar1 %s' % (o, pv, pv % 12, s, t))
    # 手搓一条钩子看 ok()
    cand = [0, 2, 4, 7, 0, 2, 0, 0]
    okc = []
    for i, o in enumerate(cand):
        bar = 0 if beats[i] < 4 else 1
        strong = int(beats[i]) in (0, 2, 4) and float(beats[i]) == int(beats[i])
        member = (base + o) % 12 in (bars[bar][0] if strong else bars[bar][1])
        okc.append((i, o, strong, member))
    print('  样例', okc)
