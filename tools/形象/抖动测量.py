# -*- coding: utf-8 -*-
"""量「点一下道」的抖动：用洋红键色(255,0,255)抠出人物，看逐帧位移。
判据：逐帧 Δ 位移幅值与换向次数；换向多说明是"颤"，单向说明是点头/摆手。
"""
import glob, os, json
import numpy as np
from PIL import Image

KEY = np.array([255, 0, 255], dtype=np.int16)

def load_seq(d, pre):
    fs = sorted([f for f in glob.glob(os.path.join(d, pre + "*.png"))
                 if os.path.basename(f).split(pre)[1][:2].isdigit()],
                key=lambda p: int(os.path.basename(p).split(pre)[1][:2]))
    out = []
    for f in fs:
        a = np.asarray(Image.open(f).convert("RGB"), dtype=np.int16)
        m = ~(np.abs(a - KEY).sum(axis=2) < 24)      # True = 人物像素
        ys, xs = np.nonzero(m)
        out.append(dict(mask=m, cx=xs.mean(), cy=ys.mean(), top=ys.min(), bot=ys.max(),
                        headx=xs[ys < ys.min() + (ys.max() - ys.min()) * 0.25].mean()))
    return out

def report(name, s):
    d_x = np.diff([f["headx"] for f in s])
    d_y = np.diff([f["cy"] for f in s])
    flips_x = int(np.sum(d_x[1:] * d_x[:-1] < 0))
    flips_y = int(np.sum(d_y[1:] * d_y[:-1] < 0))
    amp_x = float(np.abs(d_x).max()); amp_y = float(np.abs(d_y).max())
    rng_x = float(np.max([f["headx"] for f in s]) - np.min([f["headx"] for f in s]))
    rng_y = float(np.max([f["cy"] for f in s]) - np.min([f["cy"] for f in s]))
    print("== %s ==" % name)
    print("  头部横向：逐帧最大位移 %.2fpx，换向 %d/%d，整段行程 %.2fpx" % (amp_x, flips_x, len(d_x) - 1, rng_x))
    print("  整体纵向：逐帧最大位移 %.2fpx，换向 %d/%d，整段行程 %.2fpx" % (amp_y, flips_y, len(d_y) - 1, rng_y))
    return dict(head_dx=round(amp_x, 2), head_flips=flips_x, head_span=round(rng_x, 2),
                body_dy=round(amp_y, 2), body_flips=flips_y, body_span=round(rng_y, 2))

if __name__ == "__main__":
    res = {}
    for tag, d in (("改前", r"F:\Daodao\_diag_look\抖动_改前"), ("改后", r"F:\Daodao\_diag_look\抖动_改后")):
        res[tag + "_点击"] = report(tag + " 点击后(挥手+说话)", load_seq(d, "_shake_f"))
        res[tag + "_待机"] = report(tag + " 平静待机", load_seq(d, "_idle_f"))
    json.dump(res, open(r"F:\Daodao\自我状态\抖动测量.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("写入 自我状态\\抖动测量.json")
