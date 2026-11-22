# -*- coding: utf-8 -*-
"""修复 ps1 版本头位置：BOM 只能在文件最前，版本头必须在 BOM 之后的第一行"""
import io, json, os

rec = json.load(io.open(r'F:\Daodao\tools\程序版本记录.json', encoding='utf-8'))
fixed = []
for p in rec['程序']:
    path = p['路径']
    if not path.lower().endswith('.ps1') or not os.path.exists(path):
        continue
    text = io.open(path, encoding='utf-8-sig', errors='replace').read()
    text = text.replace('\ufeff', '')
    lines = text.split('\n')
    hdr = None
    for i, l in enumerate(lines):
        if l.startswith('# 程序版本：'):
            hdr = l.strip()
            del lines[i]
            break
    if hdr is None:
        hdr = '# 程序版本：v0.1 | 2026-11-22 | 基线建档'
    io.open(path, 'w', encoding='utf-8-sig').write(hdr + '\n' + '\n'.join(lines))
    fixed.append(os.path.basename(path))
print('修复 ps1：', fixed)
