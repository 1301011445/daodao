# -*- coding: utf-8 -*-
"""按学到的规律回头审自己的歌：音区落差、音符密度、强拍落点、句尾强调"""
import json, os, sys

P = r'F:\Daodao\src\桌面分身\_bundle\music\song_01_寄一封.json'
o = json.load(open(P, encoding='utf-8'))
ppq = o['ppq']
bar = 4 * ppq            # 一小节 = 4 拍
phrase = 2 * bar         # 一句 = 2 小节 = 8 拍

groups = {}
for n in o['notes']:
    gi = n['t'] // phrase
    groups.setdefault(gi, []).append(n)

SEC = {0: '主歌一', 1: '副歌', 2: '主歌二', 3: '副歌再现'}
print('句子 | 段落 | 音符数 | 首音起拍 | 强拍占比 | 句内最高 | 末音相对句尾拍')
print('--- | --- | --- | --- | --- | --- | ---')
rows = []
for gi in sorted(groups):
    ns = sorted(groups[gi], key=lambda n: n['t'])
    beats = [(n['t'] % phrase) / ppq for n in ns]
    strong = sum(1 for b in beats if abs(b % 2) < 1e-6)
    hi = max(n['pitch'] for n in ns)
    end = (ns[-1]['t'] % phrase) / ppq + ns[-1]['dur'] / ppq
    rows.append((gi, SEC.get(gi // 4, '?'), len(ns), beats[0], strong / float(len(ns)), hi, end))
    print('%d | %s | %d | %.1f | %.0f%% | %d | %.1f' % (gi, rows[-1][1], len(ns), beats[0], strong / float(len(ns)) * 100, hi, end))

verse = [r for r in rows if r[1].startswith('主歌')]
chor = [r for r in rows if r[1].startswith('副歌')]
vhi = max(r[5] for r in verse)
chi = max(r[5] for r in chor)
print('\n== 四项判定 ==')
print('1) 副歌音区 vs 主歌最高音：%d 音 → %d 音，差 %d 半音（范例多在 +7 到 +12，+5 偏弱）' % (vhi, chi, chi - vhi))
print('2) 全曲音域：%d~%d，共 %d 半音（"octave and a third" 上限 16，%s）'
      % (min(n['pitch'] for n in o['notes']), max(n['pitch'] for n in o['notes']),
         max(n['pitch'] for n in o['notes']) - min(n['pitch'] for n in o['notes']),
         '贴上限' if max(n['pitch'] for n in o['notes']) - min(n['pitch'] for n in o['notes']) >= 14 else '有余地'))
dens_v = sum(r[2] for r in verse) / float(len(verse))
dens_c = sum(r[2] for r in chor) / float(len(chor))
print('3) 每句音符数：主歌 %.1f，副歌 %.1f（副歌该更少、更长，现在 %s）'
      % (dens_v, dens_c, '对得上' if dens_c <= dens_v else '不对'))
end_c = sum(1 for r in chor if r[6] >= 7.0) / float(len(chor))
print('4) 副歌句尾落在最后一拍（弱拍）的比例：%.0f%%（范例是句尾指向强拍，越唱越顶，不是泄气收尾）' % (end_c * 100))
