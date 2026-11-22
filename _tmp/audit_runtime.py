# -*- coding: utf-8 -*-
"""巡检耗时与判据一览（2026-11-22 做，用于决定每个巡检放进哪一轮）"""
import subprocess, time, os, sys

PY = r'E:\Python313\python.exe'
items = [
    ('自检.py', [r'F:\Daodao\tools\自检.py']),
    ('版本机制.py', [r'F:\Daodao\tools\版本机制.py']),
    ('版本奖惩.py', [r'F:\Daodao\tools\版本奖惩.py']),
    ('愉悦值检查.py', [r'F:\Daodao\tools\愉悦值检查.py']),
    ('纠错体检.py', [r'F:\Daodao\tools\纠错体检.py']),
    ('学习复现日历.py', [r'F:\Daodao\tools\学习复现日历.py']),
    ('能力激励.py', [r'F:\Daodao\tools\能力激励.py']),
    ('回忆.py', [r'F:\Daodao\tools\回忆.py', 'stat']),
    ('归档.py', [r'F:\Daodao\tools\音乐\学习归档\归档.py']),
    ('判据检查.py', [r'F:\Daodao\tools\音乐\判据检查\判据检查.py']),
    ('触控热区检查.py', [r'F:\Daodao\tools\界面\触控热区检查.py']),
]
print('%-22s %6s  %s' % ('脚本', '秒', '末行'))
print('-' * 88)
for name, args in items:
    t0 = time.time()
    p = subprocess.run([PY] + args, capture_output=True, text=True, encoding='utf-8', errors='replace')
    dt = time.time() - t0
    tail = [l for l in (p.stdout or '').strip().splitlines() if l.strip()]
    print('%-22s %6.1f  %s' % (name, dt, (tail[-1][:70] if tail else '(无输出)')))
