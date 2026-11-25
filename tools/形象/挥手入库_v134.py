# -*- coding: utf-8 -*-
"""v134 挥手帧入库：14 只形象各一张"抬右手招手"的动作立绘 → wave_<k>.png
口径：去白底 → 裁透明边 → 统一 480 宽 → 清内部透明白
"""
import os
import subprocess

import numpy as np
from PIL import Image

SRC = r'F:\Daodao\形象\挥手'
A = r'F:\Daodao\src\_apk\assets'
os.makedirs(SRC, exist_ok=True)

URLS = {
    0: 'XhNrsRcKkl', 1: 'ZwV1IXadEM', 2: 'IBufCvjBkW', 3: 'm4ZKud53KG', 4: 's3Mc8V3xsa',
    5: 'UPzLc8ZPwT', 6: '2Uzlf3NQYB', 7: 'CE49JQOwnm', 8: '7wWT6swaRP', 9: '3yxzz3uNZn',
    10: 'sHpNL52aIo', 11: 'Eb5VL4F3DM', 12: 'KTOytW7hp0', 13: 'TFfcY7X0ws',
}


def white_off(im):
    a = np.array(im.convert('RGBA')).astype(np.int16)
    al = a[..., 3]
    rgb = a[..., :3]
    w = (rgb[..., 0] > 238) & (rgb[..., 1] > 238) & (rgb[..., 2] > 238)
    edge = np.zeros(al.shape, bool)
    ew, eh = max(1, int(a.shape[1] * 0.05)), max(1, int(a.shape[0] * 0.05))
    edge[:, :ew] = True; edge[:, -ew:] = True; edge[:eh] = True; edge[-eh:] = True
    kill = (al > 0) & ((w & edge) | (w & (al < 205)))
    rgb[kill] = 0
    al[kill] = 0
    al[al < 12] = 0
    return Image.fromarray(np.dstack([np.clip(rgb, 0, 255), al]).astype(np.uint8), 'RGBA')


def bbox(im):
    a = np.array(im)[..., 3] > 40
    ys, xs = np.where(a)
    return xs.min(), ys.min(), xs.max() + 1, ys.max() + 1


tot = 0
for k, sid in URLS.items():
    p = os.path.join(SRC, '挥手_%d_原.png' % k)
    if not os.path.exists(p) or os.path.getsize(p) < 20000:
        subprocess.run(['C:\\Windows\\System32\\curl.exe', '-sL', 'https://aka.doubaocdn.com/s/' + sid, '-o', p],
                       check=False)
    im = white_off(Image.open(p))
    im = im.crop(bbox(im))
    im = im.resize((480, int(im.height * 480 / im.width)), Image.LANCZOS)
    im = white_off(im)
    a = np.array(im)
    hollow = a[..., 3] < 40
    a[..., :3][hollow] = 0
    im = Image.fromarray(a, 'RGBA')
    out = os.path.join(A, 'wave_%d.png' % k)
    im.save(out, optimize=True)
    wc = int(((a[..., 3] < 40) & (a[..., 0] > 243) & (a[..., 1] > 243) & (a[..., 2] > 243)).sum())
    tot += os.path.getsize(out)
    print('%2d wave_%d.png %dx%d %dB 透明白=%d' % (k, k, im.width, im.height, os.path.getsize(out), wc))
print('合计 %.2f MB' % (tot / 1048576))
