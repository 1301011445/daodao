# -*- coding: utf-8 -*-
"""离线复算手机浮窗的实际渲染：去白底 + 尺寸 + 球头像，出预览图（真跑，不是示意）"""
import os
from PIL import Image, ImageDraw

SRC = r"F:\Daodao\src\_apk\assets\walk8.png"
OUT = r"C:\Users\LDY\Doubao\chats\2026-11-11\new-chat"
os.makedirs(OUT, exist_ok=True)

im = Image.open(SRC).convert("RGBA")
W, H = im.size
FN = 8
FW, FH = W // FN, H

# ---- 与 DaoOverlay.keyWhite 完全相同的规则：只清「从四边连通的近白」 ----
def near_white(c):
    r, g, b, a = c
    if a < 60:
        return False
    if r < 225 or g < 225 or b < 225:
        return False
    return (max(r, g, b) - min(r, g, b)) <= 14

def key_white(img):
    px = img.load()
    w, h = img.size
    seen = [[False] * w for _ in range(h)]
    stack = []
    for x in range(w):
        for y in (0, h - 1):
            if near_white(px[x, y]) and not seen[y][x]:
                seen[y][x] = True
                stack.append((x, y))
    for y in range(h):
        for x in (0, w - 1):
            if near_white(px[x, y]) and not seen[y][x]:
                seen[y][x] = True
                stack.append((x, y))
    cleared = 0
    while stack:
        x, y = stack.pop()
        px[x, y] = (0, 0, 0, 0)
        cleared += 1
        for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
            if 0 <= nx < w and 0 <= ny < h and not seen[ny][nx] and near_white(px[nx, ny]):
                seen[ny][nx] = True
                stack.append((nx, ny))
    return cleared

cleared_total = 0
frames = []
for f in range(FN):
    fr = im.crop((f * FW, 0, (f + 1) * FW, FH))
    fr.load()
    cleared_total += key_white(fr)
    frames.append(fr)

# ---- 尺寸：与 DaoOverlay.petH 同口径（1080x2400 / density 2.75） ----
DENS = 2.75
SH = 2400
petH = min(int(SH * 0.16), int(104 * DENS))
petH = max(petH, int(84 * DENS))
petW = petH // 2
ball = int(52 * DENS)
print("尺寸：满身 %dx%d px（占屏高 %.1f%%），球 %d px" % (petW, petH, petH / SH * 100, ball))

# ---- 头部方框（与 headRect 同比例） ----
side = int(FW * 0.79)
hx0, hy0 = int(FW * 0.09), int(FH * 0.03)
head = frames[0].crop((hx0, hy0, min(FW, hx0 + side), min(FH, hy0 + side)))

def checker(size, cell=14):
    img = Image.new("RGBA", size, (255, 255, 255, 255))
    d = ImageDraw.Draw(img)
    for y in range(0, size[1], cell):
        for x in range(0, size[0], cell):
            if ((x // cell) + (y // cell)) % 2:
                d.rectangle([x, y, x + cell - 1, y + cell - 1], fill=(228, 228, 228, 255))
    return img

# 满身预览
big = checker((petW * 3, petH * 3))
fr0 = frames[0].resize((petW * 3, petH * 3), Image.LANCZOS)
big.alpha_composite(fr0, (0, 0))
big.save(os.path.join(OUT, "浮窗_满身_预览.png"))

# 球预览
bs = ball * 3
bd = checker((bs, bs))
face = head.resize((int(bs * 1.06), int(bs * 1.06), ), Image.LANCZOS)
mask = Image.new("L", (bs, bs), 0)
ImageDraw.Draw(mask).ellipse([2, 2, bs - 3, bs - 3], fill=255)
bd.paste(face, (int(-bs * 0.03), int(bs * 0.04)), face.split()[3] if face.mode == "RGBA" else None)
# 用圆遮罩再裁一次
bd = Image.composite(bd, Image.new("RGBA", (bs, bs), (0, 0, 0, 0)), mask)
ImageDraw.Draw(bd).ellipse([2, 2, bs - 3, bs - 3], outline=(175, 198, 234, 255), width=3)
bd.save(os.path.join(OUT, "浮窗_小圆球_预览.png"))

# 8 帧动画条
strip = Image.new("RGBA", (8 * 110, 220), (40, 44, 56, 255))
for i, fr in enumerate(frames):
    t = fr.resize((110, 220), Image.LANCZOS)
    strip.alpha_composite(t, (i * 110, 0))
strip.save(os.path.join(OUT, "浮窗_八帧_预览.png"))

# ---- 数字：去白是否伤到人物 ----
def opaque_ratio(fr):
    px = fr.load()
    n = sum(1 for y in range(0, FH, 2) for x in range(0, FW, 2) if px[x, y][3] > 60)
    return n / ((FW // 2) * (FH // 2))

before = opaque_ratio(im.crop((0, 0, FW, FH)))
after = opaque_ratio(frames[0])
print("第0帧不透明像素占比：清理前 %.1f%% → 清理后 %.1f%%" % (before * 100, after * 100))
print("八帧共清掉背景像素 %d 个（约占 %.1f%% 的画布）" % (cleared_total, cleared_total / (FW * FH * FN) * 100))
print("预览已写入：浮窗_满身_预览.png / 浮窗_小圆球_预览.png / 浮窗_八帧_预览.png")
