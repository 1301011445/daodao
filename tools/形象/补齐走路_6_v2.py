# -*- coding: utf-8 -*-
"""6号蓝发少女八帧走路 v2：按裙摆下沿切腿，下半身整块左右错位（裙摆遮住接缝）。"""
import numpy as np, os
from PIL import Image

A = r"F:\Daodao\src\_apk\assets"
W, H = 192, 384
src = Image.open(os.path.join(A, "stand_6.png")).convert("RGBA")
if src.size != (W, H):
    src = src.resize((W, H), Image.LANCZOS)
a = np.array(src)
al = a[..., 3] > 60

widths = np.array([(np.where(al[y])[0].max() - np.where(al[y])[0].min() + 1) if al[y].any() else 0 for y in range(H)])
maxw = widths.max()
hem = None
for y in range(H - 1, 0, -1):
    if widths[y] > maxw * 0.5:
        hem = y
        break
print("裙摆下沿 y =", hem, "最大宽", maxw)
ymin = hem + 2

xs = np.where(al[ymin:].any(0))[0]
mid = (xs.min() + xs.max()) // 2
legL = np.zeros_like(al)
legR = np.zeros_like(al)
legL[ymin:, :mid] = al[ymin:, :mid]
legR[ymin:, mid:] = al[ymin:, mid:]

base = a.copy()
base[ymin:, :] = 0
bimg = Image.fromarray(base, "RGBA")

def leg_img(mask):
    d = a.copy()
    d[~mask, 3] = 0
    return Image.fromarray(d, "RGBA")

limg, rimg = leg_img(legL), leg_img(legR)

STRIDE = 16
frames = []
for i in range(8):
    ph = 2 * np.pi * i / 8
    dL = int(round(STRIDE * np.sin(ph)))
    dR = int(round(-STRIDE * np.sin(ph)))
    dY = int(round(2 * abs(np.cos(ph))))
    f = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    f.alpha_composite(bimg)
    f.alpha_composite(limg, (dL, -dY))
    f.alpha_composite(rimg, (dR, -dY))
    frames.append(f)

for i, f in enumerate(frames):
    f.save(os.path.join(A, "_walk6_%d.png" % (i + 1)))

out = Image.new("RGB", (W * 4, H * 2), (250, 250, 250))
for i, f in enumerate(frames):
    bg = Image.new("RGBA", (W, H), (250, 250, 250, 255))
    bg.alpha_composite(f)
    out.paste(bg.convert("RGB"), ((i % 4) * W, (i // 4) * H))
out.save(r"F:\Daodao\_diag_look\走路_6号_方案2.png")
print("done 裙摆下沿", hem)
