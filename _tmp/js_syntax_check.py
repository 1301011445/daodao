# -*- coding: utf-8 -*-
"""把 dao.html 里的内联 <script> 抠出来，逐块交给 node --check 做语法校验"""
import io, os, re, subprocess, sys, tempfile

HTML = r'F:\Daodao\src\_apk\assets\dao.html'
NODE = r'C:\Users\LDY\AppData\Local\Doubao\User Data\sandbox_runtime\bases\fa694f517e5995233c80a9a8db5212c2\node\node.exe'
if not os.path.exists(NODE):
    sys.exit('没有 node')

s = io.open(HTML, encoding='utf-8', errors='ignore').read()
blocks = re.findall(r'<script[^>]*>(.*?)</script>', s, re.S)
print('内联脚本块：%d 个' % len(blocks))

tmp = tempfile.mkdtemp()
bad = 0
for i, b in enumerate(blocks):
    if len(b.strip()) < 40:
        continue
    p = os.path.join(tmp, 'blk%02d.js' % i)
    io.open(p, 'w', encoding='utf-8').write(b)
    r = subprocess.run([NODE, '--check', p], capture_output=True, text=True, encoding='utf-8', errors='ignore')
    tag = 'OK' if r.returncode == 0 else 'ERR'
    looks_music = ('SONGS' in b) or ('musicPanel' in b) or ('DAO_MUSIC' in b)
    print('  块%02d %s %s %s' % (i, tag, ('[含曲库]' if looks_music else ''), '' if r.returncode == 0 else r.stderr.strip().splitlines()[:3]))
    if r.returncode != 0:
        bad += 1
print('语法失败块：%d' % bad)
