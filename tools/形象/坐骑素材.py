# -*- coding: utf-8 -*-
"""坐骑素材加工：去白底 → 裁透明边 → 缩到宽 720 → 存成 assets\mount_cloud.png / mount_horse.png
判据：透明白像素 0、透明边已裁干净（四边留 2px）、宽 720
"""
import os
import numpy as np
from PIL import Image

SRC = r'F:\Daodao\形象\坐骑'
DST = r'F:\Daodao\src\_apk\assets'
JOBS = [('祥云_原.png', 'mount_cloud.png'), ('木马_原.png', 'mount_horse.png')]
TARGET_W = 720


def strip_white(im):
    a = np.array(im.convert('RGBA')).astype(np.float32)
    alpha = a[..., 3]
    solid = alpha > 40
    whiteish = (a[..., 0] > 243) & (a[..., 1] > 243) & (a[..., 2] > 243)
    near = whiteish & (alpha > 0)
    # 边缘抗锯齿近白也一起清（只清贴着透明区或整体近白且在边缘 6% 以内）
    edge_band = np.zeros_like(alpha, bool)
    edge_band[:, :int(a.shape[1] * 0.06)] = True
    edge_band[:, -int(a.shape[1] * 0.06):] = True
    edge_band[:int(a.shape[0] * 0.06), :] = True
    edge_band[-int(a.shape[0] * 0.06):, :] = True
    kill = near & (edge_band | (alpha < 200))
    a[..., 0][kill] = 0
    a[..., 1][kill] = 0
    a[..., 2][kill] = 0
    a[..., 3][kill] = 0
    a[..., 3] = np.where(a[..., 3] < 8, 0, a[..., 3])
    return Image.fromarray(a.astype(np.uint8), 'RGBA')


def white_count(im):
    a = np.array(im)
    return int(((a[..., 3] < 40) & (a[..., 0] > 243) & (a[..., 1] > 243) & (a[..., 2] > 243)).sum())


def trim(im, pad=2):
    a = np.array(im)[..., 3]
    ys, xs = np.where(a > 8)
    x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
    box = (max(0, x0 - pad), max(0, y0 - pad), min(im.width, x1 + 1 + pad), min(im.height, y1 + 1 + pad))
    return im.crop(box)


ok = True
for src, name in JOBS:
    im = Image.open(os.path.join(SRC, src))
    im = strip_white(im)
    im = trim(im)
    w = TARGET_W
    h = int(im.height * w / im.width)
    im = im.resize((w, h), Image.LANCZOS)
    im = strip_white(im)                     # 缩放会把边缘近白又插值回来，再清一遍
    a = np.array(im)
    hollow = a[..., 3] < 40                   # 全透明处 RGB 归零，免得缩放/抗锯齿把白带进轮廓
    a[..., 0][hollow] = 0
    a[..., 1][hollow] = 0
    a[..., 2][hollow] = 0
    im = Image.fromarray(a, 'RGBA')
    out = os.path.join(DST, name)
    im.save(out)
    wc = white_count(im)
    print(f'{name}: {im.size} 字节={os.path.getsize(out)} 透明白像素={wc} {"PASS" if wc == 0 else "FAIL"}')
    ok = ok and wc == 0
print('SUMMARY', 'PASS' if ok else 'FAIL')
raise SystemExit(0 if ok else 1)
