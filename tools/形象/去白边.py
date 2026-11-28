# -*- coding: utf-8 -*-
# 程序版本：v0.2 | 2026-11-28 | 立绘去白边：按 alpha 反解白底混色 + 收掉毛边，轮廓才贴得住人
r"""白边的成因不是「图有白边」，是「白底混进了边缘颜色」：
  PNG 半透明边缘像素的 RGB 是「人物色 × α + 白底 × (1-α)」的观测值，
  直接按原色画出来，那圈就是白的；缩图（bicubic）还会把白往外抹一圈。
做法：
  1. α<50 的毛边直接清掉（原来 alpha>20 都算实体，那圈就是糊的）；
  2. 对 α>=50 的像素反解：rgb' = (rgb - 255×(1-α)) / α，把白底贡献扣掉，得到人物真实色；
  3. 保留原包围盒与尺寸，不动构图，只换颜色与 alpha。
用法：
  python 去白边.py --dry            # 只量，不写
  python 去白边.py --apply          # 处理 _bundle 顶层 png，先备份 .bak_20261128_defringe
"""
import os, sys, glob, shutil
import numpy as np
from PIL import Image

BUN = r'F:\Daodao\src\桌面分身\_bundle'
TARGETS = ('face_*.png', 'expr_*.png', 'walk8_*.png', 'mount*.png', 'pose_*.png', 'swordfly_*.png')


def defringe(im, dry=False):
    a = np.asarray(im.convert('RGBA')).astype(np.float32)
    al = a[:, :, 3]
    rgb = a[:, :, :3]
    keep = al >= 50
    out = a.copy()
    out[~keep, 3] = 0
    out[~keep, :3] = 0
    if keep.any():
        aa = (al[keep] / 255.0)[:, None]
        c = (rgb[keep] - 255.0 * (1.0 - aa)) / np.maximum(aa, 1e-3)
        out[keep, :3] = np.clip(c, 0, 255)
    # 收毛边：α<170 的一圈直接砍掉，避免渲染侧硬阈值留下一层灰
    out[al < 170, 3] = 0
    out[al < 170, :3] = 0
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), 'RGBA')


def edge_stats(a):
    al = a[:, :, 3]
    solid = al >= 200
    t = np.zeros_like(solid)
    t[1:, :] |= solid[:-1, :] & (al[1:, :] < 200)
    t[:-1, :] |= solid[1:, :] & (al[:-1, :] < 200)
    t[:, 1:] |= solid[:, :-1] & (al[:, 1:] < 200)
    t[:, :-1] |= solid[:, 1:] & (al[:, :-1] < 200)
    if t.sum() == 0:
        return 0.0
    whiteish = (a[:, :, :3].min(axis=2) >= 225) & t
    return 100.0 * float(whiteish.sum()) / float(t.sum())


if __name__ == '__main__':
    dry = '--dry' in sys.argv
    apply = '--apply' in sys.argv
    files = []
    for pat in TARGETS:
        files += sorted(glob.glob(os.path.join(BUN, pat)))
    n = 0
    worst = []
    for p in files:
        im = Image.open(p)
        before = edge_stats(np.asarray(im.convert('RGBA')))
        new = defringe(im)
        after = edge_stats(np.asarray(new))
        worst.append((before, after, os.path.basename(p)))
        if apply:
            bak = p + '.bak_20261128_defringe'
            if not os.path.exists(bak):
                shutil.copy2(p, bak)
            new.save(p)
        n += 1
    worst.sort(reverse=True)
    print('处理 %d 张%s' % (n, '' if apply else '（dry，未写盘）'))
    print('  白边占比 前 -> 后（最差 6 张）')
    for b, a2, nm in worst[:6]:
        print('  %-28s %5.1f%% -> %5.1f%%' % (nm, b, a2))
