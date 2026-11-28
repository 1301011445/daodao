# -*- coding: utf-8 -*-
# 2026-11-28 | 手机端坐骑：银白独角兽定稿去底（渐变白底+地面投影），保最大主体、软边羽化
import os, shutil
import numpy as np
from PIL import Image
from scipy import ndimage

SRC = r'F:\Daodao\tools\形象\坐骑\_raw\_unicorn_v2.png'
DST = r'F:\Daodao\src\_apk\assets\mount_unicorn.png'

im = Image.open(SRC).convert('RGB')
a = np.asarray(im).astype(np.float32)
H, W = a.shape[:2]

# 1) 梯度图：白底与投影都是缓变，马身与轮廓是高反差
gx = ndimage.sobel(a, axis=1)
gy = ndimage.sobel(a, axis=0)
g = np.sqrt(gx ** 2 + gy ** 2).max(axis=2) / 8.0   # 归一化
smooth = g < 14.0

# 2) 平滑区里与画布边连通的算背景（投影也算背景，因为它没有硬边）
lab, n = ndimage.label(smooth)
border = set(lab[0, :].tolist()) | set(lab[-1, :].tolist()) | set(lab[:, 0].tolist()) | set(lab[:, -1].tolist())
border.discard(0)
bg = np.isin(lab, list(border))

# 3) 背景之外只剩马（鞍、鬃、独角都连在马身上），取最大连通块，别的小块（腿间亮缝）一律判背景
cand = ~bg
lab2, n2 = ndimage.label(cand)
sizes = ndimage.sum(cand, lab2, range(1, n2 + 1))
main = int(np.argmax(sizes)) + 1
print('cand comps', n2, 'main area', int(sizes[main - 1]), 'all', cand.size)
horse = ndimage.binary_fill_holes(lab2 == main)
horse = ndimage.binary_closing(horse, iterations=2)
# 蹄下那几条细影连着蹄子，靠腐蚀 3px 掐断，再取最大块膨胀回原轮廓
he = ndimage.binary_erosion(horse, iterations=3)
le, ne = ndimage.label(he)
se = ndimage.sum(he, le, range(1, ne + 1))
horse = ndimage.binary_dilation(le == (int(np.argmax(se)) + 1), iterations=3)
horse = ndimage.binary_fill_holes(horse)
horse = ndimage.binary_closing(horse, iterations=1)

# 4) 羽化 1px：内部实、边缘半透
al = ndimage.gaussian_filter(horse.astype(np.float32), 1.2)
al = np.clip((al - 0.35) / 0.45, 0, 1)
al[horse & (ndimage.gaussian_filter(horse.astype(np.float32), 0.6) > 0.9)] = 1.0

# 5) 反解白底混色，去掉白边
rgb = a.copy()
A3 = np.repeat(al[:, :, None], 3, axis=2)
back = 232.0 * (1.0 - A3)
soft = (al > 0.15) & (al < 0.99)
rgb = np.where(soft[:, :, None], np.clip((rgb - back) / np.maximum(A3, 1e-3), 0, 255), rgb)

out = np.dstack([rgb, al * 255.0]).clip(0, 255).astype(np.uint8)
imu = Image.fromarray(out, 'RGBA')

bb = imu.getchannel('A').point(lambda v: 255 if v >= 8 else 0).getbbox()
imu = imu.crop(bb)
imu = imu.resize((int(imu.width * 600.0 / imu.height), 600), Image.LANCZOS)
bk = DST + '.bak_20261128'
if os.path.exists(DST) and not os.path.exists(bk):
    shutil.copy2(DST, bk)
imu.save(DST, optimize=True)
print('mount_unicorn %dx%d %dB' % (imu.width, imu.height, os.path.getsize(DST)))
