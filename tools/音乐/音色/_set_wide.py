# -*- coding: utf-8 -*-
"""只放开「气声」这一项的护城河（±40%），其余项仍 ±15%。
单依纯的气包声、李健的通透都靠 breath/centroid，不放宽度就听不出差别。
"""
import json, io
P = r'F:\Daodao\tools\音乐\音色\音色库.json'
d = json.load(io.open(P, encoding='utf-8'))
WIDE = {'单依纯': {'breath': 0.40}, '李健': {'breath': 0.40, 'tilt': 0.25}}
for n, w in WIDE.items():
    if n in d['profiles']:
        d['profiles'][n]['放宽'] = w
json.dump(d, io.open(P, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
for n, w in WIDE.items():
    print(n, '放宽=', d['profiles'][n]['放宽'])
