# -*- coding: utf-8 -*-
"""v129 最终配比（按视窗高度定，保证头不出画布）
MHW = 坐骑高 / 视窗高
FR  = 脚踩高度 / 坐骑高（从底算）
CS  = 骑上时人物缩放
"""
import os
import numpy as np
from PIL import Image

A = r'F:\Daodao\src\_apk\assets'
CFG = [
    ('mount_cloud.png', '祥云', 0.26, 0.88),
    ('mount_horse.png', '木马', 0.30, 0.72),
    ('mount_sword.png', '飞剑', 0.24, 0.52),
    ('mount_deer.png', '小鹿', 0.29, 0.80),
    ('mount_crane.png', '纸鹤', 0.33, 0.55),
]
CS = 0.74

VW, VH = 480, 640


def bbox(im):
    a = np.array(im)[..., 3] > 40
    ys, xs = np.where(a)
    return xs.min(), ys.min(), xs.max() + 1, ys.max() + 1


art0 = Image.open(os.path.join(A, 'stand_0.png')).convert('RGBA')
art0 = art0.crop(bbox(art0))

sheet = Image.new('RGBA', (VW * 6 + 50, VH), (10, 12, 16, 255))
ch = int(VH * CS)
cw = int(art0.width * ch / art0.height)
base = Image.new('RGBA', (VW, VH), (24, 28, 38, 255))
base.alpha_composite(art0.resize((cw, ch), Image.LANCZOS), ((VW - cw) // 2, VH - ch))
sheet.alpha_composite(base, (0, 0))

for i, (f, nm, mhw, fr) in enumerate(CFG):
    m = Image.open(os.path.join(A, f)).convert('RGBA')
    m = m.crop(bbox(m))
    mh = int(VH * mhw)
    mw = max(1, int(mh * m.width / m.height))
    if mw > VW * 0.98:
        mw = int(VW * 0.98)
        mh = int(mw * m.height / m.width)
    mimg = m.resize((mw, mh), Image.LANCZOS)
    rise = int(mh * fr)
    cv = Image.new('RGBA', (VW, VH), (24, 28, 38, 255))
    cv.alpha_composite(mimg, ((VW - mw) // 2, VH - mh))
    cv.alpha_composite(art0.resize((cw, ch), Image.LANCZOS), ((VW - cw) // 2, VH - rise - ch))
    sheet.alpha_composite(cv, ((i + 1) * (VW + 10), 0))
    print(f'{nm}: 坐骑 {mw}x{mh} (视窗高×{mhw}) 脚踩 {fr} 抬升 {rise} {VH-rise-ch >= 0 and "头留空间" or "头被切"}')

sheet.save(r'F:\Daodao\形象\坐骑\_配比预览5.png')
print('预览 ->', sheet.size)
