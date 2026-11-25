# -*- coding: utf-8 -*-
# 坐骑立绘抠白底 + 出"鞍面标尺"预览图
# 用法：python -X utf8 mount_matte.py <输入目录> <输出目录>
import sys, os
from PIL import Image, ImageDraw
import numpy as np
from collections import deque

IN = sys.argv[1]
OUT = sys.argv[2]
os.makedirs(OUT, exist_ok=True)


def matte(path):
    im = Image.open(path).convert("RGBA")
    a = np.asarray(im).copy()
    H, W = a.shape[:2]
    vis = np.zeros((H, W), bool)
    dq = deque()

    def near(y, x):
        r, g, b = a[y, x, 0], a[y, x, 1], a[y, x, 2]
        return min(int(r), int(g), int(b)) >= 236

    for x in range(W):
        for y in (0, H - 1):
            if near(y, x) and not vis[y, x]:
                vis[y, x] = True; dq.append((y, x))
    for y in range(H):
        for x in (0, W - 1):
            if near(y, x) and not vis[y, x]:
                vis[y, x] = True; dq.append((y, x))
    while dq:
        y, x = dq.popleft()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < H and 0 <= nx < W and not vis[ny, nx] and near(ny, nx):
                vis[ny, nx] = True; dq.append((ny, nx))
    a[:, :, 3] = np.where(vis, 0, a[:, :, 3])
    a[:, :, 3] = np.where(a[:, :, 3] < 90, 0, a[:, :, 3])
    # 半透边缘按亮度反预乘（白底）
    rgb = a[:, :, :3].astype(np.float32)
    al = a[:, :, 3:4].astype(np.float32) / 255.0
    safe = np.clip(al, 1e-4, 1)
    rgb = np.clip((rgb - (1.0 - al) * 255.0) / safe, 0, 255)
    a[:, :, :3] = rgb.astype(np.uint8)
    return Image.fromarray(a)


names = [os.path.splitext(f)[0] for f in os.listdir(IN) if f.lower().endswith(".png")]
for n in names:
    src = matte(os.path.join(IN, n + ".png"))
    bb = src.getbbox()
    src = src.crop(bb)
    h, w = src.size[1], src.size[0]
    # 统一出 600 高
    th = 600
    tw = max(2, round(w * th / h))
    src = src.resize((tw, th), Image.LANCZOS)
    src.save(os.path.join(OUT, n + "_m.png"))
    # 标尺图：每 5% 一条线，方便读鞍面比例
    g = Image.new("RGB", (tw, th), (255, 255, 255))
    bg = Image.new("RGBA", src.size, (255, 255, 255, 255)); bg.alpha_composite(src)
    g.paste(bg.convert("RGB"), (0, 0))
    d = ImageDraw.Draw(g)
    for p in range(0, 101, 5):
        y = int(th * p / 100.0)
        col = (220, 40, 40) if p % 20 == 0 else (200, 200, 200)
        d.line([(0, y), (tw, y)], fill=col, width=1)
        d.text((3, max(0, y - 11)), "%d" % p, fill=(200, 0, 0))
    g.save(os.path.join(OUT, n + "_grid.png"))
    print("%s  bbox=%s  ->  %dx%d" % (n, bb, tw, th))
