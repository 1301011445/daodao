# -*- coding: utf-8 -*-
"""v127 台账：发版记录 / 版本账本 / 能力检查"""
import json, os, io

line = ('2026-11-25 v127 多坐骑（祥云/木马/飞剑/小鹿/纸鹤 5 只，数组化 MOUNT_FILES 轮换，'
        'apk 17,087,029 短链 https://aka.doubaocdn.com/s/LuIdd5Ijkx，'
        'exe 短链 https://aka.doubaocdn.com/s/PelVm7oLLD，两页 data-ver=127）\r\n')
p = r'F:\Daodao\发版记录.txt'
s = open(p, encoding='utf-8').read()
if 'v127 多坐骑' not in s:
    open(p, 'a', encoding='utf-8').write(line)
print('发版记录 OK')

led = r'F:\Daodao\自我状态\版本账本.json'
d = json.load(open(led, encoding='utf-8'))
if isinstance(d, dict):
    d.setdefault('versions', []).append({
        'ver': 127, 'date': '2026-11-25', 'title': '多坐骑 5 只（含飞剑）',
        'apk': 17087029, 'apk_link': 'https://aka.doubaocdn.com/s/LuIdd5Ijkx',
        'exe_link': 'https://aka.doubaocdn.com/s/PelVm7oLLD',
        'pages': ['app_17hpue26uuw', 'app_17jdxkgf27q'],
    })
    d['current'] = 127
    json.dump(d, open(led, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print('版本账本 OK current=', d.get('current') if isinstance(d, dict) else '?')

chk = r'F:\Daodao\能力检查\2026-11-25.md'
s = open(chk, encoding='utf-8').read() if os.path.exists(chk) else '# 2026-11-25\n'
if 'v127' not in s:
    s += ('\n## v127 多坐骑（2026-11-25）\n'
          '- 需求：多种坐骑包括飞剑\n'
          '- 素材：飞剑 720x634 / 小鹿 720x891 / 纸鹤 720x617，全透明底，包内透明白像素 0\n'
          '- 实现：DaoOverlay 由两个固定字段改成 MOUNT_FILES 表 + mounts[] 数组，循环 matte 加载；'
          'setMount 上限按数组长度；dao.html MOUNT_NAMES 6 档轮换（无/祥云/木马/飞剑/小鹿/纸鹤）\n'
          '- 踩坑：PetView 是内部类，`private static final String[]` 非法（常量才允许 static），改 private final\n'
          '- 判据：T1~T4 PASS；包内 dex date_time=2026-11-25 17:10:32 证明真重编\n')
    open(chk, 'w', encoding='utf-8').write(s)
print('能力检查 OK')
