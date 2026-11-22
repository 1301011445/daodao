# 程序版本：v0.1 | 2026-11-22 | 新建：形象素材品红/边缘残影体检（Q-083 量化）
"""扫 PNG 的品红残影与半透明脏边，给 Q-083 一个可复跑的数。

判据：
 P1 品红像素占比 == 0（R>140 且 B>140 且 G<min(R,B)*0.65 且 alpha>0）
 P2 alpha 边带（0<a<255）里品红像素 == 0
 P3 全透明像素颜色必须已归零（a==0 但 RGB 仍亮 → 某些渲染器会漏色）
 P4 半透明脏边占 alpha 边带比 <= 2%
用法：python 评审.py <文件或目录>...
"""
import sys, os, io, numpy as np
from PIL import Image

def scan(p):
    im = Image.open(p)
    if im.mode not in ('RGBA', 'LA'):
        im = im.convert('RGBA')
    a = np.array(im).astype(np.int16)
    if a.ndim != 3:
        return None
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    al = a[..., 3] if a.shape[2] == 4 else np.full(r.shape, 255, np.int16)
    vis = al > 0
    mn = np.minimum(r, b)
    mag = vis & (r > 140) & (b > 140) & (g < mn * 0.65)
    band = (al > 0) & (al < 255)
    mag_band = mag & band
    zero_rgb_bright = (~vis) & ((r + g + b) / 3 > 40)
    total = vis.sum() or 1
    bandn = band.sum() or 1
    return dict(file=os.path.basename(p), w=im.size[0], h=im.size[1],
                mag=int(mag.sum()), mag_pct=round(mag.sum() / total * 100, 3),
                band=int(band.sum()), mag_band=int(mag_band.sum()),
                band_pct=round(band.sum() / total * 100, 2),
                zero_bright=int(zero_rgb_bright.sum()))

def judge(rows):
    p1 = all(r['mag'] == 0 for r in rows)
    p2 = all(r['mag_band'] == 0 for r in rows)
    p3 = all(r['zero_bright'] == 0 for r in rows)
    p4 = all(r['mag_band'] / max(r['band'], 1) * 100 <= 2 for r in rows)
    return [('P1 品红像素=0', p1), ('P2 边带品红=0', p2), ('P3 全透明处RGB归零', p3), ('P4 边带脏点<=2%', p4)]

def frame_audit(folder):
    """A9 评审：对 exe 自检出的渲染帧打分（表情有没有真差异、动作有没有真幅度）。"""
    import glob
    def load(pat):
        fs = sorted(glob.glob(os.path.join(folder, pat)))
        return fs
    def body_box(p):
        im = Image.open(p).convert('RGBA')
        a = np.array(im)
        mask = a[..., 3] > 8
        ys, xs = np.where(mask)
        if not len(ys):
            return None
        return (xs.min(), ys.min(), xs.max(), ys.max(), mask.sum())
    print('== A9 渲染帧评审 ==')
    faces = load('selfcheck_face_*.png')
    walks = load('selfcheck_walk8_*.png')
    talks = load('selfcheck_talk*.png')
    res = []
    if len(faces) >= 3:
        ims = [np.array(Image.open(f).convert('L').resize((160, 240))).astype(np.int16) for f in faces]
        diffs = []
        for i in range(len(ims)):
            for j in range(i + 1, len(ims)):
                diffs.append(np.abs(ims[i] - ims[j]).mean())
        mx, avg = max(diffs), sum(diffs) / len(diffs)
        print('  表情帧 %d 张，最大互差 %.1f 灰度级，平均 %.1f' % (len(faces), mx, avg))
        res.append(('A1 表情确有差异(最大互差>=8)', mx >= 8))
        res.append(('A2 表情不是同一张(平均互差>=3)', avg >= 3))
    else:
        print('  表情帧不足 3 张，跳过')
    if len(walks) >= 4:
        # 帧全画布不透明（带场景），不能用 alpha 量身体；改用「相对中位帧的差分」量动作。
        g = [np.array(Image.open(f).convert('L')).astype(np.int16) for f in walks]
        med = np.median(np.stack(g), axis=0)
        H, W = med.shape
        spans = []
        for gi in g:
            d = np.abs(gi - med) > 12
            sub = d[int(H * 0.55):, :]
            ys, xs = np.where(sub)
            spans.append((ys.max() - ys.min(), xs.max() - xs.min()) if len(ys) else (0, 0))
        vmax = max(s[0] for s in spans); hmax = max(s[1] for s in spans)
        head = []
        for gi in g:
            d = (np.abs(gi - med) > 12)[:int(H * 0.2), :]
            head.append(d.sum() / max(d.size, 1) * 100)
        print('  走路帧 %d 张：下半身差异纵向跨度 %d px、横向跨度 %d px；头顶带变化占比最大 %.2f%%'
              % (len(g), vmax, hmax, max(head)))
        res.append(('A3 抬腿幅度>=20px', vmax >= 20))
        res.append(('A4 步态横向跨度>=20px', hmax >= 20))
        res.append(('A5 头顶带不乱晃(<=5%)', max(head) <= 5))
    else:
        print('  走路帧不足 4 张，跳过')
    if len(talks) >= 3:
        print('  说话帧 %d 张（口型层见 口型判据检查.py）' % len(talks))
    for name, ok in res:
        print(('  PASS ' if ok else '  FAIL ') + name)
    print('A9|frames=%d|%s' % (len(faces) + len(walks) + len(talks), 'PASS' if all(o for _, o in res) else 'FAIL'))
    return 0 if all(o for _, o in res) else 1


def main(paths):
    if paths and paths[0] == '--frames':
        return frame_audit(paths[1])
    files = []
    for p in paths:
        if os.path.isdir(p):
            for root, _, fs in os.walk(p):
                files += [os.path.join(root, f) for f in fs if f.lower().endswith('.png')]
        elif p.lower().endswith('.png'):
            files.append(p)
    if not files:
        sys.exit('没有 png')
    rows = [r for r in (scan(f) for f in files) if r]
    bad = [r for r in rows if r['mag'] or r['mag_band'] or r['zero_bright']
           or r['mag_band'] / max(r['band'], 1) * 100 > 2]
    print('扫了 %d 张，有问题 %d 张' % (len(rows), len(bad)))
    for r in sorted(bad, key=lambda x: -x['mag'])[:12]:
        print('  %-22s %dx%d 品红=%d(%.3f%%) 边带=%d 边带品红=%d 透明亮=%d'
              % (r['file'], r['w'], r['h'], r['mag'], r['mag_pct'], r['band'], r['mag_band'], r['zero_bright']))
    res = judge(rows)
    for name, ok in res:
        print(('  PASS ' if ok else '  FAIL ') + name)
    print('IMGCHECK|n=%d|bad=%d|%s' % (len(rows), len(bad), 'PASS' if all(o for _, o in res) else 'FAIL'))
    return 0 if all(o for _, o in res) else 1

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
