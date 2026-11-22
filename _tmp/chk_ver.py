# -*- coding: utf-8 -*-
import re, os
p = r'F:\Daodao\src\_apk\assets\dao.html'
s = open(p, encoding='utf-8', errors='ignore').read()
print('dao.html HTML_VER =', re.findall("HTML_VER\\s*=\\s*'(\\d+)'", s)[:3])
for f in [r'C:\Users\LDY\Doubao\chats\2026-11-11\new-chat\vermanifest\index.html',
          r'C:\Users\LDY\Doubao\chats\2026-11-11\new-chat\道落地页\道_落地页_v069.html']:
    t = open(f, encoding='utf-8', errors='ignore').read()
    print(os.path.basename(f), 'data-ver=', re.findall('data-ver="(\\d+)"', t)[:2], 'vbadge=', re.findall('vbadge[^>]*?v(\\d+)', t)[:2])
src = open(r'F:\Daodao\tools\版本奖惩.py', encoding='utf-8', errors='ignore').read()
for line in src.splitlines():
    if 'ROOT' in line and '=' in line and 'ver_land' in line:
        print('LINE:', line.strip())
for line in src.splitlines():
    if 'ver_land' in line:
        print('V:', line.strip()[:120])
