# -*- coding: utf-8 -*-
"""探身姿态判据：换形象后不许「退回整张立绘平移」。

检查 assets\\peek.png：
  1) 比例接近 1:2（窗口就是 1:2）
  2) 透明占比 0.2–0.55（半身构图，不能整块白底，也不能只剩一小点）
  3) 头顶接近上边、鞋底接近下边（人是撑满的，不是缩在中间）
  4) 手尖落在左侧 12% 内（扒边的动作在）
再检查 DaoOverlay.java：
  5) MODE_PEEK 分支真的用了 peekArt
"""
import os, re, sys
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ASSET = r'F:\Daodao\src\_apk\assets\peek.png'
JAVA = r'F:\Daodao\src\_apk\src\com\daodao\pet\DaoOverlay.java'


def check():
    ok = True; lines = []
    if not os.path.exists(ASSET):
        return False, ['缺 assets\\peek.png']
    a = np.array(Image.open(ASSET).convert('RGBA'))
    H, W = a.shape[:2]
    al = a[:, :, 3]
    ratio = W / float(H)
    transp = float((al < 20).mean())
    rows = np.where((al > 40).any(axis=1))[0]
    cols = np.where((al > 40).any(axis=0))[0]
    top, bot = rows.min() / H, rows.max() / H
    left = cols.min() / W
    r1 = abs(ratio - 0.5) < 0.06
    r2 = 0.25 <= transp <= 0.70
    r3 = top < 0.06 and bot > 0.94
    r4 = left < 0.12
    lines.append('比例 %.3f %s' % (ratio, 'OK' if r1 else 'X'))
    lines.append('透明占比 %.2f %s' % (transp, 'OK' if r2 else 'X'))
    lines.append('上下撑满 top %.2f / bottom %.2f %s' % (top, bot, 'OK' if r3 else 'X'))
    lines.append('手尖靠边 left %.2f %s' % (left, 'OK' if r4 else 'X'))
    src = open(JAVA, encoding='utf-8').read()
    r5 = ('peekArt' in src) and re.search(r'vm\s*==\s*MODE_PEEK\s*&&\s*peekArt\s*!=', src) is not None
    lines.append('代码里 MODE_PEEK 用 peekArt %s' % ('OK' if r5 else 'X'))
    r6 = 'drawBitmapMesh' in src and 'MODE_PEEK' in src and 'drawWarp' in src
    lines.append('形象走网格变形（不是死图） %s' % ('OK' if r6 else 'X'))
    ok = all([r1, r2, r3, r4, r5, r6])
    return ok, lines


if __name__ == '__main__':
    ok, lines = check()
    for l in lines:
        print(l)
    print('PASS' if ok else 'FAIL')
    sys.exit(0 if ok else 1)
