# -*- coding: utf-8 -*-
"""2026-11-25 小红书配图 v2：八帧走路条用 6 号（蓝双马尾），并对洋红边做去溢色。"""
import os, math
import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1440
D = r"F:\Daodao\推广草稿"
BG = (13, 19, 34)
f_t = ImageFont.truetype(r"C:\Windows\Fonts\msyhbd.ttc", 46)
f_s = ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", 28)


def key_soft(path):
    """按到洋红的距离估 alpha，并把残留粉色往灰里拉，避免一圈粉描边。"""
    im = Image.open(path).convert("RGBA")
    a = np.array(im).astype(np.float32)
    r, g, b, al = a[..., 0], a[..., 1], a[..., 2], a[..., 3]
    dist = np.sqrt((255 - r) ** 2 + g ** 2 + (255 - b) ** 2) / 441.0
    alpha = np.clip((dist - 0.22) / 0.22, 0, 1) * al / 255.0
    # 侵蚀 1px：把最外圈那层半透明粉环直接削掉
    e = alpha.copy()
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            e = np.minimum(e, np.roll(np.roll(alpha, dy, 0), dx, 1))
    alpha = e
    pink = np.clip(1 - dist / 0.34, 0, 1)
    gray = (0.35 * r + 0.5 * g + 0.15 * b)[..., None]
    rgb = a[..., :3] * (1 - pink[..., None]) + gray * pink[..., None]
    a[..., :3] = rgb
    a[..., 3] = alpha * 255
    return Image.fromarray(a.clip(0, 255).astype("uint8"), "RGBA")


im = Image.new("RGB", (W, H), BG)
d = ImageDraw.Draw(im)
d.text((60, 66), "八帧走路 · 上身摆动跟帧走", font=f_t, fill=(232, 241, 255))
d.text((62, 132), "头顶横移 285.9 → 291.8 px，随帧号单调起伏", font=f_s, fill=(140, 172, 214))

COL = 8
cw = W / COL
row_h = 420
for i in range(COL):
    fr = key_soft(rf"F:\Daodao\selfcheck_walk6_{i}.png")
    bbox = fr.getbbox()
    if bbox:
        fr = fr.crop(bbox)
    sc = min(row_h / fr.size[1], (cw - 16) / fr.size[0])
    fr = fr.resize((max(1, int(fr.size[0] * sc)), max(1, int(fr.size[1] * sc))), Image.LANCZOS)
    x = int(i * cw + (cw - fr.size[0]) / 2)
    im.paste(fr, (x, 300), fr)
    d.text((int(i * cw + cw / 2 - 9), 300 + row_h + 16), str(i + 1), font=f_s, fill=(120, 155, 200))

base_y, pp = 1080, 74
pts = [(x, base_y - pp * math.sin((x - 80) / 900 * 2 * math.pi)) for x in range(80, 990)]
d.line(pts, fill=(120, 170, 240), width=4)
for i in range(8):
    x = 80 + (900 / 8) * i
    y = base_y - pp * math.sin(i * math.pi / 4)
    d.ellipse((x - 7, y - 7, x + 7, y + 7), outline=(190, 215, 255), width=3)
    d.text((x - 8, base_y + 26), str(i + 1), font=f_s, fill=(140, 170, 210))
d.text((80, base_y + 118), "一轮 8 帧 = 2π，腿落地那帧摆动正在极值，不再是各摆各的",
       font=f_s, fill=(160, 185, 218))

p = os.path.join(D, "2026-11-25-img2-walk.png")
im.save(p)
print(p, im.size, os.path.getsize(p) // 1024, "KB")
