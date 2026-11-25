# -*- coding: utf-8 -*-
"""把生成的 8 格走路图切成 8 张 192x384 PNG（去白底、按脚底对齐）。用法：切片_走路表.py 6|7"""
import numpy as np, os, sys
from PIL import Image

sp = sys.argv[1] if len(sys.argv) > 1 else "6"
S = r"F:\Daodao\_diag_look\走路生成\sheet_%s.png" % sp
A = r"F:\Daodao\src\_apk\assets"
B = r"F:\Daodao\src\桌面分身\_bundle"
OUT = r"F:\Daodao\_diag_look\走路生成"
W, H = 192, 384

im = Image.open(S).convert("RGB")
SW, SH = im.size
fw = SW // 8


def cut_white(im):
    a = np.array(im).astype(np.float32)
    mx = a.max(2); mn = a.min(2)
    white = (mn > 235) & ((mx - mn) < 12)
    alpha = np.where(white, 0, 255).astype(np.uint8)
    near = (mn > 205) & (mn <= 235) & ((mx - mn) < 20)
    alpha[near] = 160
    return Image.fromarray(np.dstack([a.astype(np.uint8), alpha]), "RGBA")


frames = []
for i in range(8):
    f = cut_white(im.crop((i * fw, 0, (i + 1) * fw, SH)))
    al = np.array(f)[..., 3] > 40
    ys, xs = np.where(al)
    if ys.size == 0:
        frames.append(Image.new("RGBA", (W, H), (0, 0, 0, 0)))
        continue
    body = f.crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))
    bw, bh = body.size
    scale = 342.0 / bh
    nw = max(1, int(round(bw * scale)))
    body = body.resize((nw, 342), Image.LANCZOS)
    canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    canvas.alpha_composite(body, ((W - nw) // 2, H - 10 - 342))
    frames.append(canvas)

for i, f in enumerate(frames):
    f.save(os.path.join(A, "walk8_%s_%d.png" % (sp, i + 1)))
    f.save(os.path.join(B, "walk8_%s_%d.png" % (sp, i + 1)))

sheet = Image.new("RGBA", (W * 8, H), (0, 0, 0, 0))
for i, f in enumerate(frames):
    sheet.paste(f, (i * W, 0), f)
sheet.save(os.path.join(A, "walk8_%s.png" % sp))

mont = Image.new("RGB", (W * 4, H * 2), (250, 250, 250))
for i, f in enumerate(frames):
    bg = Image.new("RGBA", (W, H), (250, 250, 250, 255))
    bg.alpha_composite(f)
    mont.paste(bg.convert("RGB"), ((i % 4) * W, (i // 4) * H))
mont.save(os.path.join(OUT, "切片预览_%s.png" % sp))
print("sp%s：8 帧已写入 assets 与 _bundle，预览 %s" % (sp, OUT))
