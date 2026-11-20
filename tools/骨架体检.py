# -*- coding: utf-8 -*-
"""骨架体检：从头顶点到脚底量形象比例，判 A1（头身比 6.5–8.0）

做法（全图可复现，不做语义猜测）：
 1) 去背景：与四角平均色差 > 阈值即判为主体像素
 2) 取主体竖直跨度 = 全高（头顶点→脚底最低点）
 3) 逐行量主体横向宽度，画宽度曲线
 4) 宽度曲线在最上面 35% 内找「颈部极细点」：该行为局部最小且宽度 ≤ 最大宽度的 45%
    头高 = 顶→颈行；头身比 = 全高 / 头高
 5) 肩宽 = 颈下 12% 跨度内的最大宽度；腰 = 全高 55%~75% 内最小宽度
 6) 腿长 = 裆部以下（以宽度再次快速收窄后重新变宽的点近似）→ 仅供参考

输出：每张图一行 + JSON。判据：A1 头身比 6.5–8.0（PASS/FAIL）
局限：剪影法对深色头发与背景贴近、宽松长裙会低估，值只作横向对比，不代替人眼。
"""
import io, json, os, sys
import numpy as np
from PIL import Image


def load(path, max_side=900):
    im = Image.open(path).convert('RGB')
    if max(im.size) > max_side:
        im.thumbnail((max_side, max_side), Image.LANCZOS)
    return np.asarray(im).astype(np.float32)


def subject_mask(a):
    h, w, _ = a.shape
    k = max(4, min(h, w) // 20)
    corners = np.concatenate([a[:k, :k].reshape(-1, 3), a[:k, -k:].reshape(-1, 3),
                              a[-k:, :k].reshape(-1, 3), a[-k:, -k:].reshape(-1, 3)])
    bg = np.median(corners, axis=0)
    d = np.sqrt(((a - bg) ** 2).sum(axis=2))
    return d > 28.0


def measure(path):
    a = load(path)
    m = subject_mask(a)
    h, w = m.shape
    rows = np.where(m.any(axis=1))[0]
    if rows.size < 10:
        return dict(file=os.path.basename(path), error='未检出主体')
    top, bot = int(rows[0]), int(rows[-1])
    full = bot - top + 1
    widths = np.array([int(m[y].sum()) for y in range(h)])
    seg = widths[top:bot + 1]
    wmax = int(seg.max())
    # 头宽：头顶往下 20% 内的最大宽度（近似颧骨宽，长发会略微高估）
    hw_zone = widths[top:top + max(3, int(full * 0.20))]
    head_w = int(hw_zone.max())
    # 头高：人体头高约为头宽 1.25–1.40 倍，取中值 1.32（比"找颈部"稳健，长发/高领不会崩）
    head_h = max(1, int(round(head_w * 1.32)))
    ratio = full / head_h
    neck_y = top + head_h
    # 肩宽：颈线以下 10%~35% 区间的最大宽度
    s0 = neck_y + int(full * 0.02)
    s1 = top + int(full * 0.55)
    shoulder = int(widths[s0:s1 + 1].max())
    # 腰
    w0, w1 = top + int(full * 0.55), top + int(full * 0.75)
    waist = int(widths[w0:w1 + 1].min())
    # 腿：裆部以下宽度最大处（两腿分开会出现宽度回升）
    hip0 = top + int(full * 0.60)
    legs_zone = widths[hip0:bot + 1]
    leg_open = int(np.argmax(legs_zone)) + hip0 if legs_zone.size else hip0
    leg_len = bot - leg_open
    return dict(
        file=os.path.basename(path), size=[int(w), int(h)],
        full_px=full, head_px=head_h,
        head_body_ratio=round(ratio, 2),
        shoulder_over_head=round(shoulder / head_h, 2),
        waist_px=waist, leg_over_full=round(leg_len / full, 3),
        A1=(6.5 <= ratio <= 8.0),
    )


if __name__ == '__main__':
    files = sys.argv[1:] or [f for f in os.listdir('.') if f.lower().endswith(('.jpg', '.png'))]
    rows = []
    for f in files:
        try:
            rows.append(measure(f))
        except Exception as e:
            rows.append(dict(file=os.path.basename(f), error=str(e)))
    print('%-16s %8s %8s %10s %10s %10s  %s' % ('文件', '全高px', '头高px', '头身比', '肩宽/头', '腿/全高', 'A1'))
    for r in rows:
        if 'error' in r:
            print('%-16s ERROR %s' % (r['file'], r['error'])); continue
        print('%-16s %8d %8d %10.2f %10.2f %10.3f  %s' % (
            r['file'][:16], r['full_px'], r['head_px'], r['head_body_ratio'],
            r['shoulder_over_head'], r['leg_over_full'], 'PASS' if r['A1'] else 'FAIL'))
    io.open('骨架体检.json', 'w', encoding='utf-8').write(
        json.dumps(dict(pass_band='头身比 6.5-8.0', rows=rows), ensure_ascii=False, indent=2))
    print('已写 骨架体检.json')
