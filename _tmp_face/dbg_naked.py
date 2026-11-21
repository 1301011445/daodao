# -*- coding: utf-8 -*-
import importlib.util, os, json
p = r'F:\Daodao\tools\音乐\旋律体检\和弦骨架旋律v2.py'
sp = importlib.util.spec_from_file_location('v2', p)
v2 = importlib.util.module_from_spec(sp); sp.loader.exec_module(v2)
notes, melody = v2.build(tries=200)
melody = v2.global_fix(list(melody), 0)
ivs = [melody[i + 1] - melody[i] for i in range(len(melody) - 1)]
bad = [(i, ivs[i], ivs[i + 1] if i + 1 < len(ivs) else None) for i in range(len(ivs))
       if abs(ivs[i]) >= 5 and (i + 1 >= len(ivs) or abs(ivs[i + 1]) > 2)]
print('长度', len(melody), '裸大跳', bad)
for i, d, nx in bad:
    print('  位置', i, '乐句', i // 8, '音高', melody[max(0, i - 2):i + 4])
print('音域', min(melody), max(melody))
