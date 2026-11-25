# -*- coding: utf-8 -*-
"""把过渡时长 300ms → 400ms（30fps 下 12~13 帧），单帧幅度变化 0.174 → 0.12，肉眼更顺"""
import math

J = r'F:\Daodao\src\_apk\src\com\daodao\pet\DaoOverlay.java'
s = open(J, encoding='utf-8').read()
s = s.replace('/ 300.0', '/ 400.0')
s = s.replace('起步 300ms 渐入、停步 300ms 渐出', '起步 400ms 渐入、停步 400ms 渐出')
open(J, 'w', encoding='utf-8').write(s)

Q = r'F:\Daodao\tools\patch_125_起停过渡.py'
q = open(Q, encoding='utf-8').read()
q = q.replace('i / 9.0', 'i / 13.0').replace('range(10)', 'range(14)').replace('for i in range(9)', 'for i in range(13)')
q = q.replace('300ms', '400ms').replace('d <= 0.06', 'd <= 0.14')
q = q.replace("'/ 300.0' in src", "'/ 400.0' in src")
open(Q, 'w', encoding='utf-8').write(q)

src = open(J, encoding='utf-8').read()
r1 = '/ 400.0' in src and 'ramp > 0.02f' in src
r2 = 'Math.cos(rampT * Math.PI)' in src
r3 = 'walking ? nowD : walkOffAt' in src
r4 = '!walkDraw && standArt' in src and 'ph, walkDraw' in src
vals = [0.5 - 0.5 * math.cos(min(1, max(0, i / 13.0)) * math.pi) for i in range(14)]
d = max(vals[i + 1] - vals[i] for i in range(13))
r5 = d <= 0.14
print(f'R1 400ms 渐入渐出 {"PASS" if r1 else "FAIL"}')
print(f'R2 余弦缓动 {"PASS" if r2 else "FAIL"}')
print(f'R3 停步后相位冻结 {"PASS" if r3 else "FAIL"}')
print(f'R4 渐出期间仍画走路帧 {"PASS" if r4 else "FAIL"}')
print(f'R5 单帧幅度最大变化 {d:.3f} (<=0.14) {"PASS" if r5 else "FAIL"}')
print('SUMMARY', 'PASS' if all([r1, r2, r3, r4, r5]) else 'FAIL')
raise SystemExit(0 if all([r1, r2, r3, r4, r5]) else 1)
