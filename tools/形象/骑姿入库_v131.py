# -*- coding: utf-8 -*-
"""v131 骑姿立绘入库：去白底 → 裁透明边 → 宽 720
ride_0 = 橘猫少年 / ride_8 = 银发剑客 / ride_10 = 古风少女（对应 ARTS 序号）
"""
import os
import subprocess
import numpy as np
from PIL import Image

SRC = r'F:\Daodao\形象\骑姿'
A = r'F:\Daodao\src\_apk\assets'
os.makedirs(SRC, exist_ok=True)
DL = [('xjuAwSUatD', '骑姿_少年_原.png'), ('37xGV680pc', '骑姿_剑客_原.png'), ('Ct4al5W7MW', '骑姿_少女_原.png')]
OUTS = ['ride_0.png', 'ride_8.png', 'ride_10.png']
for sid, name in DL:
    subprocess.run(['C:\\Windows\\System32\\curl.exe', '-sL', 'https://aka.doubaocdn.com/s/' + sid,
                    '-o', os.path.join(SRC, name)], check=False)


def white_off(im):
    a = np.array(im.convert('RGBA')).astype(np.int16)
    A_ = a[..., 3]
    rgb = a[..., :3]
    white = (rgb[..., 0] > 238) & (rgb[..., 1] > 238) & (rgb[..., 2] > 238)
    edge = np.zeros(A_.shape, bool)
    ew, eh = max(1, int(a.shape[1] * 0.05)), max(1, int(a.shape[0] * 0.05))
    edge[:, :ew] = True; edge[:, -ew:] = True; edge[:eh, :] = True; edge[-eh:, :] = True
    kill = (A_ > 0) & ((white & edge) | (white & (A_ < 205)))
    rgb[kill] = 0
    A_[kill] = 0
    A_[A_ < 12] = 0
    return Image.fromarray(np.dstack([np.clip(rgb, 0, 255), A_]).astype(np.uint8), 'RGBA')


def bbox(im):
    a = np.array(im)[..., 3] > 40
    ys, xs = np.where(a)
    return xs.min(), ys.min(), xs.max() + 1, ys.max() + 1


for (sid, name), out in zip(DL, OUTS):
    im = white_off(Image.open(os.path.join(SRC, name)))
    im = im.crop(bbox(im))
    w = 720
    im = im.resize((w, int(im.height * w / im.width)), Image.LANCZOS)
    im = white_off(im)
    a = np.array(im)
    hollow = a[..., 3] < 40
    a[..., :3][hollow] = 0
    im = Image.fromarray(a, 'RGBA')
    p = os.path.join(A, out)
    im.save(p)
    wc = int(((a[..., 3] < 40) & (a[..., 0] > 243) & (a[..., 1] > 243) & (a[..., 2] > 243)).sum())
    print(out, im.size, os.path.getsize(p), '透明白=', wc)
