# -*- coding: utf-8 -*-
"""头身比局部修正（2026-11-28）
只动「头」这一段，腿和身体一像素不动：以颈部（宽度最窄处）为支点，
把头部这一段按 k 倍放大，整身高度只增加 (k-1)*头高，头身比从 H/头高 拉回 6.5–8.0。

为什么不用 AI 重绘整身：试过 image_edit 让头放大 35%，出图 5.42 头身（比下限 6.5 还低），
肩甲细节也被改，等于换了个角色。局部缩放只改尺寸不改画风（Q-183）。

用法：
  python 头身修正.py --dry                 # 只出到 _bundle\_new2，不动线上素材
  python 头身修正.py --apply               # 备份后替换 _bundle 里的原图
"""
import os, sys, shutil
import numpy as np
from PIL import Image

BUN = r"F:\Daodao\src\桌面分身\_bundle"
OUT = os.path.join(BUN, "_new2")
TARGET = 7.2
NAMES = ["face_7", "face_8", "face_11"]


def profile(im):
    m = np.asarray(im.split()[-1]) > 8
    ys, xs = np.where(m)
    bb = (xs.min(), ys.min(), xs.max() + 1, ys.max() + 1)
    c = im.crop(bb)
    a = np.asarray(c.split()[-1]) > 8
    W, H = c.size
    widths = np.array([(lambda r: (r.max() - r.min() + 1) if r.size else 0)(np.where(a[y])[0]) for y in range(H)])
    hw = int(widths[:max(3, int(H * 0.22))].max())
    neck = None
    for i in range(int(H * 0.22 * 0.45), int(H * 0.6)):
        if 0 < widths[i] < 0.55 * hw:
            neck = i
            break
    return c, W, H, neck, hw


def build(c, W, H, neck, k):
    kw = 1 + (k - 1) * 0.6                      # 横向少放一点，避免大头娃娃
    hH = int(round(neck * k))
    head = c.crop((0, 0, W, neck)).resize((int(round(W * kw)), hH), Image.LANCZOS)
    body = c.crop((0, neck, W, H))
    newW = max(head.width, W)
    newH = hH + body.height
    out = Image.new("RGBA", (newW, newH), (0, 0, 0, 0))
    # 头与身同轴对齐：都按 W 的中心线居中
    out.alpha_composite(head, ((newW - head.width) // 2, 0))
    out.alpha_composite(body, ((newW - W) // 2, hH))
    # 颈部接缝做 3 行交叉淡化，避免出现一条硬边
    a = np.asarray(out).astype(np.float32)
    for d in range(-3, 3):
        y = hH + d
        if 0 <= y < newH:
            t = (d + 3) / 6.0
            top = a[hH - 1].copy()
            bot = a[hH].copy()
            a[y] = top * (1 - t) + bot * t
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), "RGBA")


def fix(name):
    p = os.path.join(BUN, name + ".png")
    im = Image.open(p).convert("RGBA")
    c, W, H, neck, hw = profile(im)
    if not neck:
        print("%s 找不到颈部，跳过" % name)
        return None
    r0 = H / neck
    if 6.5 <= r0 <= 8.0:
        print("%s 比值 %.2f 已达标，跳过" % (name, r0))
        return None
    # 两头都要能修：比值 >8 是头偏小（放大头），<6.5 是头偏大（缩头）。
    # 放大/缩小后评审再测的「颈部」位置会变（接缝改变了宽度剖面），
    # 所以不能算一次就交：按实测值反推 k 迭代，直到真测出来落在 6.5–8.0。
    k = (H - neck) / ((TARGET - 1) * neck)
    out, r1 = None, None
    for _ in range(6):
        out = build(c, W, H, neck, k)
        _, W2, H2, neck2, _ = profile(out)
        if not neck2:
            r1 = None
            break
        r1 = H2 / neck2
        if abs(r1 - TARGET) <= 0.2:
            break
        k *= (r1 / TARGET) ** 0.85              # 阻尼迭代，避免来回抖
        k = max(0.45, min(2.4, k))
    os.makedirs(OUT, exist_ok=True)
    out.save(os.path.join(OUT, name + ".png"))
    print("%s 头身比 %.2f → %.2f（k=%.2f，原头高 %d，尺寸 %dx%d → %dx%d）" %
          (name, r0, r1 if r1 else 0.0, k, neck, W, H, out.size[0], out.size[1]))
    return r1


if __name__ == "__main__":
    apply = "--apply" in sys.argv
    names = [a for a in sys.argv[1:] if not a.startswith("--")] or NAMES
    for n in names:
        r = fix(n)
        if apply and os.path.exists(os.path.join(OUT, n + ".png")):
            src = os.path.join(OUT, n + ".png")
            bak = os.path.join(BUN, n + ".png.bak_20261128_a1")
            if not os.path.exists(bak):
                shutil.copy2(os.path.join(BUN, n + ".png"), bak)
            shutil.copy2(src, os.path.join(BUN, n + ".png"))
    print("A1FIX|apply=%s|out=%s" % (int(apply), OUT))
