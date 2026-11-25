# -*- coding: utf-8 -*-
"""v134 分层骨骼试点（路径 2）：把立绘切成 base + 左右臂 + 左右腿，各自绕关节转。
手臂按"外侧条带"切（贴着轮廓外沿，不切到躯干），切口羽化；切走留下的洞用同一行
内侧像素横向补上（毛衣/长袍这种大面积同色，补完看不出）。
"""
import math
import os

import numpy as np
from PIL import Image, ImageFilter

A = r'F:\Daodao\src\_apk\assets'
OUT = r'F:\Daodao\形象\_分层骨骼预览.png'


def bbox(im):
    a = np.array(im)[..., 3] > 40
    ys, xs = np.where(a)
    return xs.min(), ys.min(), xs.max() + 1, ys.max() + 1


def build(im):
    W, H = im.size
    a = np.array(im)
    sil = a[..., 3] > 60
    # 每行的轮廓左右边界
    xmin = np.full(H, W, int)
    xmax = np.full(H, -1, int)
    for y in range(H):
        xs = np.where(sil[y])[0]
        if xs.size:
            xmin[y], xmax[y] = xs.min(), xs.max()

    m_arm_r = np.zeros((H, W), np.float32)
    m_arm_l = np.zeros((H, W), np.float32)
    for y in range(int(H * 0.15), int(H * 0.60)):
        if xmax[y] < 0:
            continue
        rw = xmax[y] - xmin[y] + 1
        band = max(6, int(rw * 0.30))            # 手臂厚度取轮廓宽的 30%
        fade = max(3, int(band * 0.45))
        for i in range(band):                      # 右臂：从外沿往里
            x = xmax[y] - i
            if x < 0 or not sil[y, x]:
                continue
            wgt = 1.0 if i < band - fade else (band - i) / fade
            m_arm_r[y, x] = max(m_arm_r[y, x], wgt)
        for i in range(band):
            x = xmin[y] + i
            if x >= W or not sil[y, x]:
                continue
            wgt = 1.0 if i < band - fade else (band - i) / fade
            m_arm_l[y, x] = max(m_arm_l[y, x], wgt)

    # 腿：髋以下，按中线劈开，交界处 6px 羽化
    m_leg_l = np.zeros((H, W), np.float32)
    m_leg_r = np.zeros((H, W), np.float32)
    hip_y = int(H * 0.52)
    for y in range(hip_y, H):
        if xmax[y] < 0:
            continue
        cx = (xmin[y] + xmax[y]) / 2.0
        for x in range(xmin[y], xmax[y] + 1):
            if not sil[y, x]:
                continue
            d = abs(x - cx)
            wgt = min(1.0, d / 7.0)
            if x < cx:
                m_leg_l[y, x] = wgt
            else:
                m_leg_r[y, x] = wgt

    parts = {'armR': m_arm_r, 'armL': m_arm_l, 'legR': m_leg_r, 'legL': m_leg_l}
    # base = 原图去掉四肢；洞用同内侧像素补齐（再糊一下交界）
    base = a.copy()
    cover = np.maximum.reduce(list(parts.values()))
    hole = cover > 0.5
    for y in range(H):
        xs = np.where(hole[y] & sil[y])[0]
        if xs.size == 0:
            continue
        row = base[y]
        for x in xs:
            # 往内找第一个没被切掉的像素
            for step in range(1, W):
                xi = x - step if x < W // 2 else x + step
                if 0 <= xi < W and base[y, xi, 3] > 60 and not hole[y, xi]:
                    base[y, x] = base[y, xi]
                    break
    base_im = Image.fromarray(base, 'RGBA').filter(ImageFilter.GaussianBlur(0.4))

    cut = {}
    for k, m in parts.items():
        al = (a[..., 3] * m).astype(np.uint8)
        cut[k] = Image.fromarray(np.dstack([a[..., 0], a[..., 1], a[..., 2], al]).astype(np.uint8), 'RGBA')
    return base_im, cut, (xmin, xmax)


def pivot(cut_key, W, H):
    if cut_key in ('armR',):
        return (0.72 * W, 0.22 * H)
    if cut_key in ('armL',):
        return (0.28 * W, 0.22 * H)
    if cut_key in ('legR',):
        return (0.55 * W, 0.53 * H)
    return (0.45 * W, 0.53 * H)


def frame(art, angs, W, H):
    im = Image.open(os.path.join(A, art)).convert('RGBA')
    im = im.crop(bbox(im))
    im = im.resize((W, H), Image.LANCZOS)
    base, cut, _ = build(im)
    out = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    out.alpha_composite(base)
    for k in ('legL', 'legR', 'armL', 'armR'):
        a = angs.get(k, 0.0)
        if abs(a) < 0.5:
            out.alpha_composite(cut[k])
        else:
            jx, jy = pivot(k, W, H)
            rot = cut[k].rotate(a, resample=Image.BICUBIC, center=(jx, jy), fillcolor=(0, 0, 0, 0))
            out.alpha_composite(rot)
    return out


TS = [i * 1.6 / 8 for i in range(8)]
MOTIONS = [
    ('挥手', [{'armR': -35 - 40 * math.sin(t * 6.0)} for t in TS]),
    ('走路', [{'legL': 14 * math.sin(t * 11), 'legR': -14 * math.sin(t * 11),
              'armL': -9 * math.sin(t * 11), 'armR': 9 * math.sin(t * 11)} for t in TS]),
    ('跳舞', [{'legL': 10 * math.sin(t * 10), 'legR': -10 * math.sin(t * 10),
              'armL': 32 * math.sin(t * 10), 'armR': -32 * math.sin(t * 10)} for t in TS]),
]
CW, CH = 240, 480
rows = []
for nm, seq in MOTIONS:
    row = Image.new('RGBA', (CW * len(seq) + 6 * (len(seq) - 1), CH), (16, 18, 26, 255))
    for i, angs in enumerate(seq):
        f = frame('stand_0.png', angs, CW, CH)
        row.alpha_composite(f, (i * (CW + 6), 0))
    rows.append(row)
sheet = Image.new('RGBA', (rows[0].width, CH * 3 + 12), (10, 12, 18, 255))
for i, r in enumerate(rows):
    sheet.alpha_composite(r, (0, i * (CH + 6)))
sheet.convert('RGB').save(OUT, optimize=True)
print('分层骨骼预览 ->', OUT, sheet.size, '行序：挥手/走路/跳舞')
