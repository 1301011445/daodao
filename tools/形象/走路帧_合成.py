# -*- coding: utf-8 -*-
# 程序版本：v0.4 | 2026-11-28 | 从单张立绘合成真八帧走路（露腿拆脚交替外摆/长裙摆裙），自带 A8 双档自调
r"""形象走路不协调的根因：除 6/7 号外，其余形象只有「整只上下颠」的替代帧，两只脚始终粘在一起
（形象评审 A8 报 脚簇=1、步幅 0.5-6px），看着像滑行不像走。

做法（纯几何重采样，不重绘原画）：
  1. 腿区从 hip（0.62H）到脚底，以图心分左右；位移随高度按 (y-hip) 的 1.5 次幂渐增——
     胯部不动、脚动，接缝是渐变的，不会一刀切；
  2. 露腿档：两脚先有基础外开 b0（拆开粘住的鞋），再按相位交替外摆 A；
  3. 长裙档：整段下摆按 sin 同向摆（八帧八个角度，不是只有左右两张）；
  4. 外摆那侧抬脚 0.4%H；
  5. 八帧共用包围盒裁切；先转预乘 alpha 再重采样，否则脚边出白边鬼影；
  6. 生成后当场量 A8（脚簇/步幅 与 裙摆摆幅），不过就把幅度乘 1.3 再来，最多三档，
     记录每只形象最终用的倍数——宽腿裤、长裙各不相同，靠一套死参数过不了。

用法：
  python 走路帧_合成.py --dry sp2 sp12        # 写 _bundle\_walknew 预览，不动原图
  python 走路帧_合成.py --apply sp0 ...      # 覆盖 walk8_<sp>_1..8.png（备份 .bak_20261128_walk）
  python 走路帧_合成.py --apply all          # 14 只全做，腿/裙自动判档
"""
import os, sys, shutil
import numpy as np
from PIL import Image

BUN = r"F:\Daodao\src\桌面分身\_bundle"
OUTDIR = os.path.join(BUN, "_walknew")
SKIRT = {"10", "13"}          # 长裙：整段下摆摆
TUNE = (1.0, 1.3, 1.6, 2.0, 2.6)


def bilinear(a, sy, sx):
    h, w = a.shape[:2]
    sy = np.clip(sy, 0, h - 1.001)
    sx = np.clip(sx, 0, w - 1.001)
    y0 = np.floor(sy).astype(np.int32)
    x0 = np.floor(sx).astype(np.int32)
    fy = (sy - y0)[..., None]
    fx = (sx - x0)[..., None]
    p00 = a[y0, x0]
    p01 = a[y0, np.minimum(x0 + 1, w - 1)]
    p10 = a[np.minimum(y0 + 1, h - 1), x0]
    p11 = a[np.minimum(y0 + 1, h - 1), np.minimum(x0 + 1, w - 1)]
    return (p00 * (1 - fx) + p01 * fx) * (1 - fy) + (p10 * (1 - fx) + p11 * fx) * fy


def knock_white(im):
    """从四条边往里泛洪清掉不透明的近白残留（与 pet.cs 的 KnockoutWhite 同一口径：
    RGB>231 且 alpha>180）。这些白斑是抠图没抠净的底，走路时会跟着腿一起甩，最扎眼。"""
    a = np.asarray(im).astype(np.uint8).copy()
    h, w = a.shape[:2]
    al = a[:, :, 3].astype(np.int16)
    rgb = a[:, :, :3].astype(np.int16)
    white = (al > 180) & (rgb.min(axis=2) > 231)
    bg = np.zeros((h, w), bool)
    stk = []
    for x in range(w):
        for y in (0, h - 1):
            if white[y, x] and not bg[y, x]:
                bg[y, x] = True; stk.append((y, x))
    for y in range(h):
        for x in (0, w - 1):
            if white[y, x] and not bg[y, x]:
                bg[y, x] = True; stk.append((y, x))
    while stk:
        y, x = stk.pop()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx < w and white[ny, nx] and not bg[ny, nx]:
                bg[ny, nx] = True; stk.append((ny, nx))
    a[:, :, 3][bg] = 0
    return Image.fromarray(a, "RGBA")


def solid_mask(a):
    """按渲染侧 Hard() 同一口径取角色：alpha>=200 算实体（渲染时 alpha<200 本来就被丢弃）。
    白斑已经在 knock_white 阶段清掉，这里不再额外排除近白，免得把白裙白鞋也挖空。"""
    return a[:, :, 3] >= 200


