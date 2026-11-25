# -*- coding: utf-8 -*-
"""v131 骑姿对位：量"坐骨线"（两腿之间的裂口），让臀部坐在鞍位，出预览
坐骨线 = 中轴线（中 6% 宽）第一次出现"空洞"的那一行（档口）
"""
import os
import numpy as np
from PIL import Image

A = r'F:\Daodao\src\_apk\assets'
OUT = r'F:\Daodao\形象\坐骑\_骑姿预览2.png'
RIDE = 'ride_0.png'
CFG = [
    ('mount_cloud.png', '祥云', 0.26, 0.86),
    ('mount_horse.png', '木马', 0.40, 0.62),
    ('mount_sword.png', '飞剑', 0.24, 0.46),
    ('mount_deer.png', '小鹿', 0.34, 0.58),
    ('mount_crane.png', '纸鹤', 0.40, 0.40),
]
VW, VH = 480, 640


def bbox(im):
    a = np.array(im)[..., 3] > 40
    ys, xs = np.where(a)
    return xs.min(), ys.min(), xs.max() + 1, ys.max() + 1


def seat_line(im):
    a = np.array(im)[..., 3] > 40
    h, w = a.shape
    x0, x1 = int(w * 0.47), int(w * 0.53)
    band = a[:, x0:x1]
    filled = band.sum(axis=1) > 0
    started = False
    for y in range(h):
        if filled[y]:
            started = True
        elif started and y > h * 0.32:
            return y / h          # 档口：从这里往下是两条腿
    return 0.6


ride = Image.open(os.path.join(A, RIDE)).convert('RGBA')
ride = ride.crop(bbox(ride))
sr = seat_line(ride)
print('坐骨线 %.3f（从顶算，即臀部 %d%%）' % (sr, int(sr * 100)))

cols = []
for f, nm, mhw, fr in CFG:
    m = Image.open(os.path.join(A, f)).convert('RGBA')
    m = m.crop(bbox(m))
    mh = int(VH * mhw)
    mw = int(mh * m.width / m.height)
    if mw > VW * 0.98:
        mw = int(VW * 0.98)
        mh = int(mw * m.height / m.width)
    mi = m.resize((mw, mh), Image.LANCZOS)
    mx, my = (VW - mw) // 2, VH - mh
    saddle_y = VH - int(mh * fr)          # 鞍面在画面上的 y

    # 人物：坐高按视窗的 0.78，臀部落在鞍面
    rch = int(VH * 0.78)
    rcw = int(ride.width * rch / ride.height)
    ri = ride.resize((rcw, rch), Image.LANCZOS)
    ry = saddle_y - int(rch * sr)          # 让坐骨线正好压在鞍面

    cv = Image.new('RGBA', (VW, VH), (24, 28, 38, 255))
    cv.alpha_composite(mi, (mx, my))
    cv.alpha_composite(ri, ((VW - rcw) // 2, ry))
    cols.append(cv)
    print(f'{nm}: 坐骑 {mw}x{mh} 鞍面 y={saddle_y} 人 {rcw}x{rch} 落位 y={ry}')

sheet = Image.new('RGBA', (VW * len(cols) + 10 * (len(cols) - 1), VH), (10, 12, 16, 255))
for i, c in enumerate(cols):
    sheet.alpha_composite(c, (i * (VW + 10), 0))
sheet.save(OUT)
print('预览 ->', OUT, sheet.size)
