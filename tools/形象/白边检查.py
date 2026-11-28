# -*- coding: utf-8 -*-
# 程序版本：v0.1 | 2026-11-28 | 量素材白边：轮廓一圈（alpha>=200 且 4 邻域有透明）里 RGB 近白的像素占比
"""量素材白边：边缘（alpha>=200 且 4 邻域有透明）里 RGB 近白的像素占比"""
import os, sys, glob
import numpy as np
from PIL import Image

BUN = r'F:\Daodao\src\桌面分身\_bundle'


def edge_white(a):
    al = a[:, :, 3]
    solid = al >= 200
    # 与透明相邻的实心像素 = 轮廓一圈
    t = np.zeros_like(solid)
    t[1:, :] |= solid[:-1, :] & (al[1:, :] < 200)
    t[:-1, :] |= solid[1:, :] & (al[:-1, :] < 200)
    t[:, 1:] |= solid[:, :-1] & (al[:, 1:] < 200)
    t[:, :-1] |= solid[:, 1:] & (al[:, :-1] < 200)
    if t.sum() == 0:
        return 0.0, 0
    rgb = a[:, :, :3]
    whiteish = (rgb.min(axis=2) >= 225) & t
    return float(whiteish.sum()) / float(t.sum()), int(t.sum())


if __name__ == '__main__':
    files = sys.argv[1:] or sorted(glob.glob(os.path.join(BUN, 'face_*.png')))[:6]
    for p in files:
        a = np.asarray(Image.open(p).convert('RGBA'))
        r, n = edge_white(a)
        print('%-28s 轮廓圈=%5d 近白占=%5.1f%%' % (os.path.basename(p), n, 100 * r))
