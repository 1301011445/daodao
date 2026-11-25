# -*- coding: utf-8 -*-
"""v134 2.5D 骨骼层预览：把立绘拆成「上身 + 左右臂 + 左右腿」五个骨头，
绕各自的关节转，用与 Java drawWarp 同构的 8×12 网格前向变形画出来。
先在这里把参数调顺，再原样搬进 DaoOverlay.drawWarp。
"""
import math
import os
from PIL import Image

A = r'F:\Daodao\src\_apk\assets'
OUT = r'F:\Daodao\形象\_2.5D骨骼预览.png'
COLS, ROWS = 16, 24

# 关节（归一化：x 按宽、y 按高）
J = {
    'body': (0.50, 0.52),   # 腰
    'armL': (0.27, 0.30),   # 左肩
    'armR': (0.73, 0.30),   # 右肩
    'legL': (0.45, 0.56),   # 左髋
    'legR': (0.55, 0.56),   # 右髋
}


def gauss(nx, ny, cx, cy, sx, sy):
    return math.exp(-(((nx - cx) / sx) ** 2 + ((ny - cy) / sy) ** 2))


def weights(nx, ny):
    armL = gauss(nx, ny, 0.20, 0.36, 0.050, 0.13) * (1.0 if ny < 0.60 else 0.0)
    armR = gauss(nx, ny, 0.80, 0.36, 0.050, 0.13) * (1.0 if ny < 0.60 else 0.0)
    legL = gauss(nx, ny, 0.40, 0.74, 0.13, 0.22) * (1.0 if ny > 0.48 else 0.0)
    legR = gauss(nx, ny, 0.60, 0.74, 0.13, 0.22) * (1.0 if ny > 0.48 else 0.0)
    body = 0.55
    raw = [body, armL, armR, legL, legR]
    tot = sum(raw)
    return [v / tot for v in raw]


def rot(px, py, jx, jy, ang):
    a = math.radians(ang)
    dx, dy = px - jx, py - jy
    return jx + dx * math.cos(a) - dy * math.sin(a), jy + dx * math.sin(a) + dy * math.cos(a)


def angles(kind, t):
    """返回 5 个骨头的角度（度）"""
    if kind == 'wave':
        return (0.0, 0.0, -40 - 45 * (0.5 + 0.5 * math.sin(t * 6.0)), 0.0, 0.0)   # 右手抬到侧上方挥
    if kind == 'walk':
        s = math.sin(t * 5.5)
        return (1.6 * s, -11 * s, 11 * s, 15 * s, -15 * s)
    if kind == 'dance':
        s = math.sin(t * 5.0)
        return (5.0 * s, 34 * s, -34 * s, 12 * s, -12 * s)
    return (0.0, 0.0, 0.0, 0.0, 0.0)


def warp(im, kind, t):
    W, H = im.size
    mesh = []
    cw, ch = W / COLS, H / ROWS
    for r in range(ROWS):
        for c in range(COLS):
            quad = []
            # PIL 要求角点顺序：左上、左下、右下、右上
            for (vx, vy) in ((c, r), (c, r + 1), (c + 1, r + 1), (c + 1, r)):
                nx, ny = vx / COLS, vy / ROWS
                px, py = nx * W, ny * H
                wts = weights(nx, ny)
                ang = angles(kind, t)
                dx = dy = 0.0
                for wi, key in zip(wts, ('body', 'armL', 'armR', 'legL', 'legR')):
                    if wi <= 0.0:
                        continue
                    jx, jy = J[key][0] * W, J[key][1] * H
                    qx, qy = rot(px, py, jx, jy, ang[('body', 'armL', 'armR', 'legL', 'legR').index(key)])
                    dx += wi * (qx - px)
                    dy += wi * (qy - py)
                quad.append((px + dx, py + dy))
            flat = [int(round(v)) if i % 2 == 0 else v for i, v in enumerate([q for pt in quad for q in pt])]
            box = (int(round(c * cw)), int(round(r * ch)), int(round((c + 1) * cw)), int(round((r + 1) * ch)))
            mesh.append((box, flat))
    return im.transform((W, H), Image.MESH, mesh, Image.BILINEAR, fillcolor=(0, 0, 0, 0))


def strip(art, kind, ts, cw=260):
    im = Image.open(os.path.join(A, art)).convert('RGBA')
    h = int(cw * im.height / im.width)
    im = im.resize((cw, h), Image.LANCZOS)
    frames = [warp(im, kind, t) for t in ts]
    row = Image.new('RGBA', (cw * len(frames) + 6 * (len(frames) - 1), h), (14, 16, 24, 255))
    for i, f in enumerate(frames):
        row.alpha_composite(f, (i * (cw + 6), 0))
    return row


TS = [i * 1.0 / 8 * 1.6 for i in range(8)]   # 一个周期分 8 拍
rows = []
for art in ('stand_0.png', 'stand_10.png'):
    for kind in ('wave', 'walk', 'dance'):
        rows.append(strip(art, kind, TS))
rowh = [r.height for r in rows]
sheet = Image.new('RGBA', (max(r.width for r in rows), sum(rowh) + 6 * (len(rows) - 1)), (10, 12, 18, 255))
y = 0
for r in rows:
    sheet.alpha_composite(r, (0, y))
    y += r.height + 6
sheet.save(OUT)
print('2.5D 预览 ->', OUT, sheet.size, '行序：少年 挥/走/跳，少女 挥/走/跳')
