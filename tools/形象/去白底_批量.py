# -*- coding: utf-8 -*-
"""批量去白底：把素材透明区里的纯白（以及半透明区的近白污染）换成"主体平均色"
为什么这样做：透明区 RGB=255 的像素在被缩放/抗锯齿插值时，会把白色混进轮廓 → 手机上的白边/白块。
不追求逐像素精确最近色（电脑上没有 scipy），改用主体平均色填充：
   ① alpha<6 的像素整体清 alpha
   ② al<250 且 min(RGB)>235 的像素 RGB 换成主体平均色
   ③ alpha<6 的像素 RGB 也换成主体平均色（保证插值时吸到的是衣服色，不是白色）
判据 W1: 处理后再数"透明且近白"像素 == 0
用法: 去白底_批量.py <目录或文件...>  [--write]
"""
import os, sys
import numpy as np
from PIL import Image


def fix_one(path, write=False):
    im = Image.open(path).convert('RGBA')
    a = np.array(im).astype(np.float32)
    al, rgb = a[..., 3], a[..., :3]
    solid = al > 250
    body = rgb[solid].mean(axis=0) if solid.any() else np.array([128, 128, 128], np.float32)
    before = int(((al < 10) & (rgb.min(axis=2) > 240)).sum())
    al2 = np.where(al < 6, 0, al)
    whiteish = (al2 < 250) & (rgb.min(axis=2) > 235)
    rgb2 = rgb.copy()
    rgb2[whiteish] = body
    rgb2[al2 < 6] = body          # 透明区一律填主体色，缩放时吸不到白
    out = np.dstack([np.clip(rgb2, 0, 255), al2]).astype(np.uint8)
    after = int(((out[..., 3] < 10) & (out[..., :3].min(axis=2) > 240)).sum())
    if write:
        bak = path + '.bak_white'
        if not os.path.exists(bak):
            os.replace(path, bak) if False else __import__('shutil').copy2(path, bak)
        Image.fromarray(out).save(path, optimize=True)
    return before, after, body


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    write = '--write' in sys.argv
    targets = []
    for p in args:
        if os.path.isdir(p):
            for f in sorted(os.listdir(p)):
                if f.lower().endswith('.png') and ('walk8' in f or 'peek' in f or f.startswith('ball')):
                    targets.append(os.path.join(p, f))
        else:
            targets.append(p)
    fails = 0
    for p in targets:
        before, after, body = fix_one(p, write)
        ok = after == 0
        if not ok:
            fails += 1
        print(f'{os.path.basename(p):24s} 原白像素={before:6d} 处理后={after:4d} 主体色=({body[0]:.0f},{body[1]:.0f},{body[2]:.0f}) {"PASS" if ok else "FAIL"}')
    print(f'SUMMARY 文件 {len(targets)} 个 | 白像素清零 {len(targets)-fails} | 未过 {fails} | 写入={write}')
    return 0 if fails == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
