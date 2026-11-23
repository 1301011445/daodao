# -*- coding: utf-8 -*-
"""把 mix=0.45 也写进 feats（blend 优先读 feats['mix']），否则模板按默认 0.35 混、气声被压到 0.09。"""
import json, io
P = r'F:\Daodao\tools\音乐\音色\音色库.json'
d = json.load(io.open(P, encoding='utf-8'))
for n in ['单依纯', '李健', '那英', '王菲']:
    if n in d['profiles']:
        d['profiles'][n]['feats']['mix'] = d['profiles'][n].get('mix', 0.45)
json.dump(d, io.open(P, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
for n in ['单依纯', '李健', '那英', '王菲']:
    f = d['profiles'][n]['feats']
    print(n, 'feats.mix=', f['mix'], 'breath=', f['breath'], 'tilt=', f['tilt'])
