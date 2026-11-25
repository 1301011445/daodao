# -*- coding: utf-8 -*-
"""离线重放「正面站姿 + 抬手打招呼」：用 stand_6.png（192×384 正面视图），
按 drawWarp 同一套系数逐像素位移，出 GIF。仅作观感验证，不是安卓真机截图。
"""
import os, math
import numpy as np
from PIL import Image, ImageDraw, ImageFont

STAND = r"F:\Daodao\src\_apk\assets\stand_6.png"
OUT = r"F:\Daodao\形象"
CELL = (300, 430)
W_H = 380

def load():
    im = Image.open(STAND).convert("RGBA")
    nh = W_H
    nw = max(1, int(im.size[0] * nh / im.size[1]))
    return im.resize((nw, nh), Image.LANCZOS)

def warp(img, t, wave):
    arr = np.array(img).astype(np.float32)
    h, w = arr.shape[:2]
    out = np.zeros_like(arr)
    xs = np.arange(w)
    breath = math.sin(t * 1.05)
    sway = math.sin(t * 0.52)
    lag = math.sin(t * 0.52 - 0.8)
    tilt = math.sin(t * 0.47 + 0.5)
    cap = 0.018 * w
    for yi in range(h):
        ny = yi / (h - 1.0)
        # 纵向：呼吸（胸口抬起）
        sy = yi - (-0.007 * h * breath * math.exp(-(((ny - 0.44) / 0.20) ** 2)))
        sy0 = max(0, min(h - 2, int(math.floor(sy)))); tt = sy - int(math.floor(sy))
        dx = (0.005 * w * sway * (ny ** 1.7) + 0.0045 * w * lag * (ny ** 2.3)) * np.ones(w, dtype=np.float32)
        if ny < 0.30:
            hs = tilt * (0.30 - ny) * (0.35 * w) * 0.18
            hs = max(-cap, min(cap, hs))
            dx += hs
        if wave > 0.01:
            # 抬手：只有画面右侧那条手臂（nx>0.66，ny 0.10~0.46）往后上方抬
            nxr = xs / (w - 1.0)
            m = (nxr > 0.66) & (ny > 0.10) & (ny < 0.46)
            wx = (nxr - 0.66) / 0.34
            wy = 1.0 - abs(ny - 0.26) / 0.20
            if wy > 0:
                amp = 0.055 * w * wave * (wx ** 2) * math.sin(t * 9.5)
                amp = np.clip(amp, -0.022 * w, 0.022 * w)
                dx = np.where(m, dx + amp, dx)
            if ny < 0.55:
                dx += -0.008 * w * wave * math.sin(t * 4.7)
        for c in range(4):
            row = arr[sy0, :, c] * (1 - tt) + arr[sy0 + 1, :, c] * tt
            out[yi, :, c] = np.interp(xs - dx, xs, row, left=0, right=0)
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), "RGBA")

base = load()
frames = []
N = 40
for k in range(N):
    t = k * 0.09
    # 0~0.5s 应声点头；1s 起抬手挥 4 秒（动 3 下），6s 落手
    if t < 1.0:
        wave = 0.0
    elif t < 5.4:
        wave = 1.0
    else:
        wave = 0.0
    im = warp(base, t, wave)
    cv = Image.new("RGBA", CELL, (14, 21, 38, 255))
    cv.alpha_composite(im, ((CELL[0] - im.size[0]) // 2, CELL[1] - im.size[1] - 8))
    frames.append(cv.convert("RGB"))
p = os.path.join(OUT, "_cmp_greet.gif")
frames[0].save(p, save_all=True, append_images=frames[1:], duration=90, loop=0)
print(p, os.path.getsize(p) // 1024, "KB")
