# -*- coding: utf-8 -*-
"""白边验收：把素材贴到深色桌面底上，数「半透明且发白」的像素 —— 那就是肉眼看到的白边。"""
import numpy as np
from PIL import Image

A = r"F:\Daodao\src\_apk\assets"
BG = (15, 21, 34)


def matte(im):
    a = np.array(im.convert("RGBA")).astype(np.int32)
    h, w = a.shape[:2]
    bg = np.zeros((h, w), bool)
    stack = [(0, x) for x in range(w)] + [(h - 1, x) for x in range(w)]
    while stack:
        y, x = stack.pop()
        if bg[y, x]:
            continue
        p = a[y, x]
        if not (p[3] >= 60 and p[0] >= 225 and p[1] >= 225 and p[2] >= 225):
            continue
        bg[y, x] = True
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx < w and not bg[ny, nx]:
                stack.append((ny, nx))
    a[..., 3] = np.where(bg, 0, a[..., 3])
    al0 = a[..., 3]
    lum0 = np.minimum(np.minimum(a[..., 0], a[..., 1]), a[..., 2])
    semi = (al0 > 6) & (al0 < 250) & (lum0 >= 215)
    k = np.minimum(1.0, (255.0 - lum0) / 40.0)
    a[..., 3] = np.where(semi, (al0 * k).astype(np.int32), al0)
    return Image.fromarray(a.astype("uint8"), "RGBA")


def pale_over_dark(im):
    a = np.array(im).astype(float)
    al = a[..., 3:4] / 255.0
    comp = a[..., :3] * al + np.array(BG, float) * (1 - al)
    semi = (a[..., 3] > 5) & (a[..., 3] < 250)
    pale = (comp[..., 0] > 150) & (comp[..., 1] > 150) & (comp[..., 2] > 150)
    return int((semi & pale).sum()), comp.astype("uint8")


rows = []
for name, box in [("stand_6.png", None), ("walk8_11.png", (0, 0, 192, 384)),
                  ("walk8.png", (0, 0, 192, 384)), ("peek.png", None)]:
    im = Image.open(A + "\\" + name).convert("RGBA")
    if box:
        im = im.crop(box)
    bc, bcmp = pale_over_dark(im)
    af = matte(im)
    ac, acmp = pale_over_dark(af)
    print("%-14s 白边 前 %5d → 后 %5d   降 %.1f%%" % (name, bc, ac, 100 * (1 - ac / max(1, bc))))
    rows.append((name, bcmp, acmp))

CELL = (400, 470)
board = Image.new("RGB", (CELL[0] * 4, CELL[1] * 2), BG)
for i, (name, bc, ac) in enumerate(rows):
    for j, comp in enumerate((bc, ac)):
        hh, ww = comp.shape[:2]
        pw = int(ww * 0.55)
        crop = Image.fromarray(comp).crop(((ww - pw) // 2, 0, (ww + pw) // 2, hh))
        board.paste(crop.resize(CELL, Image.LANCZOS), (i * CELL[0], j * CELL[1]))
p = r"F:\Daodao\形象\_mobile_matte_1125.png"
board.save(p)
print("对比图（上排前后处理前 / 下排处理后）:", p)
