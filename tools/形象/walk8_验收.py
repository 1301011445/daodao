# -*- coding: utf-8 -*-
"""walk8 素材验收（电脑端复跑，判据与云主机同口径）
G1 透明区底残留色差 <=10（白边根因）
G2 8 帧轮廓画框中心漂移 <=1.0px
G3 脚底基线 y 漂移 <=1.0px
G4 步幅（脚底 x 极差）>=6px（没把腿钉死）
用法: walk8_验收.py <png路径>
"""
import sys
import numpy as np
from PIL import Image


def check(path):
    im = Image.open(path).convert('RGBA')
    a = np.array(im).astype(np.float32)
    al, rgb = a[..., 3], a[..., :3]
    t = al < 10
    leak = int((t & (rgb.min(axis=2) > 240)).sum())   # 透明区里的纯白像素数=白边根因
    w = im.width // 8
    cx, base, fx = [], [], []
    for i in range(8):
        f = a[:, i * w:(i + 1) * w]
        yy, xx = np.where(f[..., 3] > 20)
        cx.append((xx.min() + xx.max()) / 2.0)
        base.append(yy.max())
        fx.append(xx[yy >= yy.max() - 3].mean())
    print(f'透明白底像素={leak} (==0) | 画框中心漂移={max(cx)-min(cx):.2f}px (<=1.0) | '
          f'基线漂移={max(base)-min(base):.0f}px (<=1.0) | 步幅={max(fx)-min(fx):.2f}px (>=6)')
    ok = leak == 0 and (max(cx) - min(cx)) <= 1.0 and (max(base) - min(base)) <= 1.0 and (max(fx) - min(fx)) >= 6
    print('WALK8', 'PASS' if ok else 'FAIL')
    return ok


if __name__ == '__main__':
    sys.exit(0 if check(sys.argv[1]) else 1)

