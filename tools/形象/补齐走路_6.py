# -*- coding: utf-8 -*-
"""补齐 6 号蓝发少女的八帧走路表：用分层骨骼在同一张立绘上转腿转臂，不重绘脸。"""
import importlib.util, math, os, sys
from PIL import Image
spec = importlib.util.spec_from_file_location("bone", r"F:\Daodao\tools\形象\分层骨骼_v134.py")
bone = importlib.util.module_from_spec(spec)
sys.argv = ["x"]
try:
    spec.loader.exec_module(bone)
except SystemExit:
    pass

A = r"F:\Daodao\src\_apk\assets"
W, H = 192, 384
src = Image.open(os.path.join(A, "stand_6.png")).convert("RGBA")
if src.size != (W, H):
    src = src.resize((W, H), Image.LANCZOS)
base, cut, _ = bone.build(src)

# 8 帧：迈步相位 0..2π，腿反向摆 13°，臂反向摆 9°，加 2px 上下起伏模拟重心
frames = []
for i in range(8):
    ph = 2 * math.pi * i / 8
    legL = 13 * math.sin(ph)
    legR = -13 * math.sin(ph)
    armL = -8 * math.sin(ph)
    armR = 8 * math.sin(ph)
    out = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    # 整体 2px 上下（重心）
    dy = -2 if i % 4 in (1, 2) else 0
    body = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    body.alpha_composite(base)
    for k, ang in (("legL", legL), ("legR", legR), ("armL", armL), ("armR", armR)):
        if abs(ang) < 0.5:
            body.alpha_composite(cut[k])
        else:
            jx, jy = bone.pivot(k, W, H)
            body.alpha_composite(cut[k].rotate(ang, resample=Image.BICUBIC, center=(jx, jy), fillcolor=(0, 0, 0, 0)))
    out.alpha_composite(body, (0, dy))
    frames.append(out)

sheet = Image.new("RGBA", (W * 8, H), (0, 0, 0, 0))
for i, f in enumerate(frames):
    sheet.paste(f, (i * W, 0), f)
dst = os.path.join(A, "walk8_6.png")
sheet.save(dst)
print("写出", dst, sheet.size)

# 自检：每帧脚部 x 聚类数 + 步幅
import numpy as np
ok = 0
for i, f in enumerate(frames):
    a = np.array(f)[..., 3] > 60
    ys = np.where(a.any(1))[0]
    foot = ys.max() - 6
    xs = np.where(a[foot - 4:foot + 1].any(0))[0]
    if xs.size == 0:
        print(f" 帧{i} 无脚"); continue
    gaps = np.where(np.diff(xs) > 3)[0]
    clusters = 1 + len(gaps)
    print(f" 帧{i}: 脚部 x {xs.min()}~{xs.max()} 聚类={clusters}")
    if clusters >= 2: ok += 1
print(f"SUMMARY 分腿帧 {ok}/8")
