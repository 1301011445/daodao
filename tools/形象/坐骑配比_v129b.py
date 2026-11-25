# -*- coding: utf-8 -*-
"""坐骑素材二次整理（v129）：木马去底座、飞剑转平、量"背线"；出预览供人工判看
输出 assets 里的同名文件（覆盖），并保留 _bak\mounts_v128
"""
import os
import shutil
import numpy as np
from PIL import Image

A = r'F:\Daodao\src\_apk\assets'
BAK = r'F:\Daodao\_bak\mounts_v128'
os.makedirs(BAK, exist_ok=True)

FILES = ['mount_cloud.png', 'mount_horse.png', 'mount_sword.png', 'mount_deer.png', 'mount_crane.png']
for f in FILES:
    src = os.path.join(A, f)
    dst = os.path.join(BAK, f)
    if not os.path.exists(dst):
        shutil.copy2(src, dst)


def alpha(im):
    return np.array(im.convert('RGBA'))


def bbox(im):
    a = alpha(im)[..., 3] > 40
    ys, xs = np.where(a)
    return xs.min(), ys.min(), xs.max() + 1, ys.max() + 1


def strip_base(im, cover=0.82):
    """木马那种带木底座的：从底部往上扫，整行几乎全宽不透明的连续段落就是底座，切掉"""
    im = im.convert('RGBA')
    im = im.crop(bbox(im))
    a = alpha(im)[..., 3] > 40
    h, w = a.shape
    row_cov = a.sum(axis=1) / w
    y = h - 1
    base_top = h
    while y >= 0 and row_cov[y] >= cover:
        base_top = y
        y -= 1
    if base_top >= h - 1:          # 一行都不满足，说明没底座
        return im, 0
    cut = max(0, base_top - 1)
    if cut < h * 0.05:             # 切太少，多切一点保险
        cut = int(h * 0.12)
    return im.crop((0, 0, w, cut)), h - cut


def lay_flat(im):
    """飞剑这种斜放的：按主方向 PCA 角度转成水平"""
    im = im.crop(bbox(im))
    a = alpha(im)[..., 3]
    ys, xs = np.nonzero(a > 40)
    if len(xs) < 10:
        return im, 0.0
    xs = xs - xs.mean()
    ys = ys - ys.mean()
    cov = np.cov(np.vstack([xs, ys]))
    evals, evecs = np.linalg.eigh(cov)
    v = evecs[:, np.argmax(evals)]
    ang = np.degrees(np.arctan2(v[1], v[0]))
    rot = im.rotate(-ang, resample=Image.BICUBIC, expand=True)
    rot = rot.crop(bbox(rot))
    return rot, ang


def back_line(im, band=0.46, cover=0.72):
    """背线：中间 band 宽度里，从上往下第一行"被物体压满"的行（人踩这里）"""
    a = alpha(im)[..., 3] > 40
    h, w = a.shape
    x0, x1 = int(w * (0.5 - band / 2)), int(w * (0.5 + band / 2))
    cov = a[:, x0:x1].sum(axis=1) / max(1, (x1 - x0))
    for y in range(h):
        if cov[y] >= cover:
            return y / h
    return 0.5


print('== 处理 ==')
for f in FILES:
    p = os.path.join(A, f)
    im = Image.open(p).convert('RGBA')
    if f == 'mount_horse.png':
        im2, cut = strip_base(im)
        print(f'{f}: 去底座 切掉 {cut}px -> {im2.size}')
        im = im2
    elif f == 'mount_sword.png':
        im2, ang = lay_flat(im)
        print(f'{f}: 转平 {ang:.1f}° -> {im2.size}')
        im = im2
    im.save(p)
    bl = back_line(im, cover=0.62)
    print(f'{f}: 背线 = {bl:.3f}（占高，从顶算） 从底算 {1-bl:.3f}')

print('\n== 预览 ==')
VW, VH = 480, 640
ART = 'stand_0.png'
art = Image.open(os.path.join(A, ART)).convert('RGBA')
art = art.crop(bbox(art))

cols = []
for f in FILES:
    nm = {'mount_cloud.png': '祥云', 'mount_horse.png': '木马', 'mount_sword.png': '飞剑',
          'mount_deer.png': '小鹿', 'mount_crane.png': '纸鹤'}[f]
    m = Image.open(os.path.join(A, f)).convert('RGBA')
    m = m.crop(bbox(m))
    bl = back_line(m, cover=0.62)

    ch = int(VH * 0.74)
    cw = int(art.width * ch / art.height)
    cimg = art.resize((cw, ch), Image.LANCZOS)
    mw = int(cw * 1.28)                      # 坐骑宽 ≈ 人物宽 ×1.28，别比人还瘦
    mw = min(mw, int(VW * 0.96))
    mh = int(m.height * mw / m.width)
    mimg = m.resize((mw, mh), Image.LANCZOS)

    rise = int((1 - bl) * mh)                # 脚踩背线
    canvas = Image.new('RGBA', (VW, VH), (24, 28, 38, 255))
    canvas.alpha_composite(mimg, ((VW - mw) // 2, VH - mh))
    canvas.alpha_composite(cimg, ((VW - cw) // 2, VH - rise - ch))
    cols.append(canvas)
    print(f'{nm}: 坐骑 {mw}x{mh} 背线抬升 {rise}px 人物 {cw}x{ch}')

sheet = Image.new('RGBA', (VW * len(cols) + 10 * (len(cols) - 1), VH), (10, 12, 16, 255))
for i, c in enumerate(cols):
    sheet.alpha_composite(c, (i * (VW + 10), 0))
sheet.save(r'F:\Daodao\形象\坐骑\_配比预览2.png')
print('预览 -> 形象\\坐骑\\_配比预览2.png', sheet.size)
