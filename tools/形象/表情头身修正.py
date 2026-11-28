# -*- coding: utf-8 -*-
"""表情整图头身修正（2026-11-28 v158）
A1 把 4 号、9 号的立绘头身改到 7.30 / 7.17 之后，这两只的「表情整图」
（expr_4_* / expr_9_*）还是旧比例，换表情会突然跳头。
表情图姿势各不相同，自动找颈部会误判（实测有张被当成 10.2 头身），
所以这里不找颈部：同一只角色的表情图跟立绘是同一套画、头占画面比例一致
（expr 集内实测中位头身比 ≈5.6），直接用「整集头身比中位数」反推颈部位置，
再套用立绘那一刀同样的缩放倍数，两边比例就重新对齐。

用法：python 表情头身修正.py --dry | --apply
"""
import os, sys, shutil
import numpy as np
from PIL import Image

BUN = r"F:\Daodao\src\桌面分身\_bundle"
OUT = os.path.join(BUN, "_new2")
SETS = {4: 0.75, 9: 0.73}      # 按立绘实测反推：4 号 k=0.75→7.16（立绘 7.30）；9 号 0.66 会到 8.0，收到 0.73→7.2（立绘 7.17）
KEYS = ["happy", "sad", "angry", "sleep"]
BASE_R = 5.6                   # expr 集内实测头身比中位数


def crop_tight(im):
    a = np.asarray(im.split()[-1]) > 8
    ys, xs = np.where(a)
    return im.crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))


def ratio_of(im):
    """整图头身比（颈部最窄法），只作参考，不单独采信。"""
    c = crop_tight(im)
    A = np.asarray(c.split()[-1]) > 8
    H = c.size[1]
    wd = np.array([(lambda r: (r.max() - r.min() + 1) if r.size else 0)(np.where(A[y])[0]) for y in range(H)])
    hw = int(wd[:max(3, int(H * 0.22))].max())
    for i in range(int(H * 0.22 * 0.45), int(H * 0.6)):
        if 0 < wd[i] < 0.55 * hw:
            return H / i
    return None


def build(c, k):
    W, H = c.size
    neck = int(round(H / BASE_R))               # 集内中位头身比 → 颈部位置
    kw = 1 + (k - 1) * 0.6
    hH = int(round(neck * k))
    head = c.crop((0, 0, W, neck)).resize((int(round(W * kw)), hH), Image.LANCZOS)
    body = c.crop((0, neck, W, H))
    nW = max(head.width, W)
    nH = hH + body.height
    out = Image.new("RGBA", (nW, nH), (0, 0, 0, 0))
    out.alpha_composite(head, ((nW - head.width) // 2, 0))
    out.alpha_composite(body, ((nW - W) // 2, hH))
    a = np.asarray(out).astype(np.float32)
    for d in range(-3, 3):
        y = hH + d
        if 0 <= y < nH:
            t = (d + 3) / 6.0
            a[y] = a[hH - 1] * (1 - t) + a[hH] * t
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), "RGBA"), nH / hH


if __name__ == "__main__":
    apply_ = "--apply" in sys.argv
    for sp, k in SETS.items():
        for key in KEYS:
            p = os.path.join(BUN, "expr_%d_%s.png" % (sp, key))
            if not os.path.exists(p):
                print("缺 expr_%d_%s，跳过" % (sp, key))
                continue
            im = Image.open(p).convert("RGBA")
            c = crop_tight(im)
            out, r2 = build(c, k)
            r0 = ratio_of(im)
            os.makedirs(OUT, exist_ok=True)
            out.save(os.path.join(OUT, "expr_%d_%s.png" % (sp, key)))
            print("expr_%d_%-6s 原测 %-5s → 头身比 %.2f（k=%.2f，%dx%d → %dx%d）" %
                  (sp, key, ("%.2f" % r0) if r0 else "测不准", r2, k,
                   c.size[0], c.size[1], out.size[0], out.size[1]))
            if apply_:
                bak = p + ".bak_20261128_expr"
                if not os.path.exists(bak):
                    shutil.copy2(p, bak)
                shutil.copy2(os.path.join(OUT, "expr_%d_%s.png" % (sp, key)), p)
    print("EXPRFIX|apply=%d|out=%s" % (int(apply_), OUT))
