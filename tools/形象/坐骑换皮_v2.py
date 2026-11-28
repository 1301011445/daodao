# -*- coding: utf-8 -*-
# 程序版本：v0.2 | 2026-11-28 | 坐骑升级：银白独角兽（高大上）重绘 ridef，抠白底+去白边+统一裁切入库
import os, sys, urllib.request
import numpy as np
from PIL import Image

OUT = r'F:\Daodao\src\桌面分身\_bundle'
RAW = r'F:\Daodao\tools\形象\坐骑\_raw\v2'
os.makedirs(RAW, exist_ok=True)

URLS = {
    0:  'https://aka.doubaocdn.com/s/z5CzNVIfGu',
    1:  'https://aka.doubaocdn.com/s/KPkG2VHSQ9',
    2:  'https://aka.doubaocdn.com/s/2VhROQlJPm',
    3:  'https://aka.doubaocdn.com/s/YW0uJAjZ7C',
    4:  'https://aka.doubaocdn.com/s/GcTWx0mKWt',
    5:  'https://aka.doubaocdn.com/s/W6WxCMh93u',
    6:  'https://aka.doubaocdn.com/s/rn4URmuh6E',
    7:  'https://aka.doubaocdn.com/s/QLAI3VYvTU',
    8:  'https://aka.doubaocdn.com/s/v56FAUv2UG',
    9:  'https://aka.doubaocdn.com/s/nJ8pQbRaz7',
    10: 'https://aka.doubaocdn.com/s/HA2ddNxdHe',
    11: 'https://aka.doubaocdn.com/s/UUMq3cgvcq',
    12: 'https://aka.doubaocdn.com/s/LQKxJHVIlF',
    13: 'https://aka.doubaocdn.com/s/ACtK9xUs6n',
}


def download():
    for sp, u in URLS.items():
        p = os.path.join(RAW, 'ridef_%d_raw2.png' % sp)
        if os.path.exists(p) and os.path.getsize(p) > 1000:
            continue
        urllib.request.urlretrieve(u, p)
        print('dl', sp, os.path.getsize(p))


def knock_white(im, tol=232):
    from scipy import ndimage
    im = im.convert('RGBA')
    a = np.asarray(im).astype(np.uint16)
    bright = a[:, :, :3].min(axis=2) >= tol
    lab, n = ndimage.label(bright)
    border = set(lab[0, :].tolist()) | set(lab[-1, :].tolist()) | set(lab[:, 0].tolist()) | set(lab[:, -1].tolist())
    border.discard(0)
    bg = np.isin(lab, list(border))
    h, w = bright.shape
    for i in range(1, n + 1):
        if i in border:
            continue
        ys, xs = np.where(lab == i)
        if ys.size < 3000:
            continue
        v = a[:, :, :3][ys, xs].min(axis=1)
        if ys.mean() > h * 0.72 and np.percentile(v, 10) >= 245:
            bg |= (lab == i)
    solid = ~bg
    solid = ndimage.binary_erosion(solid, iterations=1)
    out = a.astype(np.uint8)
    out[:, :, 3] = np.where(solid, 255, 0)
    out[~solid, :3] = 0
    return Image.fromarray(out, 'RGBA')


def defringe(im):
    a = np.asarray(im).astype(np.float32)
    al = a[:, :, 3:4] / 255.0
    rgb = a[:, :, :3]
    soft = (a[:, :, 3:4] >= 50) & (a[:, :, 3:4] < 255)
    back = 255.0 * (1.0 - al)
    inv = np.where(soft, np.clip((rgb - back) / np.maximum(al, 1e-3), 0, 255), rgb)
    a[:, :, :3] = inv
    a[:, :, 3:4] = np.where(a[:, :, 3:4] < 50, 0, a[:, :, 3:4])
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), 'RGBA')


def fit(im, target_h=820, pad=3):
    bb = im.getchannel('A').point(lambda v: 255 if v >= 8 else 0).getbbox()
    im = im.crop(bb)
    k = target_h / float(im.height)
    im = im.resize((max(2, int(im.width * k)), target_h), Image.LANCZOS)
    canvas = Image.new('RGBA', (im.width + pad * 2, im.height + 1), (0, 0, 0, 0))
    canvas.alpha_composite(im, (pad, 0))
    return canvas


def main():
    download()
    for sp in sorted(URLS):
        src = os.path.join(RAW, 'ridef_%d_raw2.png' % sp)
        im = Image.open(src)
        im = knock_white(im)
        im = defringe(im)
        im = fit(im)
        dst = os.path.join(OUT, 'ridef_%d.png' % sp)
        im.save(dst, optimize=True)
        print('sp%-2d %dx%d %d' % (sp, im.width, im.height, os.path.getsize(dst)))


if __name__ == '__main__':
    main()
