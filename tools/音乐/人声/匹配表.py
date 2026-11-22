# -*- coding: utf-8 -*-
"""词-曲-音色 的对照表：检查器和合成器共用同一份，避免一边一个说法。"""

MOOD = {
    '清早': 'bright', '敞亮': 'bright', '小跑': 'bright', '太阳': 'bright',
    '做成样': 'steady', '照常': 'steady', '漂亮': 'steady',
    '街灯': 'warm', '家里灯光': 'warm', '累了': 'warm',
    '肩上': 'strong', '成长': 'strong', '风大雨急': 'strong', '点亮': 'strong',
    '平常人': 'calm', '慢慢走': 'calm', '不慌张': 'calm', '更强': 'strong',
}

MOOD_TARGET = {
    'bright': dict(centroid=1.10, breath=0.85, vib=1.00, reg=0.0),
    'steady': dict(centroid=1.00, breath=0.90, vib=1.00, reg=0.0),
    'warm':   dict(centroid=0.90, breath=1.15, vib=0.85, reg=-1.0),
    'strong': dict(centroid=1.08, breath=0.80, vib=1.15, reg=1.0),
    'calm':   dict(centroid=0.92, breath=1.05, vib=0.75, reg=-0.5),
}

ROLE = {
    'V':  dict(voices=['M'], reg=0.0),
    'C1': dict(voices=['M'], reg=1.0),
    'V2': dict(voices=['F'], reg=-0.6),
    'C2': dict(voices=['F', 'M'], reg=0.4),
    'B':  dict(voices=['F'], reg=1.4),
    'C3': dict(voices=['M', 'F'], reg=1.6),
}

# 合成阶段按段落补的「唱法修正」：高频提亮 dB、气声倍率、颤音倍率
TAG_FIX = {
    'V':  dict(bright_db=1.6, breath=0.85, vib=0.95),
    'C1': dict(bright_db=1.8, breath=0.90, vib=1.05),
    'V2': dict(bright_db=0.4, breath=1.10, vib=0.85),
    'C2': dict(bright_db=1.4, breath=1.00, vib=1.10),
    'B':  dict(bright_db=0.6, breath=1.05, vib=0.80),
    'C3': dict(bright_db=1.6, breath=1.00, vib=1.15),
}
