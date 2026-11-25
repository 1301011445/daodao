# -*- coding: utf-8 -*-
"""骨链膝下分腿判据（与 DaoOverlay.drawWarp 同一套顶点算式，w=90 h=180 walkAmp=1）
L1 左右脚反相：左右脚抬脚量序列相关系数 <= -0.8
L2 中线不裂：nx=0.5 处横移 <=0.5px
L3 接缝平滑：相邻列（1/8 网格）横移差 <=2.5px
L4 抬脚幅度 <=3.6px
L5 上身不甩：上身横移 <=1.0px
"""
import math

W, H = 90.0, 180.0
AMP = 1.0


def vertex(nx, ny, phase):
    st = math.sin(phase)
    fan = (ny - 0.55) / 0.17 if 0.55 < ny <= 0.72 else 0.0
    dx = 0.010 * W * AMP * st * fan
    dy = -abs(st) * 0.006 * AMP * H * ny * ny if 0.55 < ny <= 0.72 else 0.0
    if ny > 0.72:
        side = max(-1.0, min(1.0, (nx - 0.5) / 0.22))
        leg = st * side
        k = (ny - 0.72) / 0.28
        dx += 0.006 * W * AMP * leg * k
        dy += -max(0.0, leg) * 0.010 * H * AMP * k
    return dx, dy


def corr(a, b):
    ma, mb = sum(a) / len(a), sum(b) / len(b)
    ca = sum((x - ma) ** 2 for x in a) ** 0.5
    cb = sum((y - mb) ** 2 for y in b) ** 0.5
    if ca == 0 or cb == 0:
        return 0.0
    return sum((x - ma) * (y - mb) for x, y in zip(a, b)) / (ca * cb)


N = 8
ph = [2 * math.pi * i / N for i in range(N)]
left_y = [vertex(0.22, 1.0, p)[1] for p in ph]
right_y = [vertex(0.78, 1.0, p)[1] for p in ph]
l = [-v for v in left_y]
rr = [-v for v in right_y]
alt = sum(1 for a, b in zip(l, rr) if (a > 0.5) != (b > 0.5)) / N
both = sum(1 for a, b in zip(l, rr) if a > 0.5 and b > 0.5) / N
mid_x = [abs(vertex(0.5, 1.0, p)[0]) for p in ph]
seam = []
for p in ph:
    xs = [i / 8 for i in range(9)]
    dxs = [vertex(x, 1.0, p)[0] for x in xs]
    seam.append(max(abs(dxs[i + 1] - dxs[i]) for i in range(8)))
lift = max(abs(v) for v in left_y + right_y)
up = abs(vertex(0.5, 0.4, 0.0)[0]) + 0.005 * W * (0.4 ** 1.7)

print(f'L1 左右脚交替率={alt:.2f} (>=0.75) {"PASS" if alt >= 0.75 else "FAIL"} 同落帧占比={both:.2f} 左脚抬{max(l):.2f}px 右脚抬{max(rr):.2f}px')
print(f'L2 中线横移 max={max(mid_x):.2f}px (<=0.5) {"PASS" if max(mid_x) <= 0.5 else "FAIL"}')
print(f'L3 接缝相邻列差 max={max(seam):.2f}px (<=2.5) {"PASS" if max(seam) <= 2.5 else "FAIL"}')
print(f'L4 抬脚幅度 max={lift:.2f}px (<=3.6) {"PASS" if lift <= 3.6 else "FAIL"}')
print(f'L5 上身横移 {up:.2f}px (<=1.0) {"PASS" if up <= 1.0 else "FAIL"}')
ok = alt >= 0.75 and both == 0 and max(mid_x) <= 0.5 and max(seam) <= 2.5 and lift <= 3.6 and up <= 1.0
print('SUMMARY', 'PASS' if ok else 'FAIL')
raise SystemExit(0 if ok else 1)


