# 程序版本：v0.3 | 2026-11-22 | _bundle 去紫边最后一刀：离透明 2px 内的粉边把绿抬到 min(R,B)
import os, numpy as np
from PIL import Image

BD = r'F:\Daodao\src\桌面分身\_bundle'
files = [f for f in os.listdir(BD) if f.lower().endswith('.png')]
changed = fixed = 0
for f in files:
    p = os.path.join(BD, f)
    im = Image.open(p)
    if im.mode not in ('RGBA', 'LA'):
        im = im.convert('RGBA')
    a = np.array(im).astype(np.int16)
    if a.ndim != 3 or a.shape[2] < 4:
        continue
    r, g, b, al = a[..., 0], a[..., 1], a[..., 2], a[..., 3]
    t = (al == 0)
    d = np.where(t, 0, 10 ** 6)
    for _ in range(2):
        d = np.minimum(d, np.minimum(np.minimum(np.roll(d, 1, 0), np.roll(d, -1, 0)),
                                     np.minimum(np.roll(d, 1, 1), np.roll(d, -1, 1))) + 1)
    near = (al > 0) & (d <= 2)
    pink = (r > 110) & (b > 110) & (g < np.minimum(r, b) * 0.85)
    fx = near & pink
    n = int(fx.sum())
    if not n:
        continue
    a[fx, 1] = np.minimum(r[fx], b[fx])
    Image.fromarray(a.astype(np.uint8), 'RGBA').save(p)
    changed += 1; fixed += n

print('处理 %d 张，改过 %d 张；2px 粉边去紫 %d px' % (len(files), changed, fixed))
