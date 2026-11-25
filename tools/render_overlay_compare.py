# -*- coding: utf-8 -*-
"""离线重放悬浮窗的网格变形（同一套系数），把「旧摆幅 / 新摆幅」并排出 GIF。
说明：这是按 drawWarp 的逐行位移公式做的近似重放，不是安卓真机截图（本机 adb 看不到设备）。
"""
import os, math
import numpy as np
from PIL import Image, ImageDraw, ImageFont

SHEET = r"F:\Daodao\src\_apk\assets\walk8.png"
OUT = r"F:\Daodao\形象"
W, H = 260, 380
CELL = (300, 420)

def load_frame(idx):
    im = Image.open(SHEET).convert("RGBA")
    n = 8
    fw = im.size[0] // n
    f = im.crop((idx * fw, 0, (idx + 1) * fw, im.size[1]))
    # 白底键掉（跟 keyWhite 一个口径：近中性白）
    a = np.array(f).astype(int)
    r, g, b, al = a[:, :, 0], a[:, :, 1], a[:, :, 2], a[:, :, 3]
    white = (r > 225) & (g > 225) & (b > 225) & (np.maximum(np.maximum(r, g), b) - np.minimum(np.minimum(r, g), b) <= 14)
    a[:, :, 3] = np.where(white, 0, al)
    f = Image.fromarray(a.astype(np.uint8), "RGBA")
    # 等比放到 H 高
    nh = H
    nw = max(1, int(f.size[0] * nh / f.size[1]))
    return f.resize((nw, nh), Image.LANCZOS)

def shift_rows(img, dx_of_ny, dy_of_ny):
    """逐行水平平移 + 垂直错位，近似 mesh 变形的主效应。"""
    arr = np.array(img).astype(np.float32)
    h, w = arr.shape[:2]
    out = np.zeros_like(arr)
    for yi in range(h):
        ny = yi / (h - 1.0)
        sy = yi - dy_of_ny(ny)
        sy0 = int(math.floor(sy)); t = sy - sy0
        sy0 = max(0, min(h - 2, sy0))
        sx = dx_of_ny(ny)
        for c in range(4):
            row = arr[sy0, :, c] * (1 - t) + arr[sy0 + 1, :, c] * t
            out[yi, :, c] = np.interp(np.arange(w) - sx, np.arange(w), row, left=0, right=0)
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), "RGBA")

def frame_at(t, walking, fi, new):
    """t: 秒；walking：是否走路；fi：当前帧号（0~7）"""
    base = load_frame(fi)
    w = float(base.size[0]); h = float(base.size[1])
    breath = math.sin(t * 1.05)
    sway = math.sin(t * 0.52)
    lag = math.sin(t * 0.52 - 0.8)
    tilt = math.sin(t * 0.47 + 0.5)
    phase = (fi / 8.0) * 2 * math.pi
    step = math.sin(phase) if walking else 0.0
    if new:
        k_sway, k_lag, k_head, k_shear = 0.005, 0.0045, 0.18, 0.010
    else:
        k_sway, k_lag, k_head, k_shear = 0.013, 0.011, 0.45, 0.020
    cap = (0.018 if new else 0.05) * w

    def dx_of_ny(ny):
        dx = k_sway * w * sway * (ny ** 1.7) + k_lag * w * lag * (ny ** 2.3)
        dy_breath = -0.007 * h * breath * math.exp(-(((ny - 0.44) / 0.20) ** 2))
        if ny < 0.30:
            hs = tilt * (0.30 - ny) * (0.35 * w) * k_head
            hs = max(-cap, min(cap, hs))
            dx += hs
        if walking and ny > 0.55:
            dx += k_shear * w * step * (ny - 0.55) / 0.45
        return dx

    def dy_of_ny(ny):
        dy = -0.007 * h * breath * math.exp(-(((ny - 0.44) / 0.20) ** 2))
        if walking and ny > 0.55:
            dy += -abs(step) * 0.010 * h * ny * ny
        return dy

    im = shift_rows(base, dx_of_ny, dy_of_ny)
    canvas = Image.new("RGBA", CELL, (14, 21, 38, 255))
    canvas.alpha_composite(im, ((CELL[0] - im.size[0]) // 2, CELL[1] - im.size[1] - 6))
    return canvas.convert("RGB")

def build(walking, name):
    frames = []
    n = 24
    for k in range(n):
        t = k * 0.09                      # 一拍 90ms，跟 beat 一致
        fi = (k // 2) % 8 if walking else 0
        old = frame_at(t, walking, fi, False)
        new = frame_at(t, walking, fi, True)
        comp = Image.new("RGB", (CELL[0] * 2 + 12, CELL[1] + 34), (10, 14, 24))
        comp.paste(old, (0, 0)); comp.paste(new, (CELL[0] + 12, 0))
        d = ImageDraw.Draw(comp)
        f = ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", 18)
        d.text((8, CELL[1] + 6), "旧：摆动 1.3% / 步态 3.2s", font=f, fill=(235, 150, 150))
        d.text((CELL[0] + 20, CELL[1] + 6), "新：摆动 0.5% / 步态跟帧 1.44s", font=f, fill=(150, 220, 175))
        frames.append(comp)
    p = os.path.join(OUT, name)
    frames[0].save(p, save_all=True, append_images=frames[1:], duration=90, loop=0)
    print(p, os.path.getsize(p) // 1024, "KB")

build(False, "_cmp_stand.gif")
build(True, "_cmp_walk.gif")
