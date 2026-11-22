# 程序版本：v0.1 | 2026-11-22 | 一次性：桌面 _bundle 立绘去紫边（与手机 SPR 同一套规则）
"""把 _bundle 里的 PNG 按手机端 SPR 的规则清一遍：alpha<6 的 RGB 归零；6<=alpha<40 且偏紫提绿。
先整目录备份，再逐张写回，最后给出改了多少张/多少像素。
"""
import os, shutil, numpy as np
from PIL import Image

BD = r'F:\Daodao\src\桌面分身\_bundle'
BK = r'F:\Daodao\_bak\_bundle_20261122_despill'
if not os.path.isdir(BK):
    shutil.copytree(BD, BK)
    print('备份 ->', BK)

files = [f for f in os.listdir(BD) if f.lower().endswith('.png')]
changed = 0
zeroed = 0
fixed = 0
for f in files:
    p = os.path.join(BD, f)
    try:
        im = Image.open(p)
    except Exception as e:
        print('跳过', f, e); continue
    if im.mode not in ('RGBA', 'LA'):
        im = im.convert('RGBA')
    a = np.array(im).astype(np.int16)
    if a.ndim != 3 or a.shape[2] < 4:
        continue
    r, g, b, al = a[..., 0], a[..., 1], a[..., 2], a[..., 3]
    lowt = al < 6
    low = (al >= 6) & (al < 40)
    mag = (r > 120) & (b > 120) & (g < np.minimum(r, b) * 0.7)
    n_zero = int((lowt & ((r + g + b) > 60)).sum())
    n_fix = int((low & mag).sum())
    if not n_zero and not n_fix:
        continue
    a[lowt, 0:3] = 0
    fx = low & mag
    a[fx, 1] = ((r[fx] + b[fx]) / 2).clip(0, 255)
    Image.fromarray(a.astype(np.uint8), im.mode).save(p)
    changed += 1
    zeroed += n_zero
    fixed += n_fix

print('处理 %d 张，改过 %d 张；透明处归零 %d px，淡边去紫 %d px' % (len(files), changed, zeroed, fixed))
