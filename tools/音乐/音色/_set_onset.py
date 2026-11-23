# -*- coding: utf-8 -*-
"""给四个唱法模板补「起颤」比例（0 = 整颗抖到底，0.55 = 前六成直音后四成颤）。"""
import json, io
P = r'F:\Daodao\tools\音乐\音色\音色库.json'
d = json.load(io.open(P, encoding='utf-8'))
ONSET = {'单依纯': 0.25, '李健': 0.35, '那英': 0.50, '王菲': 0.60}
for n, v in ONSET.items():
    if n in d['profiles']:
        d['profiles'][n].setdefault('唱法', {})['起颤'] = v
json.dump(d, io.open(P, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
for n in ONSET:
    print(n, '起颤=', d['profiles'][n]['唱法']['起颤'])
