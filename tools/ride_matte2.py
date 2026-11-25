"""自适应白/灰底抠图：以边框像素的中位亮度作为底色，按距离算 alpha，并反预乘去底污染。"""
import sys
from PIL import Image
import numpy as np


def matte(src, dst, k=16.0):
    im = Image.open(src).convert("RGB")
    a = np.array(im).astype(np.float32)
    mn = a.min(axis=2)
    border = np.concatenate([mn[0, :], mn[-1, :], mn[:, 0], mn[:, -1]])
    base = float(np.median(border))
    al = np.clip((base - mn) / k, 0, 1)
    safe = np.where(al > 0.02, al, 1.0)
    rgb = np.clip((a - (1 - al[..., None]) * base) / safe[..., None], 0, 255)
    out = np.dstack([rgb, al * 255]).astype(np.uint8)
    c = Image.fromarray(out, "RGBA")
    arr = np.array(c)
    m = arr[:, :, 3] > 20
    ys, xs = np.where(m)
    c = c.crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))
    c.save(dst)
    print("matte", dst, c.size, "base", round(base, 1))
    return c


if __name__ == "__main__":
    matte(sys.argv[1], sys.argv[2])
