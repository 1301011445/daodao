# -*- coding: utf-8 -*-
"""高点分布体检：看每句旋律峰值、全曲最高音出现次数、以及副歌/主歌音区差。
只读结构，不渲音频。"""
import importlib.util, io, os

SONGS = [(r'F:\Daodao\tools\音乐\故乡歌\故乡歌.py', '归途的月光'),
         (r'F:\Daodao\tools\音乐\打工人歌\打工人歌.py', '把好日子扛在肩上')]

def load(p):
    spec = importlib.util.spec_from_file_location('m%d' % abs(hash(p)), p)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

for p, name in SONGS:
    m = load(p)
    notes, mel, secs = m.build()
    peaks = [x['peaks'] for x in mel]
    top = max(peaks)
    print('【%s】全曲最高音 %d ｜ 出现于 %d 句 / 共 %d 句' % (name, top, peaks.count(top), len(peaks)))
    for i, x in enumerate(mel):
        flag = '★' if x['peaks'] == top else ' '
        print('  %2d %s %s 「%s」 峰 %d' % (i, flag, '副' if x['chorus'] else '主', x['text'], x['peaks']))
    v = [x['peaks'] for x in mel if not x['chorus']]
    c = [x['peaks'] for x in mel if x['chorus']]
    if v and c:
        print('  主歌峰值区间 %d–%d ｜ 副歌峰值区间 %d–%d ｜ 差 %d 半音\n'
              % (min(v), max(v), min(c), max(c), max(c) - max(v)))
