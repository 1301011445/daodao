import sys, urllib.request
from PIL import Image
import numpy as np

def matte(src, dst):
    im = Image.open(src).convert("RGB")
    a = np.array(im).astype(np.float32)
    mn = a.min(axis=2)
    al = np.clip((250.0 - mn) / 15.0, 0, 1)   # 白底 253~255 -> 0
    safe = np.where(al > 0.02, al, 1)
    rgb = np.clip((a - (1 - al[..., None]) * 252.0) / safe[..., None], 0, 255)
    out = np.dstack([rgb, al * 255]).astype(np.uint8)
    c = Image.fromarray(out, "RGBA")
    arr = np.array(c)
    m = arr[:, :, 3] > 18
    ys, xs = np.where(m)
    c = c.crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))
    c.save(dst)
    print("matte", dst, c.size)
    return c

if __name__ == "__main__":
    src, dst = sys.argv[1], sys.argv[2]
    if src.startswith("http"):
        open(src.split("/")[-1] if False else r"F:\Daodao\_diag_look\_dl.png", "wb").write(
            urllib.request.urlopen(src, timeout=60).read())
        src = r"F:\Daodao\_diag_look\_dl.png"
    matte(src, dst)
