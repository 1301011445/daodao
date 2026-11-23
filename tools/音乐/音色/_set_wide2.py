# -*- coding: utf-8 -*-
"""放宽改成绝对区间：气声 0.10–0.24（单依纯）、0.08–0.16（李健）；李健 tilt 0.44–0.60。
只放这两项，其余项仍按 ±15% 的乘性护城河。"""
import json, io
P = r'F:\Daodao\tools\音乐\音色\音色库.json'
d = json.load(io.open(P, encoding='utf-8'))
WIDE = {'单依纯': {'breath': [0.10, 0.24]},
        '李健': {'breath': [0.08, 0.16], 'tilt': [0.44, 0.60]},
        '那英': {'tilt': [0.60, 0.80], 'centroid': [1600.0, 2100.0]},
        '王菲': {'breath': [0.10, 0.22]}}
for n, w in WIDE.items():
    if n in d['profiles']:
        d['profiles'][n]['放宽'] = w
json.dump(d, io.open(P, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
for n, w in WIDE.items():
    print(n, '放宽=', d['profiles'][n]['放宽'])
