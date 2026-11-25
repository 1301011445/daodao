# -*- coding: utf-8 -*-
"""离线复刻 matteInPlace + deFringe，验证手机端素材的白边是否真被清掉。
按 Java 里同一套阈值做：泛洪清纯白 → 边缘两圈按白度估 alpha + 去白。"""
import numpy as np
from PIL import Image

A = r"F:\Daodao\src\_apk\assets"


def near_white(r, g, b, a):
    if a < 60:
        return False
    if r < 225 or g < 225 or b < 225:
        return False
    return (max(r, g, b) - min(r, g, b)) <= 14


def matte(im):
    a = np.array(im.convert("RGBA")).astype(np.int32)
    h, w = a.shape[:2]
    bg = np.zeros((h, w), bool)
    stack = []
    for x in range(w):
        for y in (0, h - 1):
            stack.append((y, x))
    for y in range(h):
        for x in (0, w - 1):
            stack.append((y, x))
    while stack:
        y, x = stack.pop()
        if bg[y, x]:
            continue
        px = a[y, x]
        if not near_white(px[0], px[1], px[2], px[3]):
            continue
        bg[y, x] = True
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx < w and not bg[ny, nx]:
                stack.append((ny, nx))
    a[..., 3] = np.where(bg, 0, a[..., 3])
    # 第二刀：素材自带的半透明近白混色，按亮度打折 alpha
    r0, g0, b0, al0 = a[..., 0], a[..., 1], a[..., 2], a[..., 3]
    lum = np.minimum(np.minimum(r0, g0), b0)
    semi = (al0 > 6) & (al0 < 250) & (lum >= 215)
    k = np.minimum(1.0, (255.0 - lum) / 40.0)
    a[..., 3] = np.where(semi, (al0 * k).astype(np.int32), al0)
    for _ in range(2):
        for y in range(h):
            for x in range(w):
                if bg[y, x]:
                    continue
                nb = ((x > 0 and bg[y, x - 1]) or (x < w - 1 and bg[y, x + 1])
                      or (y > 0 and bg[y - 1, x]) or (y < h - 1 and bg[y + 1, x]))
                if not nb:
                    continue
                r, g, b, al = a[y, x]
                if al < 40:
                    continue
                lum = min(r, g, b)
                mx = max(r, g, b)
                if mx - lum > 28 or lum < 140:
                    continue
                s = min(1.0, (255 - lum) / 78.0)
                s = max(0.04, s)
                inv = max(0.10, s)
                a[y, x, 0] = max(0, min(255, (r - 255 * (1 - s)) / inv))
                a[y, x, 1] = max(0, min(255, (g - 255 * (1 - s)) / inv))
                a[y, x, 2] = max(0, min(255, (b - 255 * (1 - s)) / inv))
                a[y, x, 3] = int(al * s)
                bg[y, x] = True
    return Image.fromarray(a.astype("uint8"), "RGBA")


def white_edge_score(im):
    """贴在深底上，数「亮度>200 且透明度>25」的像素 = 肉眼能看到的白边。"""
    a = np.array(im.convert("RGBA")).astype(int)
    r, g, b, al = a[..., 0], a[..., 1], a[..., 2], a[..., 3]
    lum = np.minimum(np.minimum(r, g), b)
    return int(((lum > 200) & (al > 25)).sum())


cases = [("stand_6.png", None), ("peek.png", None), ("walk8_6.png", (0, 0, 192, 384))]
rows = []
for name, box in cases:
    im = Image.open(f"{A}\\{name}").convert("RGBA")
    if box:
        im = im.crop(box)
    before = im.copy()
    after = matte(im)
    rows.append((name, white_edge_score(before), white_edge_score(after), before, after))
    print(name, "白边像素 前/后 =", rows[-1][1], "/", rows[-1][2])

# 拼对比图：上排是处理前，下排是处理后，都贴在深色背景上，右半是 3 倍放大
board = Image.new("RGB", (3 * 420, 2 * 460), (16, 22, 36))
d = None
for i, (name, sb, sa, before, after) in enumerate(rows):
    for j, im in enumerate((before, after)):
        bg = Image.new("RGBA", im.size, (16, 22, 36, 255))
        bg.alpha_composite(im)
        crop = bg.convert("RGB")
        # 取人物中上部一块放大，边缘最明显
        w, h = crop.size
        pw = min(w, int(w * 0.6))
        c2 = crop.crop(((w - pw) // 2, 0, (w + pw) // 2, h)).resize((420, 460), Image.LANCZOS)
        board.paste(c2, (i * 420, j * 460))
board.save(r"F:\Daodao\形象\_mobile_matte_1125.png")
print("对比图: F:\\Daodao\\形象\\_mobile_matte_1125.png")
