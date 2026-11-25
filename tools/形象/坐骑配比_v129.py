# -*- coding: utf-8 -*-
"""坐骑 × 人物 配比测量与预览（不改素材，只算/出图）
输出：
1) 每只立绘的透明包围盒高度占比（看形象大小是否统一）
2) 每只坐骑的"鞍位线"：中间 40% 宽度内不透明像素的加权中线高度（占坐骑高比例，从底部算）
3) 预览图：5 只坐骑各托一次 art0，看脚有没有落在鞍上、比例是否协调
"""
import os
import json
import numpy as np
from PIL import Image

A = r'F:\Daodao\src\_apk\assets'
OUT = r'F:\Daodao\形象\坐骑\_配比预览.png'
RPT = r'F:\Daodao\形象\坐骑\_配比报告.json'

arts = sorted([f for f in os.listdir(A) if f.startswith('stand_') and f.endswith('.png')],
              key=lambda s: int(s.split('_')[1].split('.')[0]))
mounts = ['mount_cloud.png', 'mount_horse.png', 'mount_sword.png', 'mount_deer.png', 'mount_crane.png']
names = ['祥云', '木马', '飞剑', '小鹿', '纸鹤']

rep = {'stand': {}, 'mount': {}}

print('== 立绘包围盒（占画布高）==')
for f in arts:
    im = Image.open(os.path.join(A, f)).convert('RGBA')
    a = np.array(im)[..., 3] > 40
    ys, xs = np.where(a)
    hh = (ys.max() - ys.min() + 1) / im.height
    ww = (xs.max() - xs.min() + 1) / im.width
    bottom = 1 - (ys.max() + 1) / im.height
    rep['stand'][f] = {'canvas': im.size, 'h_ratio': round(float(hh), 3),
                       'w_ratio': round(float(ww), 3), 'bottom_gap': round(float(bottom), 3)}
    print(f'{f:12s} 画布{im.size} 高占比={hh:.3f} 宽占比={ww:.3f} 底边留白={bottom:.3f}')

print('\n== 坐骑鞍位线（中间 40% 宽度）==')
for f, nm in zip(mounts, names):
    im = Image.open(os.path.join(A, f)).convert('RGBA')
    a = np.array(im)[..., 3] > 40
    h, w = a.shape
    x0, x1 = int(w * 0.30), int(w * 0.70)
    band = a[:, x0:x1]
    ys, xs = np.where(band)
    top = ys.min() / h       # 中间带最上面的不透明像素（人物该踩到这附近才不会穿模）
    mid = np.median(ys) / h
    bottom = ys.max() / h
    rep['mount'][nm] = {'file': f, 'size': im.size,
                        'top_ratio': round(float(top), 3),
                        'median_ratio': round(float(mid), 3),
                        'alpha_cols': int(a.shape[1] > 0)}
    print(f'{nm:4s} {im.size} 中间带顶部={top:.3f} 中线={mid:.3f}')

json.dump(rep, open(RPT, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print('\n报告 ->', RPT)

# ---- 预览 ----
VW, VH = 480, 640          # 模拟一块悬浮窗画布
ART = 'stand_0.png'        # 先用主少女
art = Image.open(os.path.join(A, ART)).convert('RGBA')
aa = np.array(art)[..., 3] > 40
ys, xs = np.where(aa)
art = art.crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))

pads = []
for f, nm in zip(mounts, names):
    m = Image.open(os.path.join(A, f)).convert('RGBA')
    ap = np.array(m)[..., 3] > 40
    ys2, xs2 = np.where(ap)
    m = m.crop((xs2.min(), ys2.min(), xs2.max() + 1, ys2.max() + 1))

    # 人物：高度占画布 0.72，脚落在鞍位
    ch = int(VH * 0.72)
    cw = int(art.width * ch / art.height)
    cimg = art.resize((cw, ch), Image.LANCZOS)

    # 坐骑：宽度占画布 0.92，高度按比例
    mw = int(VW * 0.92)
    mh = int(m.height * mw / m.width)
    mimg = m.resize((mw, mh), Image.LANCZOS)

    # 鞍位：坐骑中间带顶部的 12% 往下（踩在背脊上，不穿模也不悬空）
    top_ratio = rep['mount'][nm]['top_ratio']
    rise = int(mh * (1 - top_ratio) * 0.72)

    canvas = Image.new('RGBA', (VW, VH), (24, 28, 38, 255))
    # 坐骑贴底、水平居中
    canvas.alpha_composite(mimg, ((VW - mw) // 2, VH - mh))
    # 人物：水平居中，脚落在 底 - rise
    canvas.alpha_composite(cimg, ((VW - cw) // 2, VH - rise - ch))
    pads.append((nm, canvas, mh, rise, mw))

sheet = Image.new('RGBA', (VW * len(pads) + 10 * (len(pads) - 1), VH + 0), (10, 12, 16, 255))
for i, (nm, im, mh, rise, mw) in enumerate(pads):
    sheet.alpha_composite(im, (i * (VW + 10), 0))
    print(f'{nm}: 坐骑 {mw}x{mh} 鞍位抬升 {rise}px 人物高 {int(VH*0.72)}px')
sheet.save(OUT)
print('预览 ->', OUT, sheet.size)
