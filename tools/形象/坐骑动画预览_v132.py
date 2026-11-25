# -*- coding: utf-8 -*-
"""v132 动画预览：按 Java 里同一套公式，把坐骑"动起来"的 5 个瞬间摆出来
坐骑公式（秒 t）：
 祥云 dx=sin(0.85t)*0.030w, dy=sin(1.25t)*0.012h
 木马 dy=sin(6.2t)*0.008h, rot=sin(6.2t)*1.6°
 飞剑 dy=sin(2.3t)*0.022h, rot=sin(2.3t)*3.2°
 小鹿 dy=sin(4.0t)*0.011h, rot=sin(4.0t)*1.3°
 纸鹤 dy=sin(2.8t)*0.020h, 横向 1+0.035sin / 纵向 1-0.035sin
"""
import math
import os
from PIL import Image

A = r'F:\Daodao\src\_apk\assets'
OUT = r'F:\Daodao\形象\坐骑\_坐骑动画预览.png'
CW, CH = 240, 340
MHW = [0.32, 0.52, 0.34, 0.50, 0.46]
FR = [0.88, 0.64, 0.62, 0.62, 0.44]
FILES = ['mount_cloud.png', 'mount_horse.png', 'mount_sword.png', 'mount_deer.png', 'mount_crane.png']
NAMES = ['祥云', '木马', '飞剑', '小鹿', '纸鹤']


def bbox(im):
    import numpy as np
    a = np.array(im)[..., 3] > 40
    ys, xs = np.where(a)
    return xs.min(), ys.min(), xs.max() + 1, ys.max() + 1


def motion(mi, t, w, h):
    mdx = mdy = rot = 0.0
    sc = 1.0
    if mi == 0:
        mdx = math.sin(t * 0.85) * 0.030 * w
        mdy = math.sin(t * 1.25) * 0.012 * h
    elif mi == 1:
        mdy = math.sin(t * 6.2) * 0.008 * h
        rot = math.sin(t * 6.2) * 1.6
    elif mi == 2:
        mdy = math.sin(t * 2.3) * 0.022 * h
        rot = math.sin(t * 2.3) * 3.2
    elif mi == 3:
        mdy = math.sin(t * 4.0) * 0.011 * h
        rot = math.sin(t * 4.0) * 1.3
    else:
        mdy = math.sin(t * 2.8) * 0.020 * h
        sc = 1.0 + 0.035 * math.sin(t * 2.8)
    return mdx, mdy, rot, sc


TS = [0.0, 0.16, 0.32, 0.48, 0.64]
ride = Image.open(os.path.join(A, 'ride_0.png')).convert('RGBA')
row_y = 0
sheet = Image.new('RGBA', (CW * len(TS) + 6 * (len(TS) - 1), (CH + 6) * len(FILES) - 6), (12, 14, 20, 255))
for mi in range(5):
    m = Image.open(os.path.join(A, FILES[mi])).convert('RGBA')
    m = m.crop(bbox(m))
    mh = int(CH * MHW[mi])
    mw = int(mh * m.width / m.height)
    base_m = m.resize((mw, mh), Image.LANCZOS)
    rch = int(CH * 0.62)
    rcw = int(ride.width * rch / ride.height)
    ri = ride.resize((rcw, rch), Image.LANCZOS)
    for k, t in enumerate(TS):
        cv = Image.new('RGBA', (CW, CH), (24, 28, 40, 255))
        mdx, mdy, rot, sc = motion(mi, t, CW, CH)
        bw, bh = int(mw * sc), int(mh * (2 - sc))
        mi2 = base_m.resize((max(1, bw), max(1, bh), ), Image.LANCZOS)
        img = Image.new('RGBA', (CW, CH), (0, 0, 0, 0))
        img.alpha_composite(mi2, (int(CW * 0.5 + mdx - bw * 0.5), int(CH + mdy - bh)))
        img = img.rotate(rot, resample=Image.BICUBIC, center=(CW * 0.5 + mdx, CH - mh * FR[mi]))
        saddle = CH - mh * FR[mi]
        img.alpha_composite(ri, (int(CW * 0.5 + mdx - rcw * 0.5), int(saddle - rch * 0.606 + mdy)))
        cv.alpha_composite(img)
        sheet.alpha_composite(cv, (k * (CW + 6), mi * (CH + 6)))
sheet.save(OUT)
print('动画预览 ->', OUT, sheet.size, '每行 %s 的 %d 个瞬间' % ('/'.join(NAMES), len(TS)))
