# -*- coding: utf-8 -*-
"""对比点击后的连续帧（改前/改后）：按洋红键色抠出人物→浅灰底，出拼图 + 并排 GIF。"""
import glob, os
import numpy as np
from PIL import Image

KEY = np.array([255, 0, 255], dtype=np.int16)
B = r"F:\Daodao\_diag_look\抖动_改前"
A = r"F:\Daodao\_diag_look\抖动_改后"

def seq(d, pre="_shake_f"):
    fs = sorted([f for f in glob.glob(os.path.join(d, pre + "*.png"))
                 if os.path.basename(f).split(pre)[1][:2].isdigit()],
                key=lambda p: int(os.path.basename(p).split(pre)[1][:2]))
    return [Image.open(f).convert("RGB") for f in fs]

def clean(im):
    a = np.asarray(im, dtype=np.int16)
    m = (np.abs(a - KEY).sum(axis=2) < 24)
    out = np.asarray(im).copy()
    out[m] = (246, 248, 250)
    return Image.fromarray(out)

old, new = seq(B), seq(A)
n = min(len(old), len(new))
imgs_o = [clean(i) for i in old[:n]]
imgs_n = [clean(i) for i in new[:n]]

# 人物在画面里的公共范围
bbox = None
for im in imgs_n + imgs_o:
    a = np.asarray(im, dtype=np.int16)
    m = ~(np.abs(a - KEY).sum(axis=2) < 24)
    ys, xs = np.nonzero(m)
    b = (xs.min(), ys.min(), xs.max(), ys.max())
    bbox = b if bbox is None else (min(bbox[0], b[0]), min(bbox[1], b[1]),
                                   max(bbox[2], b[2]), max(bbox[3], b[3]))
pad = 6
box = (90, 0, 290, 205)   # 人物在画布正中，取中间 200px 一竖条看就行
cw, ch = box[2] - box[0], box[3] - box[1]
print("人物范围", bbox, "裁切", box)

cols = 6
sheet = Image.new("RGB", (cw * cols, ch * 2 + 18), (255, 255, 255))
for c in range(cols):
    idx = min(c * 4, n - 1)
    sheet.paste(imgs_o[idx].crop(box), (c * cw, 0))
    sheet.paste(imgs_n[idx].crop(box), (c * cw, ch + 18))
sheet.save(r"F:\Daodao\_diag_look\抖动_改前后对比.png")
print("拼图 -> 抖动_改前后对比.png（上排改前 / 下排改后）")

pairs = []
for i in range(n):
    a = imgs_o[i].crop(box); b = imgs_n[i].crop(box)
    fr = Image.new("RGB", (cw * 2 + 10, ch), (255, 255, 255))
    fr.paste(a, (0, 0)); fr.paste(b, (cw + 10, 0))
    pairs.append(fr)
pairs[0].save(r"F:\Daodao\_diag_look\抖动_改前后.gif", save_all=True, append_images=pairs[1:],
              duration=33, loop=0)
print("GIF -> 抖动_改前后.gif（左改前 右改后）")
