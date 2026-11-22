# 程序版本：v0.1 | 2026-11-22 | 一次性：看残余品红是边带残留还是画稿本来就有
import numpy as np, os
from PIL import Image

BD = r'F:\Daodao\src\桌面分身\_bundle'

def edge_dist(al):
    t = (al == 0)
    d = np.where(t, 0, 10 ** 6)
    for _ in range(6):
        d = np.minimum(d, np.minimum(np.minimum(np.roll(d, 1, 0), np.roll(d, -1, 0)),
                                     np.minimum(np.roll(d, 1, 1), np.roll(d, -1, 1))) + 1)
    return d

for f in ['expr_10_angry.png', 'expr_4_happy.png', 'expr_5_happy.png']:
    im = Image.open(os.path.join(BD, f)).convert('RGBA')
    a = np.array(im).astype(np.int16)
    r, g, b, al = a[..., 0], a[..., 1], a[..., 2], a[..., 3]
    mag = (r > 110) & (b > 110) & (g < np.minimum(r, b) * 0.72) & (al > 0)
    d = edge_dist(al)
    print(f, '品红', int(mag.sum()), '距透明<=2px', int((mag & (d <= 2)).sum()),
          '内部', int((mag & (d > 2)).sum()))
    ys, xs = np.where(mag)
    if len(ys):
        print('   范围 x', xs.min(), xs.max(), 'y', ys.min(), ys.max(),
              '均色', a[mag][:, :3].mean(axis=0).round(0))
