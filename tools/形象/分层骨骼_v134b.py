# -*- coding: utf-8 -*-
"""v134b 分层骨骼（A 字骨架立绘）：手臂/腿与身体分离，切出来就能各自转
切法：手臂 = 外侧 38% 宽 + 肩线以下 42% 高；腿 = 髋以下按中线分左右。
"""
import math
import os
import subprocess

import numpy as np
from PIL import Image, ImageFilter

SRC = r'F:\Daodao\形象\骨骼'
A = r'F:\Daodao\src\_apk\assets'
OUT = r'F:\Daodao\形象\_分层骨骼预览2.png'
os.makedirs(SRC, exist_ok=True)
P = os.path.join(SRC, '骨骼_0_原.png')
if not os.path.exists(P) or os.path.getsize(P) < 20000:
    subprocess.run(['C:\\Windows\\System32\\curl.exe', '-sL', 'https://aka.doubaocdn.com/s/Ftr6irwBte', '-o', P],
                   check=False)


def white_off(im):
    a = np.array(im.convert('RGBA')).astype(np.int16)
    al = a[..., 3]
    rgb = a[..., :3]
    w = (rgb[..., 0] > 238) & (rgb[..., 1] > 238) & (rgb[..., 2] > 238)
    edge = np.zeros(al.shape, bool)
    ew, eh = max(1, int(a.shape[1] * 0.05)), max(1, int(a.shape[0] * 0.05))
    edge[:, :ew] = True; edge[:, -ew:] = True; edge[:eh] = True; edge[-eh:] = True
    kill = (al > 0) & ((w & edge) | (w & (al < 205)))
    rgb[kill] = 0; al[kill] = 0; al[al < 12] = 0
    return Image.fromarray(np.dstack([np.clip(rgb, 0, 255), al]).astype(np.uint8), 'RGBA')


def bbox(im):
    a = np.array(im)[..., 3] > 40
    ys, xs = np.where(a)
    return xs.min(), ys.min(), xs.max() + 1, ys.max() + 1


im = white_off(Image.open(P))
im = im.crop(bbox(im))
im = im.resize((480, int(im.height * 480 / im.width)), Image.LANCZOS)
a = np.array(im)
h, w = a.shape[:2]
sil = a[..., 3] > 60

# 肩线 / 髋线（按身高比例）
sy, hy = int(h * 0.26), int(h * 0.56)
m = {'armR': np.zeros((h, w), np.float32), 'armL': np.zeros((h, w), np.float32),
     'legR': np.zeros((h, w), np.float32), 'legL': np.zeros((h, w), np.float32)}
for y in range(sy, hy):
    xs = np.where(sil[y])[0]
    if not xs.size:
        continue
    x0, x1 = xs.min(), xs.max()
    span = x1 - x0
    cutR = x0 + span * 0.62          # 右边到手的那一段
    cutL = x0 + span * 0.38
    fade = max(3, int(span * 0.06))
    for x in range(int(cutR), x1 + 1):
        if sil[y, x]:
            m['armR'][y, x] = min(1.0, (x - cutR) / fade + 0.35)
    for x in range(x0, int(cutL) + 1):
        if sil[y, x]:
            m['armL'][y, x] = min(1.0, (cutL - x) / fade + 0.35)
# 肩部以上不再切手臂（袖子上端留在躯干上，避免露肩）
for y in range(0, sy):
    m['armR'][y] = 0; m['armL'][y] = 0
# 腿
for y in range(hy, h):
    xs = np.where(sil[y])[0]
    if not xs.size:
        continue
    cx = (xs.min() + xs.max()) / 2 - 0.02 * w
    for x in range(xs.min(), xs.max() + 1):
        if sil[y, x]:
            d = (x - cx) / (0.05 * w)
            if x < cx:
                m['legL'][y, x] = min(1.0, max(0.0, -d))
            else:
                m['legR'][y, x] = min(1.0, max(0.0, d))

cover = np.maximum.reduce(list(m.values()))
base = a.copy()
base[..., 3] = (base[..., 3] * (1 - np.clip(cover, 0, 1) * 0.55)).astype(np.uint8)
base_im = Image.fromarray(base, 'RGBA')
cut = {}
for k, mm in m.items():
    al = (a[..., 3] * np.clip(mm, 0, 1)).astype(np.uint8)
    cut[k] = Image.fromarray(np.dstack([a[..., 0], a[..., 1], a[..., 2], al]).astype(np.uint8), 'RGBA')

J = {'armR': (0.78 * w, 0.30 * h), 'armL': (0.22 * w, 0.30 * h),
     'legR': (0.56 * w, 0.56 * h), 'legL': (0.44 * w, 0.56 * h)}


def render(angs):
    out = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    out.alpha_composite(base_im)
    for k in ('legL', 'legR', 'armL', 'armR'):
        ang = angs.get(k, 0.0)
        if abs(ang) < 0.5:
            out.alpha_composite(cut[k])
        else:
            out.alpha_composite(cut[k].rotate(ang, resample=Image.BICUBIC, center=J[k], fillcolor=(0, 0, 0, 0)))
    return out


TS = [i * 1.6 / 8 for i in range(8)]
MOTIONS = [
    ('挥手', [{'armR': -30 - 45 * math.sin(t * 6.0)} for t in TS]),
    ('走路', [{'legL': 13 * math.sin(t * 11), 'legR': -13 * math.sin(t * 11),
              'armL': -8 * math.sin(t * 11), 'armR': 8 * math.sin(t * 11)} for t in TS]),
    ('跳舞', [{'legL': 9 * math.sin(t * 10), 'legR': -9 * math.sin(t * 10),
              'armL': 30 * math.sin(t * 10), 'armR': -30 * math.sin(t * 10)} for t in TS]),
]
CW, CH = 240, 480
rows = []
for nm, seq in MOTIONS:
    row = Image.new('RGBA', (CW * len(seq) + 6 * (len(seq) - 1), CH), (16, 18, 26, 255))
    for i, angs in enumerate(seq):
        f = render(angs).resize((CW, CH), Image.LANCZOS)
        row.alpha_composite(f, (i * (CW + 6), 0))
    rows.append(row)
sheet = Image.new('RGBA', (rows[0].width, CH * 3 + 12), (10, 12, 18, 255))
for i, r in enumerate(rows):
    sheet.alpha_composite(r, (0, i * (CH + 6)))
sheet.convert('RGB').save(OUT, optimize=True)
print('A 字骨架分层预览 ->', OUT, sheet.size)
