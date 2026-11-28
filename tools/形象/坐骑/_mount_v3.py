# -*- coding: utf-8 -*-
import os, urllib.request, shutil
import numpy as np
from PIL import Image
from scipy import ndimage

SRC_URL = 'https://aka.doubaocdn.com/s/mri9NVH9CG'
RAW = r'F:\Daodao\tools\形象\坐骑\_raw\_unicorn_v3.png'
DST = r'F:\Daodao\src\_apk\assets\mount_unicorn.png'
if not os.path.exists(RAW) or os.path.getsize(RAW) < 1000:
    urllib.request.urlretrieve(SRC_URL, RAW)
im0 = Image.open(RAW).convert('RGBA')
a = np.asarray(im0).astype(np.uint16)
bright = a[:, :, :3].min(axis=2) >= 232
lab, n = ndimage.label(bright)
border = set(lab[0, :].tolist()) | set(lab[-1, :].tolist()) | set(lab[:, 0].tolist()) | set(lab[:, -1].tolist())
border.discard(0)
bg = np.isin(lab, list(border))
solid = ndimage.binary_erosion(~bg, iterations=1)
out = a.astype(np.uint8)
out[:, :, 3] = np.where(solid, 255, 0)
out[~solid, :3] = 0
imu = Image.fromarray(out, 'RGBA')

# 去白边
f = np.asarray(imu).astype(np.float32)
al = f[:, :, 3:4] / 255.0
rgb = f[:, :, :3]
soft = (f[:, :, 3:4] >= 50) & (f[:, :, 3:4] < 255)
back = 255.0 * (1.0 - al)
rgb = np.where(soft, np.clip((rgb - back) / np.maximum(al, 1e-3), 0, 255), rgb)
f[:, :, :3] = rgb
f[:, :, 3:4] = np.where(f[:, :, 3:4] < 50, 0, f[:, :, 3:4])
imu = Image.fromarray(np.clip(f, 0, 255).astype(np.uint8), 'RGBA')

bb = imu.getchannel('A').point(lambda v: 255 if v >= 8 else 0).getbbox()
imu = imu.crop(bb)
imu = imu.resize((int(imu.width * 600.0 / imu.height), 600), Image.LANCZOS)
bk = DST + '.bak_20261128'
if os.path.exists(DST) and not os.path.exists(bk):
    shutil.copy2(DST, bk)
imu.save(DST, optimize=True)
imu2 = Image.new('RGBA', imu.size, (64, 72, 86, 255))
imu2.alpha_composite(imu)
imu2.convert('RGB').save(r'F:\Daodao\temp_ride\_mount_dark.png')
print('mount %dx%d %dB' % (imu.width, imu.height, os.path.getsize(DST)))
