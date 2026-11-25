# -*- coding: utf-8 -*-
"""包内素材检查：apk 里真正要用的 walk8.png 与 dao.html 版本
判据：P1 包内 walk8 尺寸 1536x384；P2 透明区纯白像素 ==0（白边根因已消）；
     P3 HTML_VER 与本次版本号一致；P4 包内 walk8 字节数与源文件一致
"""
import io, re, sys, zipfile
import numpy as np
from PIL import Image

APK = sys.argv[1] if len(sys.argv) > 1 else r'F:\Daodao\道.apk'
VER = sys.argv[2] if len(sys.argv) > 2 else '118'
SRC = r'F:\Daodao\src\_apk\assets\walk8.png'

z = zipfile.ZipFile(APK)
d = z.read('assets/walk8.png')
im = Image.open(io.BytesIO(d)).convert('RGBA')
a = np.array(im).astype(np.float32)
t = a[..., 3] < 10
white = int((t & (a[..., :3].min(axis=2) > 240)).sum())
html = z.read('assets/dao.html').decode('utf-8', 'ignore')
hv = re.search(r"HTML_VER\s*=\s*'([0-9]+)'", html)
hv = hv.group(1) if hv else 'NONE'
src_len = len(open(SRC, 'rb').read())
p1 = im.size == (1536, 384)
p2 = white == 0
p3 = hv == VER
p4 = len(d) == src_len
print(f'包内 walk8: {len(d)} 字节 尺寸={im.size} 透明白底像素={white}')
print(f'包内 HTML_VER={hv} 源文件字节={src_len}')
print(f'P1 尺寸 {im.size}==(1536,384) {"PASS" if p1 else "FAIL"}')
print(f'P2 白底像素 {white}==0 {"PASS" if p2 else "FAIL"}')
print(f'P3 HTML_VER {hv}=={VER} {"PASS" if p3 else "FAIL"}')
print(f'P4 字节数 {len(d)}=={src_len} {"PASS" if p4 else "FAIL"}')
print('SUMMARY', 'PASS' if all([p1, p2, p3, p4]) else 'FAIL')
sys.exit(0 if all([p1, p2, p3, p4]) else 1)
