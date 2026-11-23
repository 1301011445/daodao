# -*- coding: utf-8 -*-
"""给唱法模板补机读字段「尾招」：合成侧只认这几个值，人话留在「尾音」里。"""
import json, io
P = r'F:\Daodao\tools\音乐\音色\音色库.json'
d = json.load(io.open(P, encoding='utf-8'))
TAIL = {'单依纯': '弱收', '李健': '气不散', '那英': '稳后颤', '王菲': '弱收'}
for n, v in TAIL.items():
    if n in d['profiles']:
        d['profiles'][n].setdefault('唱法', {})['尾招'] = v
json.dump(d, io.open(P, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
for n in TAIL:
    print(n, '尾招=', d['profiles'][n]['唱法']['尾招'])
