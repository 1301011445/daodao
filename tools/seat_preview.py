from PIL import Image
import numpy as np, sys

tH = 137
mh = 0.70 * tH
mt = Image.open(r"F:\Daodao\src\_apk\assets\mount_horse.png").convert("RGBA")
mw = mh * mt.width / mt.height
mt = mt.resize((int(round(mw)), int(round(mh))), Image.LANCZOS)
mTop = 6 - 0.62 * mh
saddle = mTop + 0.36 * mh

def preview(ride_path, seat, out):
    r = Image.open(ride_path).convert("RGBA")
    rh = 0.62 * tH
    rw = rh * r.width / r.height
    r = r.resize((int(round(rw)), int(round(rh))), Image.LANCZOS)
    rTop = saddle - rh * seat
    rxR = -rw / 2 - tH * 0.045
    O = int(abs(mTop) + abs(rTop) + 20)
    W = int(max(mw, rw) + 40); H = int(mh + rh + O + 20)
    cv = Image.new("RGBA", (W, H), (236, 238, 242, 255))
    cx = W / 2
    x0 = cx + rxR
    cv.alpha_composite(r, (int(round(x0)), int(round(rTop + O))))
    cv.alpha_composite(mt, (int(round(cx - mw / 2)), int(round(mTop + O))))
    cv.convert("RGB").save(out)
    print(out, "seat", seat, "rh", rh, "rw", rw, "rTop", rTop)

if __name__ == "__main__":
    p = sys.argv[1]
    for s in [0.40, 0.43, 0.46, 0.49]:
        preview(p, s, rf"F:\Daodao\_diag_look\seat_{s:.2f}.png")
