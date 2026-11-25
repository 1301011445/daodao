# -*- coding: utf-8 -*-
"""全部形象素材逐帧居中（治"形象偏到右边、像被裁掉"）
做法：每张 walk8_N.png 的 8 帧里，把轮廓画框中心 x 挪到 96（帧宽 192 正中），
     脚底基线挪到同一水平线，其余保持不动（摆动仍在，只是不再整块偏）。
判据（逐张）：
 C1 画框中心漂移 <=1.0px
 C2 脚底基线漂移 <=1.0px
 C3 步幅（脚底 x 极差）>=6px（没把腿钉死）
 C4 帧宽仍是 192 的整数倍、总宽仍 1536
用法: 形象居中_批量.py <assets目录> [--write]
"""
import os, sys
import numpy as np
from PIL import Image

NF = 8


def frames(path):
    im = Image.open(path).convert('RGBA')
    w = im.width // NF
    return im, [np.array(im.crop((i * w, 0, (i + 1) * w, im.height))).astype(np.float32) for i in range(NF)]


def stats(f):
    a = f[..., 3]
    ys, xs = np.where(a > 20)
    if len(xs) == 0:
        return None
    lo = ys.max() - 3
    return dict(cx=(xs.min() + xs.max()) / 2.0, base=float(ys.max()),
                fx=float(xs[ys >= lo].mean()))


def shift(f, dx, dy):
    a, rgb = f[..., 3], f[..., :3]
    outa, outr = np.zeros_like(a), np.zeros_like(rgb)
    h, w = a.shape
    sx0, sx1, tx0, tx1 = (0, w - dx, dx, w) if dx > 0 else ((-dx, w, 0, w + dx) if dx < 0 else (0, w, 0, w))
    sy0, sy1, ty0, ty1 = (0, h - dy, dy, h) if dy > 0 else ((-dy, h, 0, h + dy) if dy < 0 else (0, h, 0, h))
    outa[ty0:ty1, tx0:tx1] = a[sy0:sy1, sx0:sx1]
    outr[ty0:ty1, tx0:tx1] = rgb[sy0:sy1, sx0:sx1]
    return np.dstack([outr, outa]).astype(np.float32)


def process(path, write=False):
    im, fs = frames(path)
    st = [stats(f) for f in fs]
    if any(s is None for s in st):
        return None
    cx0 = [s['cx'] for s in st]
    base0 = [s['base'] for s in st]
    tgt, tbase = 96.0, max(base0)
    fx = [shift(f, int(round(tgt - s['cx'])), int(round(tbase - s['base']))) for f, s in zip(fs, st)]
    st2 = [stats(f) for f in fx]
    cx1 = [s['cx'] for s in st2]
    base1 = [s['base'] for s in st2]
    stride = max(s['fx'] for s in st2) - min(s['fx'] for s in st2)
    c1 = (max(cx1) - min(cx1)) <= 1.0
    c2 = (max(base1) - min(base1)) <= 1.0
    c3 = stride >= 6.0
    c4 = im.width % NF == 0 and im.width // NF == 192
    if write and not (c1 and c2 and c3 and c4):
        pass
    if write:
        Image.fromarray(np.concatenate(fx, axis=1).astype(np.uint8)).save(path, optimize=True)
    return dict(name=os.path.basename(path), before=max(cx0) - min(cx0), after=max(cx1) - min(cx1),
                base=(max(base1) - min(base1)), stride=stride, ok=all([c1, c2, c3, c4]))


def main():
    d = sys.argv[1]
    write = '--write' in sys.argv
    rows, fails = [], 0
    for f in sorted(os.listdir(d)):
        if not (f.startswith('walk8') and f.endswith('.png')) or 'backup' in f or 'bak' in f:
            continue
        r = process(os.path.join(d, f), write)
        if r is None:
            print(f, 'SKIP 空帧'); continue
        rows.append(r)
        if not r['ok']:
            fails += 1
        print(f"{r['name']:16s} 中心漂移 {r['before']:5.1f}->{r['after']:4.2f}px 基线{r['base']:.0f}px 步幅{r['stride']:.1f}px {'PASS' if r['ok'] else 'FAIL'}")
    print(f'SUMMARY 张数={len(rows)} 未过={fails} 写入={write}')
    return 0 if fails == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
