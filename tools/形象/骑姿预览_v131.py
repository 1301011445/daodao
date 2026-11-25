# -*- coding: utf-8 -*-
"""v131 骑姿预览：坐姿压腿 + 双腿分开 + 坐骑鞍部盖住腿（三段合成）
1) 人物骨盆以下竖向压缩 12%（坐下去），双腿左右分开
2) 先画坐骑 → 再画人 → 最后把坐骑"鞍部那条"再贴一遍盖住腿
"""
import os
import numpy as np
from PIL import Image

A = r'F:\Daodao\src\_apk\assets'
OUT = r'F:\Daodao\形象\坐骑\_骑姿预览.png'
CFG = [
    ('mount_cloud.png', '祥云', 0.28, 0.86),
    ('mount_horse.png', '木马', 0.40, 0.62),
    ('mount_sword.png', '飞剑', 0.24, 0.46),
    ('mount_deer.png', '小鹿', 0.34, 0.58),
    ('mount_crane.png', '纸鹤', 0.40, 0.40),
]
VW, VH = 480, 640
CS = 0.72
LEG_Y = 0.50
COMPRESS = 0.12
SPREAD = 0.055


def bbox(im):
    a = np.array(im)[..., 3] > 40
    ys, xs = np.where(a)
    return xs.min(), ys.min(), xs.max() + 1, ys.max() + 1


def ride_pose(art):
    a = np.array(art.convert('RGBA'))
    h, w = a.shape[:2]
    out = np.zeros_like(a)
    ys = np.arange(h)
    ny = ys / max(1, h)
    src = np.where(ny <= LEG_Y, ys, LEG_Y * h + (ys - LEG_Y * h) / (1.0 - COMPRESS))
    src = np.clip(src, 0, h - 1).astype(np.int32)
    for x in range(w):
        nx = x / max(1, w)
        outer = max(0.0, abs(nx - 0.5) - 0.08) * 2      # 只掰外侧
        shift = int(round((1 if nx >= 0.5 else -1) * SPREAD * w * outer))
        col = a[src, x]
        tx = int(np.clip(x + shift, 0, w - 1))
        m = col[:, 3] > out[:, tx, 3]
        out[m, tx] = col[m]
    return Image.fromarray(out, 'RGBA')


art = Image.open(os.path.join(A, 'stand_0.png')).convert('RGBA')
art = art.crop(bbox(art))
ch = int(VH * CS)
cw = int(art.width * ch / art.height)
stand = art.resize((cw, ch), Image.LANCZOS)
ride = ride_pose(stand)

cols = []
base = Image.new('RGBA', (VW, VH), (24, 28, 38, 255))
base.alpha_composite(stand, ((VW - cw) // 2, VH - ch))
cols.append(base)

for f, nm, mhw, fr in CFG:
    m = Image.open(os.path.join(A, f)).convert('RGBA')
    m = m.crop(bbox(m))
    mh = int(VH * mhw)
    mw = int(mh * m.width / m.height)
    if mw > VW * 0.98:
        mw = int(VW * 0.98)
        mh = int(mw * m.height / m.width)
    mi = m.resize((mw, mh), Image.LANCZOS)
    mx = (VW - mw) // 2
    my = VH - mh
    feet = int(VH - mh * fr)

    cv = Image.new('RGBA', (VW, VH), (24, 28, 38, 255))
    cv.alpha_composite(mi, (mx, my))
    rx = (VW - ride.width) // 2
    ry = feet - ride.height + int(ride.height * 0.08)
    cv.alpha_composite(ride, (rx, ry))
    band_bottom = min(mh, max(0, feet + int(mh * 0.03) - my))
    band = mi.crop((0, 0, mw, band_bottom))
    cv.alpha_composite(band, (mx, my))
    cols.append(cv)
    print(f'{nm}: 坐骑 {mw}x{mh} 鞍位 {fr} 人物 {ride.width}x{ride.height} 盖带 {band_bottom}px')

sheet = Image.new('RGBA', (VW * len(cols) + 10 * (len(cols) - 1), VH), (10, 12, 16, 255))
for i, c in enumerate(cols):
    sheet.alpha_composite(c, (i * (VW + 10), 0))
sheet.save(OUT)
print('预览 ->', OUT, sheet.size)
