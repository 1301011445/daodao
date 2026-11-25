# -*- coding: utf-8 -*-
"""把生成的 8 格走路图切成 8 张 192x384 PNG（去白底、按脚底对齐）。"""
import numpy as np, os
from PIL import Image

S = r"F:\Daodao\_diag_look\走路生成\sheet_6.png"
A = r"F:\Daodao\src\_apk\assets"
OUT = r"F:\Daodao\_diag_look\走路生成"
W, H = 192, 384

im = Image.open(S).convert("RGB")
SW, SH = im.size
fw = SW // 8


def cut_white(im):
    a = np.array(im).astype(np.float32)
    # 白底：三通道都很亮且接近
    mx = a.max(2); mn = a.min(2)
    white = (mn > 235) & ((mx - mn) < 12)
    alpha = np.where(white, 0, 255).astype(np.uint8)
    # 边缘羽化：对接近白的像素给半透明
    near = (mn > 205) & (mn <= 235) & ((mx - mn) < 20)
    alpha[near] = 160
    out = np.dstack([a.astype(np.uint8), alpha])
    return Image.fromarray(out, "RGBA")


frames = []
for i in range(8):
    f = im.crop((i * fw, 0, (i + 1) * fw, SH))
    f = cut_white(f)
    arr = np.array(f)
    al = arr[..., 3] > 40
    ys, xs = np.where(al)
    if ys.size == 0:
        frames.append(Image.new("RGBA", (W, H), (0, 0, 0, 0)))
        continue
    box = (xs.min(), ys.min(), xs.max() + 1, ys.max() + 1)
    body = f.crop(box)
    bw, bh = body.size
    # 统一身高到 342（留 10px 底边），等比缩放
    scale = 342.0 / bh
    nw, nh = max(1, int(round(bw * scale))), 342
    body = body.resize((nw, nh), Image.LANCZOS)
    canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    canvas.alpha_composite(body, ((W - nw) // 2, H - 10 - nh))
    frames.append(canvas)

for i, f in enumerate(frames):
    f.save(os.path.join(A, "walk8_6_%d.png" % (i + 1)))
sheet = Image.new("RGBA", (W * 8, H), (0, 0, 0, 0))
for i, f in enumerate(frames):
    sheet.paste(f, (i * W, 0), f)
sheet.save(os.path.join(A, "walk8_6.png"))

mont = Image.new("RGB", (W * 4, H * 2), (250, 250, 250))
for i, f in enumerate(frames):
    bg = Image.new("RGBA", (W, H), (250, 250, 250, 255))
    bg.alpha_composite(f)
    mont.paste(bg.convert("RGB"), ((i % 4) * W, (i // 4) * H))
mont.save(os.path.join(OUT, "切片预览.png"))

# 判据：每帧脚部分簇 + 脚部横向跨度
print("帧 | 脚簇 | 脚 x 范围 | 身高")
ok = 0
for i, f in enumerate(frames):
    a = np.array(f)[..., 3] > 60
    ys = np.where(a.any(1))[0]
    foot = ys.max() - 4
    xs = np.where(a[foot - 4:foot + 1].any(0))[0]
    cl = 1 + len(np.where(np.diff(xs) > 3)[0]) if xs.size else 0
    print(i + 1, "|", cl, "|", (int(xs.min()), int(xs.max())), "|", ys.max() - ys.min() + 1)
    ok += 1 if cl >= 2 else 0
print("SUMMARY|分腿帧=%d/8" % ok)
