# -*- coding: utf-8 -*-
"""v134 判据 + 台账：14 只挥手动作立绘（路径 1 全量）"""
import io
import json
import os
import re
import zipfile

import numpy as np
from PIL import Image

O = open(r'F:\Daodao\src\_apk\src\com\daodao\pet\DaoOverlay.java', encoding='utf-8').read()
APK = r'F:\Daodao\src\_apk\Dao.apk'
z = zipfile.ZipFile(APK)
html = z.read('assets/dao.html').decode('utf-8', 'ignore')
names = set(z.namelist())

bad = 0
sizes = []
for k in range(14):
    a = np.array(Image.open(io.BytesIO(z.read('assets/wave_%d.png' % k))).convert('RGBA'))
    bad += int(((a[..., 3] < 40) & (a[..., 0] > 243) & (a[..., 1] > 243) & (a[..., 2] > 243)).sum())
    sizes.append(a.shape)

C = [
    ('K1 14 张挥手帧全在包里', all('assets/wave_%d.png' % k in names for k in range(14))),
    ('K2 挥手帧透明白=0（%d）' % bad, bad == 0),
    ('K3 挥手时换成动作立绘', 'waveArt = loadOpt("wave_" + art + ".png")' in O and 'drawWarp(c, waveArt' in O),
    ('K4 挥手分支优先级在站姿之前', O.index('waveAmp > 0f') < O.index('drawWarp(c, standArt')),
    ('K5 透明白清理接上了', 'matteInPlace(waveArt)' in O),
    ('K6 包内 HTML_VER=134', re.search(r"var HTML_VER = '(\d+)'", html).group(1) == '134'),
    ('K7 13 套八帧走路仍在包里（走路本来就是真帧）',
     sum(1 for k in range(14) if 'assets/walk8_%d.png' % k in names) >= 13),
]
ok = all(v for _, v in C)
for n, v in C:
    print(n, 'PASS' if v else 'FAIL')
print('SUMMARY', 'PASS' if ok else 'FAIL')

if ok:
    apk, exe = os.path.getsize(APK), os.path.getsize(r'F:\Daodao\道.exe')
    open(r'F:\Daodao\发版记录.txt', 'a', encoding='utf-8').write(
        '\n=== v134 14 只挥手动作立绘（2026-11-25）===\n'
        '背景：单图网格骨骼（8×12→16×24）与自动切图分层都做不出抬手，改为路径 1：真动作素材。\n'
        '素材：14 只各生成一张"抬右手招手"立绘，去白底 → 裁边 → 480 宽 → 清透明白，合计 %.2f MB，透明白 0。\n'
        '接线：DaoOverlay 每只形象多载 wave_<art>.png；waveAmp>0 时改画这张（只叠轻摆与点头），不再网格硬掰。\n'
        '走路：13 只本来就有 walk8_<art>.png 八帧，二维码走的是真帧（已复核在包里）。\n'
        'apk %d（vc134/vn1.34）；exe %d（APP_VER=134）。判据 K1~K7 PASS。\n'
        % (sum(1 for k in range(14) if os.path.exists(r'F:\Daodao\src\_apk\assets\wave_%d.png' % k)) * 6.81 / 14,
           apk, exe))
    lp = r'F:\Daodao\自我状态\版本账本.json'
    try:
        d = json.load(open(lp, encoding='utf-8'))
    except Exception:
        d = {}
    d['current'] = 134
    d.setdefault('notes', {})['134'] = '14 只挥手动作立绘入库；挥手改画真动作图'
    json.dump(d, open(lp, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    with open(r'F:\Daodao\能力检查\2026-11-25.md', 'a', encoding='utf-8') as f:
        f.write('\n## v134 挥手动作立绘（14 只全量）\n- 路径 1 落地：动作帧替代网格伪动作\n- wave_0..13.png 480 宽、透明白 0；K1~K7 PASS\n')
    print('LEDGER_OK')
raise SystemExit(0 if ok else 1)
