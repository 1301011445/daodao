# -*- coding: utf-8 -*-
"""坐骑素材加工（v127 扩到 5 只）：去白底 → 裁透明边 → 缩到宽 720 → 存进 assets
祥云 / 木马 / 飞剑 / 小鹿 / 纸鹤
判据：透明白像素 0、宽 720
"""
import os
import numpy as np
from PIL import Image

SRC = r'F:\Daodao\形象\坐骑'
DST = r'F:\Daodao\src\_apk\assets'
JOBS = [
    ('祥云_原.png', 'mount_cloud.png'),
    ('木马_原.png', 'mount_horse.png'),
    ('飞剑_原.png', 'mount_sword.png'),
    ('小鹿_原.png', 'mount_deer.png'),
    ('纸鹤_原.png', 'mount_crane.png'),
]
TARGET_W = 720


def strip_white(im):
    a = np.array(im.convert('RGBA')).astype(np.float32)
    alpha = a[..., 3]
    whiteish = (a[..., 0] > 243) & (a[..., 1] > 243) & (a[..., 2] > 243)
    edge_band = np.zeros_like(alpha, bool)
    ew, eh = max(1, int(a.shape[1] * 0.06)), max(1, int(a.shape[0] * 0.06))
    edge_band[:, :ew] = True
    edge_band[:, -ew:] = True
    edge_band[:eh, :] = True
    edge_band[-eh:, :] = True
    kill = whiteish & (alpha > 0) & (edge_band | (alpha < 200))
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
    box = (max(0, xs.min() - pad), max(0, ys.min() - pad),
           min(im.width, xs.max() + 1 + pad), min(im.height, ys.max() + 1 + pad))
    return im.crop(box)


ok = True
for src, name in JOBS:
    src_path = os.path.join(SRC, src)
    if not os.path.exists(src_path):
        print(f'{name}: 缺原图 {src}')
        ok = False
        continue
    im = strip_white(Image.open(src_path))
    im = trim(im)
    w = TARGET_W
    h = int(im.height * w / im.width)
    im = im.resize((w, h), Image.LANCZOS)
    im = strip_white(im)
    a = np.array(im)
    hollow = a[..., 3] < 40
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
