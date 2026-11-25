# -*- coding: utf-8 -*-
"""v129 坐骑素材替换：木马（无底座）、飞剑（水平）
处理：去白底 → 清阴影（低 alpha 且灰白）→ 裁透明边 → 缩到宽 720
"""
import os
import subprocess
import numpy as np
from PIL import Image

SRC = r'F:\Daodao\形象\坐骑'
A = r'F:\Daodao\src\_apk\assets'
DLS = [('1M9ZmSWBUz', '木马_原.png'), ('xAgYtJV2y3', '飞剑_原.png')]
for sid, name in DLS:
    subprocess.run(['C:\\Windows\\System32\\curl.exe', '-sL',
                    'https://aka.doubaocdn.com/s/' + sid, '-o', os.path.join(SRC, name)], check=False)


def clean(im):
    a = np.array(im.convert('RGBA')).astype(np.int16)
    A_ = a[..., 3]
    rgb = a[..., :3]
    white = (rgb[..., 0] > 238) & (rgb[..., 1] > 238) & (rgb[..., 2] > 238)
    gray = (np.abs(rgb[..., 0] - rgb[..., 1]) < 12) & (np.abs(rgb[..., 1] - rgb[..., 2]) < 12) & (rgb[..., 0] > 120)
    # 边缘一圈的白/灰（纸白或摄影台阴影）一律清掉
    edge = np.zeros(A_.shape, bool)
    ew, eh = max(1, int(a.shape[1] * 0.05)), max(1, int(a.shape[0] * 0.05))
    edge[:, :ew] = True; edge[:, -ew:] = True; edge[:eh, :] = True; edge[-eh:, :] = True
    kill = (A_ > 0) & ((white & edge) | (white & (A_ < 210)) | (gray & (A_ < 150)))
    rgb[kill] = 0
    A_[kill] = 0
    A_[A_ < 10] = 0
    return Image.fromarray(np.dstack([np.clip(rgb, 0, 255), A_]).astype(np.uint8), 'RGBA')


def bbox(im):
    a = np.array(im)[..., 3] > 40
    ys, xs = np.where(a)
    return xs.min(), ys.min(), xs.max() + 1, ys.max() + 1


for _, name in DLS:
    p = os.path.join(SRC, name)
    im = clean(Image.open(p))
    im = im.crop(bbox(im))
    w = 720
    im = im.resize((w, int(im.height * w / im.width)), Image.LANCZOS)
    im = clean(im)
    a = np.array(im)
    hollow = a[..., 3] < 40
    a[..., :3][hollow] = 0
    im = Image.fromarray(a, 'RGBA')
    out = os.path.join(A, 'mount_horse.png' if '木马' in name else 'mount_sword.png')
    im.save(out)
    wc = int(((a[..., 3] < 40) & (a[..., 0] > 243) & (a[..., 1] > 243) & (a[..., 2] > 243)).sum())
    print(name, '->', out.split('\\')[-1], im.size, os.path.getsize(out), '透明白=', wc)
