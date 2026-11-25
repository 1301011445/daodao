# -*- coding: utf-8 -*-
"""v129 配比确认：按"坐骑高 = 人物高 × 比例"定尺寸（比按宽度定更接近真实比例）
MH  = 坐骑高 / 人物高
FR  = 脚踩的高度 / 坐骑高（从底算）
"""
import os
import numpy as np
from PIL import Image
import json

A = r'F:\Daodao\src\_apk\assets'
CFG = [
    ('mount_cloud.png', '祥云', 0.34, 0.90),
    ('mount_horse.png', '木马', 0.58, 0.78),
    ('mount_sword.png', '飞剑', 0.30, 0.55),
    ('mount_deer.png', '小鹿', 0.62, 0.86),
    ('mount_crane.png', '纸鹤', 0.52, 0.62),
]


def bbox(im):
    a = np.array(im)[..., 3] > 40
    ys, xs = np.where(a)
    return xs.min(), ys.min(), xs.max() + 1, ys.max() + 1


VW, VH = 480, 640
art0 = Image.open(os.path.join(A, 'stand_0.png')).convert('RGBA')
art0 = art0.crop(bbox(art0))
cols = []
for f, nm, mh_r, fr in CFG:
    m = Image.open(os.path.join(A, f)).convert('RGBA')
    m = m.crop(bbox(m))
    ch = int(VH * 0.72)
    cw = int(art0.width * ch / art0.height)
    cimg = art0.resize((cw, ch), Image.LANCZOS)
    mh = int(ch * mh_r)
    mw = max(1, int(mh * m.width / m.height))
    if mw > int(VW * 0.98):
        mw = int(VW * 0.98)
        mh = int(mw * m.height / m.width)
    mimg = m.resize((mw, mh), Image.LANCZOS)
    rise = int(mh * fr)
    cv = Image.new('RGBA', (VW, VH), (24, 28, 38, 255))
    cv.alpha_composite(mimg, ((VW - mw) // 2, VH - mh))
    cv.alpha_composite(cimg, ((VW - cw) // 2, VH - rise - ch))
    cols.append(cv)
    print(f'{nm}: 坐骑 {mw}x{mh} (=人物高×{mh_r}) 脚踩 {fr} 抬升 {rise}px')

sheet = Image.new('RGBA', (VW * 6 + 10 * 5, VH), (10, 12, 16, 255))
# 加一格"无坐骑"做对照
base = Image.new('RGBA', (VW, VH), (24, 28, 38, 255))
ch = int(VH * 0.72)
cw = int(art0.width * ch / art0.height)
base.alpha_composite(art0.resize((cw, ch), Image.LANCZOS), ((VW - cw) // 2, VH - ch))
sheet.alpha_composite(base, (0, 0))
for i, c in enumerate(cols):
    sheet.alpha_composite(c, ((i + 1) * (VW + 10), 0))
sheet.save(r'F:\Daodao\形象\坐骑\_配比预览4.png')
print('预览 ->', sheet.size)
