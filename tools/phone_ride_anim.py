# -*- coding: utf-8 -*-
# 手机端骑乘「动起来」模拟：照 DaoOverlay.drawRide 的同一套算式逐帧合成，
# 用来在没真机的情况下先看清走动时会不会出框、比例是否舒服
import os
import math
from PIL import Image, ImageDraw

A = r"F:\Daodao\src\_apk\assets"
OUT = r"F:\Daodao\_diag_look\手机骑乘_动.gif"

PAD_X, PAD_TOP, PAD_BOT = 0.05, 0.10, 0.05
RIDE_H = 0.72
K = {"mount_milu.png": 0.86, "mount_bailongma.png": 0.86,
     "mount_unicorn.png": 0.86, "mount_shenlu.png": 0.86, "mount_cloud.png": 0.50}
FR = {"mount_milu.png": 0.51, "mount_bailongma.png": 0.63,
      "mount_unicorn.png": 0.59, "mount_shenlu.png": 0.49, "mount_cloud.png": 0.44}

W0, H0 = 500, 806          # 0.62 宽高比
ix, iy = int(W0 * PAD_X), int(H0 * PAD_TOP)
w = W0 - ix * 2
h = H0 - iy - int(H0 * PAD_BOT)

CASES = [("mount_milu.png", "ride_10.png", 0.680, "麋鹿+少女"),
         ("mount_unicorn.png", "ride_8.png", 0.600, "独角兽+剑客")]


def comp(mf, rf, sr, t):
    mb = Image.open(os.path.join(A, mf)).convert("RGBA")
    rb = Image.open(os.path.join(A, rf)).convert("RGBA")
    mi = list(K).index(mf)
    mh = h * K[mf]
    mw = mh * mb.width / mb.height
    if mw > w * 0.96:
        mw = w * 0.96
        mh = mw * mb.height / mb.width
    if mh > h * 0.92:
        mh = h * 0.92
        mw = mh * mb.width / mb.height
    rh = mh * RIDE_H
    # 动效：马/鹿/神鹿 3.x Hz 小颠，云慢飘
    if mi in (0,):
        mdy = math.sin(t * 3.1) * 0.010 * h
        mrot = math.sin(t * 3.1) * 1.5
    elif mi in (1, 2):
        mdy = math.sin(t * 3.4) * 0.009 * h
        mrot = math.sin(t * 3.4) * 1.4
    elif mi == 3:
        mdy = math.sin(t * 2.4) * 0.008 * h
        mrot = math.sin(t * 2.4) * 1.1
    else:
        mdx = math.sin(t * 0.85) * 0.030 * w
        mdy = math.sin(t * 1.25) * 0.012 * h
    mdx = 0.0

    canvas = Image.new("RGBA", (W0, H0), (255, 255, 255, 255))
    d = ImageDraw.Draw(canvas)
    d.rectangle([ix, iy, ix + w - 1, iy + h - 1], outline=(150, 190, 235))
    d.ellipse([ix + w * 0.24, iy + h - h * 0.03, ix + w * 0.76, iy + h + h * 0.005],
              fill=(228, 228, 228, 140))
    # 坐骑（含轻微俯仰）：绕鞍面旋转后贴回
    mimg = mb.resize((max(2, int(mw)), max(2, int(mh))), Image.LANCZOS)
    rot = mimg.rotate(-mrot, resample=Image.BICUBIC, expand=True)
    cx = ix + w / 2 - rot.width / 2
    cy = iy + h - mh + mdy - (rot.height - mimg.height) / 2
    canvas.alpha_composite(rot, (int(cx), int(cy)))
    saddleY = h - mh * FR[mf]
    rw = rh * rb.width / rb.height
    if rw > w * 0.92:
        rw = w * 0.92
        rh = rw * rb.height / rb.width
    top = saddleY - rh * sr + mdy
    if top < 0:
        shift = -top
    else:
        shift = 0
    rimg = rb.resize((max(2, int(rw)), max(2, int(rh))), Image.LANCZOS)
    canvas.alpha_composite(rimg, (int(ix + w / 2 - rw / 2), int(iy + top + shift)))
    flat = Image.new("RGB", canvas.size, (255, 255, 255))
    flat.paste(canvas, (0, 0), canvas)
    return flat


frames = []
N, FPS = 24, 12
for k in range(N):
    t = k / FPS
    row = [comp(mf, rf, sr, t) for mf, rf, sr, _ in CASES]
    sheet = Image.new("RGB", (W0 * len(row) + 8 * (len(row) - 1), H0), (255, 255, 255))
    for i, im in enumerate(row):
        sheet.paste(im, (i * (W0 + 8), 0))
    frames.append(sheet)

frames[0].save(OUT, save_all=True, append_images=frames[1:], duration=int(1000 / FPS), loop=0)
print("ok", OUT, frames[0].size, len(frames))
