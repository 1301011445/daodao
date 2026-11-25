# -*- coding: utf-8 -*-
"""apk 内全部形象素材白底普查
W1 每个 walk8*/peek*/ball* 的"透明且近白"像素数 == 0
W2 包内 HTML_VER == 指定版本
"""
import io, re, sys, zipfile
import numpy as np
from PIL import Image

APK = sys.argv[1] if len(sys.argv) > 1 else r'F:\Daodao\道.apk'
VER = sys.argv[2] if len(sys.argv) > 2 else '119'

z = zipfile.ZipFile(APK)
bad, tot = [], 0
for n in z.namelist():
    if not (n.startswith('assets/') and n.endswith('.png')):
        continue
    base = n.split('/')[-1]
    if not ('walk8' in base or 'peek' in base or base == 'ball.png' or base.startswith('ball_')):
        continue
    a = np.array(Image.open(io.BytesIO(z.read(n))).convert('RGBA')).astype(np.float32)
    t = a[..., 3] < 10
    w = int((t & (a[..., :3].min(axis=2) > 240)).sum())
    tot += 1
    if w:
        bad.append((base, w))
    print(f'  {base:18s} 透明白底={w}')
h = z.read('assets/dao.html').decode('utf-8', 'ignore')
hv = re.search(r"HTML_VER\s*=\s*'([0-9]+)'", h)
hv = hv.group(1) if hv else 'NONE'
print(f'W1 素材 {tot} 个，白底未清 {len(bad)} 个 {bad[:4]} {"PASS" if len(bad) == 0 else "FAIL"}')
print(f'W2 包内 HTML_VER={hv} 期望={VER} {"PASS" if hv == VER else "FAIL"}')
ok = len(bad) == 0 and hv == VER
print('SUMMARY', 'PASS' if ok else 'FAIL')
sys.exit(0 if ok else 1)
