# -*- coding: utf-8 -*-
"""坐骑素材整理 v129（第三次修正）：先还原备份再处理
· 木马去底座：先跳过底部空白行，再往上扫满宽行
· 飞剑转平：PCA 角度归一到 [-90,90]，不要转成竖的
· 背线：只用中间 20% 窄带、覆盖 0.55，取"身子压满"的第一行（避开耳朵与翅膀）
"""
import os
import shutil
import numpy as np
from PIL import Image

A = r'F:\Daodao\src\_apk\assets'
BAK = r'F:\Daodao\_bak\mounts_v128'
FILES = ['mount_cloud.png', 'mount_horse.png', 'mount_sword.png', 'mount_deer.png', 'mount_crane.png']
NAMES = {'mount_cloud.png': '祥云', 'mount_horse.png': '木马', 'mount_sword.png': '飞剑',
         'mount_deer.png': '小鹿', 'mount_crane.png': '纸鹤'}

for f in FILES:
    shutil.copy2(os.path.join(BAK, f), os.path.join(A, f))


def alpha(im):
    return np.array(im.convert('RGBA'))[..., 3] > 40


def bbox(im):
    a = alpha(im)
    ys, xs = np.where(a)
    return xs.min(), ys.min(), xs.max() + 1, ys.max() + 1


def strip_base(im, cover=0.88):
    im = im.convert('RGBA')
    im = im.crop(bbox(im))
    a = alpha(im)
    h, w = a.shape
    cov = a.sum(axis=1) / w
    rows = [y for y in range(h) if cov[y] > 0.02]
    if not rows:
        return im, 0
    ybot = rows[-1]
    run = 0
    y = ybot
    while y >= 0 and cov[y] >= cover:
        run += 1
        y -= 1
    if run < max(6, int(h * 0.06)):
        return im, 0
    cut = y + 1
    return im.crop((0, 0, w, cut)), h - cut


def lay_flat(im):
    im = im.crop(bbox(im))
    a = alpha(im)
    ys, xs = np.nonzero(a)
    xs = xs.astype(float) - xs.mean()
    ys = ys.astype(float) - ys.mean()
    evals, evecs = np.linalg.eigh(np.cov(np.vstack([xs, ys])))
    v = evecs[:, np.argmax(evals)]
    ang = float(np.degrees(np.arctan2(v[1], v[0])))
    ang = ((ang + 90) % 180) - 90          # 归一：保证是"横着放"
    rot = im.rotate(-ang, resample=Image.BICUBIC, expand=True)
    return rot.crop(bbox(rot)), ang


def back_line(im, band=0.20, cover=0.55):
    a = alpha(im)
    h, w = a.shape
    x0, x1 = int(w * (0.5 - band / 2)), int(w * (0.5 + band / 2))
    cov = a[:, x0:x1].sum(axis=1) / max(1, (x1 - x0))
    for y in range(h):
        if cov[y] >= cover:
            return y / h
    return 0.5


print('== 处理 ==')
bl_map = {}
for f in FILES:
    p = os.path.join(A, f)
    im = Image.open(p).convert('RGBA')
    if f == 'mount_horse.png':
        im, cut = strip_base(im)
        print(f'{NAMES[f]}: 去底座切掉 {cut}px -> {im.size}')
    elif f == 'mount_sword.png':
        im, ang = lay_flat(im)
        print(f'{NAMES[f]}: 转平 {ang:.1f}° -> {im.size}')
    im.save(p)
    bl = back_line(im)
    bl_map[f] = bl
    print(f'{NAMES[f]}: 背线(从顶) {bl:.3f} / 从底 {1-bl:.3f}')

print('\n== 预览 ==')
VW, VH = 480, 640
art = Image.open(os.path.join(A, 'stand_0.png')).convert('RGBA')
art = art.crop(bbox(art))
cols = []
for f in FILES:
    m = Image.open(os.path.join(A, f)).convert('RGBA')
    m = m.crop(bbox(m))
    ch = int(VH * 0.74)
    cw = int(art.width * ch / art.height)
    cimg = art.resize((cw, ch), Image.LANCZOS)
    mw = min(int(cw * 1.28), int(VW * 0.96))
    mh = int(m.height * mw / m.width)
    mimg = m.resize((mw, mh), Image.LANCZOS)
    rise = int((1 - bl_map[f]) * mh)
    canvas = Image.new('RGBA', (VW, VH), (24, 28, 38, 255))
    canvas.alpha_composite(mimg, ((VW - mw) // 2, VH - mh))
    canvas.alpha_composite(cimg, ((VW - cw) // 2, VH - rise - ch))
    cols.append(canvas)
    print(f'{NAMES[f]}: 坐骑 {mw}x{mh} 抬升 {rise} 人物 {cw}x{ch}')

sheet = Image.new('RGBA', (VW * len(cols) + 10 * (len(cols) - 1), VH), (10, 12, 16, 255))
for i, c in enumerate(cols):
    sheet.alpha_composite(c, (i * (VW + 10), 0))
sheet.save(r'F:\Daodao\形象\坐骑\_配比预览2.png')
print('预览 ->', sheet.size)