def warp_frame(im, theta, mode, mul=1.0):
    a = np.asarray(im).astype(np.float32)
    h, w = a.shape[:2]
    m = solid_mask(np.asarray(im))
    ys, xs = np.where(m)
    if ys.size == 0:
        return im, (0, 0, w, h)
    y0, y1 = int(ys.min()), int(ys.max())
    H = y1 - y0 + 1
    hip = y0 + int(H * 0.62)
    bottom = y1
    cx = (xs.min() + xs.max()) / 2.0

    A = float(np.clip(H * 0.022, 8.0, 16.0)) * mul
    b0 = float(np.clip(H * 0.016, 5.0, 9.0)) * mul if mode == "legs" else 0.0
    lift = float(np.clip(H * 0.004, 1.5, 3.5)) if mode == "legs" else 0.0

    s = np.sin(theta)
    if mode == "legs":
        dL = b0 + A * max(0.0, s)
        dR = b0 + A * max(0.0, -s)
        lfL = lift if s > 0 else 0.0
        lfR = lift if s < 0 else 0.0
        dconst = 0.0
    else:
        dL = dR = 0.0
        dconst = A * 0.45 * s          # 有正负，八帧八个位置
        lfL = lfR = 0.0

    Y, X = np.mgrid[0:h, 0:w].astype(np.float32)
    ty = np.clip((Y - hip) / max(1.0, float(bottom - hip)), 0.0, 1.0) ** 1.5
    left = X < cx
    fe = np.clip(np.abs(X - cx) / 3.0, 0.0, 1.0)
    d = (np.where(left, -dL, dR) + dconst) * fe
    lf = np.where(left, lfL, lfR) * fe

    al = a[:, :, 3:4] / 255.0
    pm = np.concatenate([a[:, :, :3] * al, a[:, :, 3:4]], axis=2)
    sx = X - d * ty
    sy = Y + lf * ty
    outp = bilinear(pm, sy, sx)
    outp[Y < hip] = pm[Y < hip]
    oa = np.clip(outp[:, :, 3:4], 0, 255)
    orgb = np.where(oa > 0.5, np.clip(outp[:, :, :3] / np.maximum(oa / 255.0, 1e-3), 0, 255), 0)
    out = np.clip(np.concatenate([orgb, oa], axis=2), 0, 255).astype(np.uint8)
    mm = solid_mask(out)
    ys2, xs2 = np.where(mm)
    return Image.fromarray(out, "RGBA"), (int(xs2.min()), int(ys2.min()), int(xs2.max()) + 1, int(ys2.max()) + 1)


def gen(sp, mode, mul):
    im0 = knock_white(Image.open(os.path.join(BUN, "face_%s.png" % sp)).convert("RGBA"))
    outs, boxes = [], []
    for k in range(8):
        im, bb = warp_frame(im0, 2 * np.pi * k / 8.0, mode, mul)
        outs.append(im)
        boxes.append(bb)
    x0 = min(b[0] for b in boxes); y0 = min(b[1] for b in boxes)
    x1 = max(b[2] for b in boxes); y1 = max(b[3] for b in boxes)
    box = (max(0, x0 - 2), max(0, y0 - 2), min(im0.size[0], x1 + 2), min(im0.size[1], y1 + 2))
    return [o.crop(box) for o in outs]


def measure(frames):
    feet_n, seps, hem = [], [], []
    for im in frames:
        a = np.asarray(im.convert("RGBA"))
        m = solid_mask(a)
        ys, xs = np.where(m)
        if ys.size == 0:
            return 0, 0.0, 0.0
        y0, y1 = ys.min(), ys.max()
        H = y1 - y0 + 1
        band = m[max(0, y1 - int(H * 0.10)):y1 + 1]
        cols = np.where(band.any(axis=0))[0]
        gaps = np.where(np.diff(cols) > 2)[0] if cols.size else []
        segs = np.split(cols, gaps + 1) if cols.size else []
        feet_n.append(len(segs))
        seps.append(abs(float(segs[0].mean() - segs[-1].mean())) if len(segs) >= 2 else 0.0)
        lo = m[max(0, y1 - int(H * 0.25)):y1 + 1]
        cxx = np.where(lo.any(axis=0))[0]
        hem.append(float(cxx.mean()) if cxx.size else 0.0)
    fn = min(feet_n)
    stride = (max(seps) - min(seps)) if fn >= 2 else 0.0
    return fn, round(stride, 1), round(max(hem) - min(hem), 1)


def build(sp):
    mode = "skirt" if sp in SKIRT else "legs"
    best = None
    for mul in TUNE:
        frames = gen(sp, mode, mul)
        fn, stride, sway = measure(frames)
        ok = (fn >= 2 and stride >= 6) or sway >= 6
        if best is None:
            best = (mul, frames, fn, stride, sway, ok)
        if ok:
            best = (mul, frames, fn, stride, sway, ok)
            break
    return mode, best


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    dry = "--dry" in sys.argv
    apply = "--apply" in sys.argv
    if args == ["all"]:
        args = ["sp%d" % i for i in range(14)]
    if not args:
        print("要指定形象号：sp0 sp2 … 或 all")
        return 1
    os.makedirs(OUTDIR, exist_ok=True)
    for tag in args:
        sp = tag.replace("sp", "")
        mode, (mul, frames, fn, stride, sway, ok) = build(sp)
        print("sp%-3s %-5s 倍数=%.1f 帧=%s 脚簇=%d 步幅=%.1f 裙摆=%.1f -> %s"
              % (sp, mode, mul, frames[0].size, fn, stride, sway,
                 "PASS(腿)" if (fn >= 2 and stride >= 6) else ("PASS(裙)" if sway >= 6 else "FAIL")))
        for i, im in enumerate(frames):
            im.save(os.path.join(OUTDIR if dry else BUN, "walk8_%s_%d.png" % (sp, i + 1)))
        if apply:
            for i in range(1, 9):
                p = os.path.join(BUN, "walk8_%s_%d.png" % (sp, i))
                bak = p + ".bak_20261128_walk"
                if os.path.exists(p) and not os.path.exists(bak):
                    shutil.copy2(p, bak)
    print("完成")
    return 0


if __name__ == "__main__":
    sys.exit(main())
