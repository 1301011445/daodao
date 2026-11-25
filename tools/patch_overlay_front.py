# -*- coding: utf-8 -*-
"""2026-11-25：手机端悬浮窗补「正视图」——站着面向你（stand_*.png），走路仍用八帧侧步。"""
import io, shutil, os, glob

SRC = r"F:\Daodao\src\_apk\_stand_bak"
DST = r"F:\Daodao\src\_apk\assets"
for p in glob.glob(os.path.join(SRC, "stand_*.png")):
    shutil.copy2(p, os.path.join(DST, os.path.basename(p)))
print("stand 拷入", len(glob.glob(os.path.join(DST, "stand_*.png"))), "张")

P = r"F:\Daodao\src\_apk\src\com\daodao\pet\DaoOverlay.java"
src = io.open(P, encoding="utf-8").read()
hits = []

def sub(old, new, tag, must=True):
    global src
    if old not in src:
        hits.append((tag, 0)); return
    src = src.replace(old, new, 1); hits.append((tag, 1))

# 1) 声明 standArt
sub("        private Bitmap peekArt;      // 贴边探头的半身姿态（assets/peek.png）",
    "        private Bitmap peekArt;      // 贴边探头的半身姿态（assets/peek.png）\n"
    "        private Bitmap standArt;     // 正面站姿（assets/stand_<序号>.png）：站着时面向你，不是侧脸",
    "field")

# 2) 加载
sub('            peekArt = loadOpt("peek.png");',
    '            peekArt = loadOpt("peek.png");\n'
    '            // 2026-11-25：原来站着时停在八帧的第 0 帧，那是个侧身迈步的姿势，看着像永远在走路。\n'
    '            // 现在单独加载正面站姿，站着就面向你。\n'
    '            standArt = loadOpt("stand_" + art + ".png");',
    "load")

# 3) 绘制分支：站着（非走路、非贴边）用正面站姿
sub("            } else if (frames != null && fi >= 0 && fi < frames.length) {",
    "            } else if (vm != MODE_PEEK && !walking && standArt != null && !standArt.isRecycled()) {\n"
    "                drawWarp(c, standArt, 0, bob, w, h + bob, tick / 30.0, 0f, false, false, waveAmp, nodAmp);\n"
    "            } else if (frames != null && fi >= 0 && fi < frames.length) {",
    "draw-stand")

io.open(P, "w", encoding="utf-8").write(src)
for tag, ok in hits:
    print(("OK   " if ok else "MISS ") + tag)
