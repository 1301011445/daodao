# -*- coding: utf-8 -*-
"""v129 最终测量 + 预览（素材已是新版：木马无底座、飞剑水平）"""
import numpy as np
from PIL import Image
import os

A = r'F:\Daodao\src\_apk\assets'
FILES = [('mount_cloud.png', '祥云'), ('mount_horse.png', '木马'), ('mount_sword.png', '飞剑'),
         ('mount_deer.png', '小鹿'), ('mount_crane.png', '纸鹤')]


def bbox(im):
    a = np.array(im)[..., 3] > 40
    ys, xs = np.where(a)
    return xs.min(), ys.min(), xs.max() + 1, ys.max() + 1


def back_line(im, band=0.22, cover=0.55):
    a = np.array(im)[..., 3] > 40
    h, w = a.shape
    x0, x1 = int(w * (0.5 - band / 2)), int(w * (0.5 + band / 2))
    cov = a[:, x0:x1].sum(axis=1) / max(1, (x1 - x0))
    for y in range(int(h * 0.55)):
        if cov[y] >= cover:
            return y / h
    return 0.5


VW, VH = 480, 640
art = Image.open(os.path.join(A, 'stand_0.png')).convert('RGBA')
art = art.crop(bbox(art))
cols, lines = [], {}
for f, nm in FILES:
    m = Image.open(os.path.join(A, f)).convert('RGBA')
    m = m.crop(bbox(m))
    bl = back_line(m)
    lines[nm] = round(1 - bl, 3)
    ch = int(VH * 0.74)
    cw = int(art.width * ch / art.height)
    cimg = art.resize((cw, ch), Image.LANCZOS)
    mw = min(int(cw * 1.30), int(VW * 0.96))
    mh = int(m.height * mw / m.width)
    mimg = m.resize((mw, mh), Image.LANCZOS)
    rise = int((1 - bl) * mh)
    cv = Image.new('RGBA', (VW, VH), (24, 28, 38, 255))
    cv.alpha_composite(mimg, ((VW - mw) // 2, VH - mh))
    cv.alpha_composite(cimg, ((VW - cw) // 2, VH - rise - ch))
    cols.append(cv)
    print(f'{nm}: {m.size} 背线从底 {1-bl:.3f} 坐骑 {mw}x{mh} 抬升 {rise}')

sheet = Image.new('RGBA', (VW * len(cols) + 10 * (len(cols) - 1), VH), (10, 12, 16, 255))
for i, c in enumerate(cols):
    sheet.alpha_composite(c, (i * (VW + 10), 0))
sheet.save(r'F:\Daodao\形象\坐骑\_配比预览3.png')
print('BACK_LINE', lines)
print('预览 ->', sheet.size)
