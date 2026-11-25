# -*- coding: utf-8 -*-
"""v131 判据 + 台账：骑姿上鞍（14 张骑姿图、臀落鞍位、坐骑下标修正）"""
import json
import os
import re
import zipfile

P = r'F:\Daodao\src\_apk\src\com\daodao\pet\DaoOverlay.java'
APK = r'F:\Daodao\src\_apk\Dao.apk'
j = open(P, encoding='utf-8').read()

C = []
C.append(('G1 骑姿配比进表', 'MOUNT_MHW = {0.32f, 0.52f, 0.34f, 0.50f, 0.46f}' in j and 'MOUNT_FR = {0.88f, 0.64f, 0.62f, 0.62f, 0.44f}' in j))
C.append(('G2 14 张骑姿真实加载', 'rides = new Bitmap[RIDE_FILES.length];' in j and '"ride_13.png"' in j))
C.append(('G3 有骑姿就先走骑姿', 'Bitmap rb = rideFor(art);' in j and 'drawRide(c, w, h, rb, mounts[mount - 1]);' in j))
C.append(('G4 臀落鞍位（逐只坐骨线）', 'saddleY - rh * sr' in j and 'RIDE_SEAT = {' in j))
C.append(('G5 坐骑下标不再越界', 'mount >= 1 && mount <= mounts.length ? mounts[mount - 1]' in j))

z = zipfile.ZipFile(APK)
html = z.read('assets/dao.html').decode('utf-8', 'ignore')
C.append(('G6 包内 HTML_VER=131', re.search(r"var HTML_VER = '(\d+)'", html).group(1) == '131'))
names = set(z.namelist())
C.append(('G7 包内 14 张骑姿齐全', all('assets/ride_%d.png' % k in names for k in range(14))))
import numpy as np
from PIL import Image
import io
bad = 0
for k in range(14):
    a = np.array(Image.open(io.BytesIO(z.read('assets/ride_%d.png' % k))).convert('RGBA'))
    bad += int(((a[..., 3] < 40) & (a[..., 0] > 243) & (a[..., 1] > 243) & (a[..., 2] > 243)).sum())
C.append(('G8 骑姿透明白=0（%d）' % bad, bad == 0))

ok = all(v for _, v in C)
for n, v in C:
    print(n, 'PASS' if v else 'FAIL')
print('SUMMARY', 'PASS' if ok else 'FAIL')

if ok:
    apk = os.path.getsize(APK)
    exe = os.path.getsize(r'F:\Daodao\道.exe')
    rec = ('\n=== v131 骑姿上鞍（2026-11-25 17:5x）===\n'
           '问题：人物与坐骑"站着叠在一起"，不是骑；姿势不对、比例不配。\n'
           '做法：给 14 个形象各生成一张**真跨坐骑姿立绘**（腿分开、膝弯、脚垂两侧），透明底入库；\n'
           '      Java 里坐骑高/鞍面高按坐骑自己比例（MHW: 0.32/0.52/0.34/0.50/0.46，FR: 0.88/0.64/0.62/0.62/0.44），\n'
           '      人物按"坐骨线"（逐只量出来的 0.579~0.68）压到鞍面上，人高 = 视窗 0.62；\n'
           '      顺手修掉 mounts[mount] 下标越界（纸鹤此前永远画不出来）。\n'
           '素材：ride_0..13.png 均 480 宽、合计 4.60MB、透明白 0。\n'
           'apk %d（vc131/vn1.31，HTML_VER=131）；exe %d（APP_VER=131）。\n'
           '短链：apk https://aka.doubaocdn.com/s/hWhJPj5z93 ； exe https://aka.doubaocdn.com/s/U6UHcamTJG\n'
           '判据 G1~G8 全 PASS。\n') % (apk, exe)
    open(r'F:\Daodao\发版记录.txt', 'a', encoding='utf-8').write(rec)
    lp = r'F:\Daodao\自我状态\版本账本.json'
    try:
        d = json.load(open(lp, encoding='utf-8'))
    except Exception:
        d = {}
    d['current'] = 131
    d.setdefault('notes', {})['131'] = '骑姿上鞍：14 张跨坐立绘，臀落鞍位，修坐骑下标越界'
    json.dump(d, open(lp, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    with open(r'F:\Daodao\能力检查\2026-11-25.md', 'a', encoding='utf-8') as f:
        f.write('\n## v131 骑姿上鞍\n- 14 张骑姿立绘入库（480 宽 / 透明白 0 / 4.60MB），Java 按坐骨线压鞍面\n'
                '- 修 mounts[mount] 越界：纸鹤此前画不出来\n- apk %d / exe %d，G1~G8 PASS\n' % (apk, exe))
    print('LEDGER_OK')
raise SystemExit(0 if ok else 1)
