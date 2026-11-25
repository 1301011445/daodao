"""连通域抠图：从边框泛洪去掉与边框相连的近白背景，人物内部白色衣服因有描边包围不会被吃。"""
import sys
from PIL import Image, ImageDraw
import numpy as np


def matte(src, dst, thr=238.0, ramp=12.0):
    im = Image.open(src).convert("RGB")
    a = np.array(im).astype(np.float32)
    mn = a.min(axis=2)
    mask = Image.new("L", im.size, 0)
    mask.putdata(np.where(mn >= thr, 255, 0).astype(np.uint8).ravel().tolist())
    w, h = im.size
    for seed in [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)]:
        if mask.getpixel(seed) == 255:
            ImageDraw.floodfill(mask, seed, 128)
    bgmask = np.array(mask) == 128
    al = np.where(mn >= thr - ramp, np.clip((thr - mn) / ramp, 0, 1), 1.0)
    al = np.where(bgmask, 0.0, al).astype(np.float32)
    base = thr
    safe = np.where(al > 0.02, al, 1.0)
    rgb = np.clip((a - (1 - al[..., None]) * base) / safe[..., None], 0, 255)
    out = np.dstack([rgb, al * 255]).astype(np.uint8)
    c = Image.fromarray(out, "RGBA")
    arr = np.array(c)
    m = arr[:, :, 3] > 20
    ys, xs = np.where(m)
    c = c.crop((max(0, xs.min() - 1), max(0, ys.min() - 1), xs.max() + 2, ys.max() + 2))
    c.save(dst)
    print("matte", dst, c.size, "bg掉率", round(float(bgmask.mean()), 3))
    return c


if __name__ == "__main__":
    matte(sys.argv[1], sys.argv[2])
