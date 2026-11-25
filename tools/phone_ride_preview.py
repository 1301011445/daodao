# -*- coding: utf-8 -*-
# 手机端骑乘配比模拟：完全不跑安卓，按 DaoOverlay.drawRide 的同一套算式拼出预览图
# 目的：换坐骑/改窗口比例后，先在这里看有没有裁头、比例对不对
import os, sys
from PIL import Image, ImageDraw

A = r"F:\Daodao\src\_apk\assets"
OUT = r"F:\Daodao\_diag_look\手机骑乘配比.png"

PAD_X, PAD_TOP, PAD_BOT = 0.05, 0.10, 0.05
RIDE_H = 0.62
MOUNTS = [
    ("mount_milu.png", 0.86, 0.51, "麋鹿"),
    ("mount_bailongma.png", 0.86, 0.63, "白龙马"),
    ("mount_unicorn.png", 0.86, 0.59, "独角兽"),
    ("mount_shenlu.png", 0.86, 0.49, "九色神鹿"),
    ("mount_cloud.png", 0.50, 0.44, "祥云"),
]
SEAT = [
    ("ride_10.png", 0.680, "少女"),
    ("ride_8.png", 0.600, "剑客"),
    ("ride_0.png", 0.606, "橙发少年"),
]

W0, H0 = 620, 1000
ix, iy = int(W0 * PAD_X), int(H0 * PAD_TOP)
w = W0 - ix * 2
h = H0 - iy - int(H0 * PAD_BOT)


def fit(im, maxw, maxh):
    sc = min(maxw / im.width, maxh / im.height)
    return im.resize((max(2, int(im.width * sc)), max(2, int(im.height * sc))), Image.LANCZOS)


cells = []
for mf, K, FR, mname in MOUNTS:
    mb = Image.open(os.path.join(A, mf)).convert("RGBA")
    for rf, sr, rname in SEAT:
        rb = Image.open(os.path.join(A, rf)).convert("RGBA")
        rh = 0
        mh = h * K
        mw = mh * mb.width / mb.height
        if mw > w * 0.96:
            mw = w * 0.96
            mh = mw * mb.height / mb.width
        if mh > h * 0.92:
            mh = h * 0.92
            mw = mh * mb.width / mb.height
        saddleY = h - mh * FR
        rh = mh * 0.72
        rw = rh * rb.width / rb.height
        if rw > w * 0.92:
            rw = w * 0.92
            rh = rw * rb.height / rb.width
        top = saddleY - rh * sr
        shift = -top if top < 0 else 0

        cell = Image.new("RGBA", (W0, H0), (255, 255, 255, 255))
        d = ImageDraw.Draw(cell)
        d.rectangle([0, 0, W0 - 1, H0 - 1], outline=(210, 210, 210))
        d.rectangle([ix, iy, ix + w - 1, iy + h - 1], outline=(160, 200, 240))
        # 地面阴影
        d.ellipse([ix + w * 0.24, iy + h - h * 0.03, ix + w * 0.76, iy + h + h * 0.005], fill=(226, 226, 226, 120))
        cy = iy + h - mh + shift
        cx = ix + (w - mw) / 2
        cell.alpha_composite(fit(mb, mw, mh), (int(cx), int(cy)))
        rx = ix + (w - rw) / 2
        ry = iy + top + shift
        cell.alpha_composite(fit(rb, rw, rh), (int(rx), int(ry)))
        d.text((8, 8), "%s + %s" % (mname, rname), fill=(120, 0, 0))
        frame = Image.new("RGB", cell.size, (255, 255, 255))
        frame.paste(cell.convert("RGB"), (0, 0))
        # 叠白底，避免透明处看起来是黑的
        bg = Image.new("RGBA", cell.size, (255, 255, 255, 255))
        bg.alpha_composite(cell)
        cells.append((bg.convert("RGB"), "%s+%s" % (mname, rname), top + shift))

cw, ch = W0 // 2, H0 // 2
cols = 3
rows = (len(cells) + cols - 1) // cols
sheet = Image.new("RGB", (cw * cols, ch * rows), (245, 245, 245))
for i, (im, name, headroom) in enumerate(cells):
    t = im.resize((cw, ch), Image.LANCZOS)
    dd = ImageDraw.Draw(t)
    dd.text((6, 6), "%s  头顶余量%.0f" % (name, headroom), fill=(180, 0, 0))
    sheet.paste(t, ((i % cols) * cw, (i // cols) * ch))
sheet.save(OUT)
print("window", W0, H0, "inner", w, h, "->", OUT, sheet.size)

