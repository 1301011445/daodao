# 程序版本：v0.2 | 2026-11-22 | _bundle 去紫边改全边带规则（0<alpha<255 且偏品红 → 提绿）
import os, shutil, numpy as np
from PIL import Image

BD = r'F:\Daodao\src\桌面分身\_bundle'
files = [f for f in os.listdir(BD) if f.lower().endswith('.png')]
changed = zeroed = fixed = 0
for f in files:
    p = os.path.join(BD, f)
    im = Image.open(p)
    if im.mode not in ('RGBA', 'LA'):
        im = im.convert('RGBA')
    a = np.array(im).astype(np.int16)
    if a.ndim != 3 or a.shape[2] < 4:
        continue
    r, g, b, al = a[..., 0], a[..., 1], a[..., 2], a[..., 3]
    lowt = al < 6
    band = (al >= 6) & (al < 255)
    mag = (r > 110) & (b > 110) & (g < np.minimum(r, b) * 0.72)
    n_zero = int((lowt & ((r + g + b) > 60)).sum())
    n_fix = int((band & mag).sum())
    if not n_zero and not n_fix:
        continue
    a[lowt, 0:3] = 0
    fx = band & mag
    a[fx, 1] = ((r[fx] + b[fx]) / 2).clip(0, 255)
    Image.fromarray(a.astype(np.uint8), 'RGBA').save(p)
    changed += 1; zeroed += n_zero; fixed += n_fix

print('处理 %d 张，改过 %d 张；透明处归零 %d px，边带去紫 %d px' % (len(files), changed, zeroed, fixed))
