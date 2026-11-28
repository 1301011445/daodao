# -*- coding: utf-8 -*-
# 程序版本：v0.1 | 2026-11-28 | 坐骑换皮：大模型重绘 ridef 换成白色独角兽，抠白底+去白边+统一裁切入库
import io, os, sys, urllib.request
import numpy as np
from PIL import Image, ImageDraw

OUT = r'F:\Daodao\src\桌面分身\_bundle'
RAW = r'F:\Daodao\tools\形象\坐骑\_raw'
os.makedirs(RAW, exist_ok=True)

URLS = {
    0: 'https://aka.doubaocdn.com/s/31Ix9Ucxv3',
    1: 'https://aka.doubaocdn.com/s/wsQg5DGRKf',
    2: 'https://aka.doubaocdn.com/s/iX5JOY5q7X',
    3: 'https://aka.doubaocdn.com/s/AI5wBtBEbw',
    4: 'https://aka.doubaocdn.com/s/ZoUQ9ZK6YX',
    5: 'https://aka.doubaocdn.com/s/LqjLhj8Lj9',
    6: 'https://aka.doubaocdn.com/s/EurOzWeIpr',
    7: 'https://aka.doubaocdn.com/s/IpR9dBxV7L',
    8: 'https://aka.doubaocdn.com/s/szxVGXDmjN',
    9: 'https://aka.doubaocdn.com/s/zY7h3wQRLd',
    10: 'https://aka.doubaocdn.com/s/LE6VjU8lK8',
    11: 'https://aka.doubaocdn.com/s/wqgaUTydAg',
    12: 'https://aka.doubaocdn.com/s/x6D1U9UP9V',
    13: 'https://aka.doubaocdn.com/s/i0laAswaWe',
}


def download():
    for sp, u in URLS.items():
        p = os.path.join(RAW, 'ridef_%d_raw.png' % sp)
        if os.path.exists(p) and os.path.getsize(p) > 1000:
            continue
        urllib.request.urlretrieve(u, p)
        print('dl', sp, os.path.getsize(p))


def knock_white(im, tol=232):
    """扣白底：把「亮到接近白」的区域整体连通找出来，只清掉连着画布边的那几块，
    人物/独角兽内部的白色（白衣、白裙、白鬃）因为不连边会保留。
    2026-11-28：第一批用四边泛洪漏了两样东西——腿间被围住的灰影、蹄下的浅灰地影，
    渲出来是一块块发白的补丁，这里改成连通域标记，边上一律清、内部亮的保留。"""
    from scipy import ndimage
    im = im.convert('RGBA')
    a = np.asarray(im).astype(np.uint16)
    bright = a[:, :, :3].min(axis=2) >= tol
    lab, n = ndimage.label(bright)
    # 与画布边相邻的连通块都算背景
    border = set(lab[0, :].tolist()) | set(lab[-1, :].tolist()) | set(lab[:, 0].tolist()) | set(lab[:, -1].tolist())
    border.discard(0)
    bg = np.isin(lab, list(border))
    # 2026-11-28 二修：蹄子之间的地面白/灰影不连边，泛洪与连边判定都碰不到，
    # 于是按「亮且成片、且落在画面下部」单独清掉（白马的毛是亮的，但成片的高光是包在
    # 身体轮廓里的小块，不会满足 area 与位置两个条件）
    h, w = bright.shape
    for i in range(1, n + 1):
        if i in border:
            continue
        ys, xs = np.where(lab == i)
        if ys.size < 3000:
            continue
        v = a[:, :, :3][ys, xs].min(axis=1)
        # 地面留下的白滩：成片很大、极亮（10 分位也 ≥245）、且整块都压在画面下三分之一
        if ys.mean() > h * 0.72 and np.percentile(v, 10) >= 245:
            bg |= (lab == i)
    # 主体往里收 1px，把边缘那圈半白也剃掉，不留灰圈
    solid = ~bg
    solid = ndimage.binary_erosion(solid, iterations=1)
    out = a.astype(np.uint8)
    out[:, :, 3] = np.where(solid, 255, 0)
    out[~solid, :3] = 0
    return Image.fromarray(out, 'RGBA')


def defringe(im):
    a = np.asarray(im).astype(np.float32)
    al = a[:, :, 3:4] / 255.0
    rgb = a[:, :, :3]
    # α<50 的毛边直接清掉；α≥50 反解白底混色
    soft = (a[:, :, 3:4] >= 50) & (a[:, :, 3:4] < 255)
    back = 255.0 * (1.0 - al)
    inv = np.where(soft, np.clip((rgb - back) / np.maximum(al, 1e-3), 0, 255), rgb)
    a[:, :, :3] = inv
    a[:, :, 3:4] = np.where(a[:, :, 3:4] < 50, 0, a[:, :, 3:4])
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), 'RGBA')


def fit(im, target_h=1000, pad=3):
    bb = im.getchannel('A').point(lambda v: 255 if v >= 8 else 0).getbbox()
    im = im.crop(bb)
    k = target_h / float(im.height)
    im = im.resize((max(2, int(im.width * k)), target_h), Image.LANCZOS)
    # 八张统一：底边留 1px、左右居中，保证渲染时蹄子都落在同一条地线上
    canvas = Image.new('RGBA', (im.width + pad * 2, im.height + 1), (0, 0, 0, 0))
    canvas.alpha_composite(im, (pad, 0))
    return canvas


def main():
    download()
    for sp in sorted(URLS):
        src = os.path.join(RAW, 'ridef_%d_raw.png' % sp)
        im = Image.open(src)
        im = knock_white(im)
        im = defringe(im)
        im = fit(im)
        dst = os.path.join(OUT, 'ridef_%d.png' % sp)
        im.save(dst)
        print('sp%-2d %s' % (sp, im.size))


if __name__ == '__main__':
    main()
