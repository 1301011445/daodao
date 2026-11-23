# -*- coding: utf-8 -*-
"""把四位歌手的「唱法模板」写进 音色库.json（人工设定，不是采样测量）。
features 只作为目标值给合成侧参照：mix 上限 0.55，且与 dao_base 加权。
"""
import json, io, os

P = r'F:\Daodao\tools\音乐\音色\音色库.json'
d = json.load(io.open(P, encoding='utf-8'))
base = d['dao_base']
prof = d.setdefault('profiles', {})

TPL = {
    '单依纯': dict(
        feats=dict(f0=224.0, range_semi=11.0, vib_rate=5.4, vib_depth=0.03, breath=0.34,
                   centroid=2380.0, tilt=0.58, dyn=0.72),
        mix=0.45,
        唱法=dict(气声='气包声，弱混保持闭合', 尾音='弱收 + 句中气口停顿', 咬字='句尾微糊、关键字单列',
                 听感='弱而不虚，私语感'),
        note='学「弱到极限还不塌」与句尾弱收；不学她的高频换气密度（机能，硬塞会变喘）'),
    '李健': dict(
        feats=dict(f0=132.0, range_semi=12.0, vib_rate=5.0, vib_depth=0.02, breath=0.12,
                   centroid=2020.0, tilt=0.47, dyn=0.40),
        mix=0.45,
        唱法=dict(气声='少而通透，靠高位置', 尾音='气不断、轻提半音', 咬字='字正腔圆、喉舌分离',
                 听感='空灵、悬在将破未破'),
        note='学「高位置 + 弱混当修饰 + 长句不换气」；不用他的音域，男声只借质感'),
    '那英': dict(
        feats=dict(f0=182.0, range_semi=13.0, vib_rate=5.6, vib_depth=0.06, breath=0.08,
                   centroid=1720.0, tilt=0.74, dyn=0.86),
        mix=0.45,
        唱法=dict(气声='少，胸声打底', 尾音='先稳再颤，颤得宽', 咬字='靠后、有宽度、关键字咬长',
                 听感='厚、直给、有重量'),
        note='学「靠倾斜与共振压出厚度而不是加音量」「段落之间要有落差」；颤音别句句用'),
    '王菲': dict(
        feats=dict(f0=236.0, range_semi=12.0, vib_rate=6.6, vib_depth=0.025, breath=0.29,
                   centroid=2310.0, tilt=0.56, dyn=0.46),
        mix=0.45,
        唱法=dict(气声='极少气息仍有质感', 尾音='弱收 / 突然截断 / 拉长降调 三选一',
                 咬字='松弛写意、允许半句', 听感='气息当画笔，该推处卸劲'),
        note='学「延迟起颤 + 尾音三种收法轮换 + 副歌敢卸劲」；不做她的音色复刻（解剖条件不可复制）'),
}

for name, t in TPL.items():
    prof[name] = {
        'feats': t['feats'],
        'source': '风格参照（人工设定，非采样测量）',
        'at': '2026-11-23',
        'like': None,
        'mix': t['mix'],
        '唱法': t['唱法'],
        'note': t['note'],
    }

# 与道自己的底子做一次加权，给出「实际可用」的混后值，便于合成侧直接取
for name, t in TPL.items():
    f = t['feats']
    blended = {k: round(f[k] * t['mix'] + base[k] * (1 - t['mix']), 3) for k in f}
    prof[name]['blended_55'] = blended

json.dump(d, io.open(P, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('profiles:', list(prof.keys()))
for name in TPL:
    print(name, 'mix=', prof[name]['mix'], 'blended=', prof[name]['blended_55'])
