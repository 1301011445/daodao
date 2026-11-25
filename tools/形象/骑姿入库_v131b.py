# -*- coding: utf-8 -*-
"""v131b 全部 14 个形象的骑姿立绘入库 + 量每张的坐骨线
输出 ride_{k}.png（k=0..13），并打印 Java 用的 RIDE_SEAT 表
"""
import os
import subprocess
import numpy as np
from PIL import Image

SRC = r'F:\Daodao\形象\骑姿'
A = r'F:\Daodao\src\_apk\assets'
os.makedirs(SRC, exist_ok=True)

JOBS = [
    (0, 'xjuAwSUatD', '橘猫少年'), (1, 'lwcdMehxh9', '白兔少女'), (2, 'uNxt2hWVlW', '狐狸少女'),
    (3, 'bBqA8Rbbm1', '熊猫少女'), (4, 'Yk5XRxjXxU', '恐龙少女'), (5, 'LtstLRf3bU', '企鹅少年'),
    (6, 'BK0azrVqJJ', '蓝发少女'), (7, 'PtBdJEapVq', '黑发少年'), (8, '37xGV680pc', '银发剑客'),
    (9, '08ZTxZQ37C', '魔法师少女'), (10, 'Ct4al5W7MW', '古风少女'), (11, 'xz3pGSx9SZ', '机械少年'),
    (12, '1kaUVh77bT', '白衫少年'), (13, '1nVfgNH50c', '青衫少女'),
]


def white_off(im):
    a = np.array(im.convert('RGBA')).astype(np.int16)
    al = a[..., 3]
    rgb = a[..., :3]
    white = (rgb[..., 0] > 238) & (rgb[..., 1] > 238) & (rgb[..., 2] > 238)
    edge = np.zeros(al.shape, bool)
    ew, eh = max(1, int(a.shape[1] * 0.05)), max(1, int(a.shape[0] * 0.05))
    edge[:, :ew] = True; edge[:, -ew:] = True; edge[:eh, :] = True; edge[-eh:, :] = True
    kill = (al > 0) & ((white & edge) | (white & (al < 205)))
    rgb[kill] = 0
    al[kill] = 0
    al[al < 12] = 0
    return Image.fromarray(np.dstack([np.clip(rgb, 0, 255), al]).astype(np.uint8), 'RGBA')


def bbox(im):
    a = np.array(im)[..., 3] > 40
    ys, xs = np.where(a)
    return xs.min(), ys.min(), xs.max() + 1, ys.max() + 1


def seat_line(im):
    a = np.array(im)[..., 3] > 40
    h, w = a.shape
    band = a[:, int(w * 0.46):int(w * 0.54)]
    filled = band.sum(axis=1) > 0
    started = False
    for y in range(h):
        if filled[y]:
            started = True
        elif started and y > h * 0.30:
            return round(y / h, 3)
    return 0.60


seats = {}
for k, sid, nm in JOBS:
    p = os.path.join(SRC, '骑姿_%d_原.png' % k)
    if not os.path.exists(p) or os.path.getsize(p) < 20000:
        subprocess.run(['C:\\Windows\\System32\\curl.exe', '-sL', 'https://aka.doubaocdn.com/s/' + sid, '-o', p],
                       check=False)
    im = white_off(Image.open(p))
    im = im.crop(bbox(im))
    im = im.resize((720, int(im.height * 720 / im.width)), Image.LANCZOS)
    im = white_off(im)
    a = np.array(im)
    hollow = a[..., 3] < 40
    a[..., :3][hollow] = 0
    im = Image.fromarray(a, 'RGBA')
    out = os.path.join(A, 'ride_%d.png' % k)
    im.save(out)
    wc = int(((a[..., 3] < 40) & (a[..., 0] > 243) & (a[..., 1] > 243) & (a[..., 2] > 243)).sum())
    s = seat_line(im)
    seats[k] = s
    print('%2d %-6s %s %dx%d %dB 透明白=%d 坐骨线=%.3f' % (k, nm, os.path.basename(out), im.width, im.height,
                                                        os.path.getsize(out), wc, s))

print('RIDE_SEAT = {%s};' % ', '.join('%.3ff' % seats[k] for k in range(14)))
