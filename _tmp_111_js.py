# 2026-11-22 一次性：把 dao.html 里的 <script> 块抠出来，逐块过 node --check
# 用法: python _tmp_111_js.py
import re, os, subprocess, sys

HTML = r'F:\Daodao\src\_apk\assets\dao.html'
NODE = r'C:\Users\LDY\AppData\Local\Doubao\User Data\sandbox_runtime\bases\fa694f517e5995233c80a9a8db5212c2\node\node.exe'
OUT  = r'F:\Daodao\_chk111.js'

s = open(HTML, encoding='utf-8').read()
blocks = re.findall(r'<script[^>]*>(.*?)</script>', s, re.S | re.I)
print('script blocks =', len(blocks))
bad = 0
for i, b in enumerate(blocks):
    open(OUT, 'w', encoding='utf-8').write(b)
    r = subprocess.run([NODE, '--check', OUT], capture_output=True, text=True)
    if r.returncode != 0:
        bad += 1
        print('BLOCK', i, 'FAIL')
        print(r.stderr[:1200])
    else:
        print('BLOCK', i, 'ok', len(b), 'chars')
print('JSCHECK', 'PASS' if bad == 0 else 'FAIL', bad)
os.remove(OUT) if os.path.exists(OUT) else None
