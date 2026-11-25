# -*- coding: utf-8 -*-
"""2026-11-25：手机端悬浮窗收摆幅 + 走路相位与换帧同步。逐条 replace，改完打印命中数。"""
import io, sys

P = r"F:\Daodao\src\_apk\src\com\daodao\pet\DaoOverlay.java"
src = io.open(P, encoding="utf-8").read()
hits = []

def sub(old, new, tag):
    global src
    if old not in src:
        hits.append((tag, 0))
        return
    src = src.replace(old, new, 1)
    hits.append((tag, 1))

# 1) 走路相位跟当前帧号走
sub("                drawWarp(c, frames[fi], 0, bob, w, h + bob, tick / 30.0, walking, false, waveAmp, nodAmp);",
    "                float ph = (float) ((fi / (float) Math.max(1, fN)) * Math.PI * 2.0);\n"
    "                drawWarp(c, frames[fi], 0, bob, w, h + bob, tick / 30.0, ph, walking, false, waveAmp, nodAmp);",
    "walk-phase-call")

sub("                drawWarp(c, peekArt, 0, bob, w, h + bob, tick / 30.0, false, true, 0f, 0f);",
    "                drawWarp(c, peekArt, 0, bob, w, h + bob, tick / 30.0, 0f, false, true, 0f, 0f);",
    "peek-phase-call")

sub("        void drawWarp(Canvas c, Bitmap bm, float left, float top, float w, float h, double t, boolean walk,\n"
    "                boolean peek, float wave, float nod) {",
    "        void drawWarp(Canvas c, Bitmap bm, float left, float top, float w, float h, double t, float phase,\n"
    "                boolean walk, boolean peek, float wave, float nod) {",
    "sig")

sub("            float step = walk ? (float) Math.sin(t * 5.2) : 0f;",
    "            float step = walk ? (float) Math.sin(phase) : 0f;   // 与换帧同频：一轮 8 帧 = 一个步态周期",
    "step")

# 2) 下身摆动收小
sub("                    float dx = 0.013f * w * sway * (float) Math.pow(ny, 1.7f)\n"
    "                             + 0.011f * w * lag * (float) Math.pow(ny, 2.3f);",
    "                    // 2026-11-25：原来 1.3% / 1.1% 身宽的下身摆动叠头发的延迟跟随，连起来就是「东倒西歪」。\n"
    "                    // 站着不动时几乎不该晃，压到 0.5% / 0.45%，只留一点呼吸感。\n"
    "                    float dx = 0.005f * w * sway * (float) Math.pow(ny, 1.7f)\n"
    "                             + 0.0045f * w * lag * (float) Math.pow(ny, 2.3f);",
    "sway")

# 3) 头部侧倾横向位移收小
sub("                        float headShift = tilt * (0.30f - ny) * (0.35f * w) * 0.45f;\n"
    "                        float capX = 0.05f * w;",
    "                        float headShift = tilt * (0.30f - ny) * (0.35f * w) * 0.18f;\n"
    "                        float capX = 0.018f * w;",
    "head")

# 4) 贴边姿态的几个摆动一起收
sub("                        dx += 0.016f * w * (float) Math.sin(t * 0.6) * ny * ny;",
    "                        dx += 0.006f * w * (float) Math.sin(t * 0.6) * ny * ny;",
    "peek-sway")
sub("                        if (ny < 0.32f) dx += 0.022f * w * look * (0.32f - ny) / 0.32f;",
    "                        if (ny < 0.32f) dx += 0.009f * w * look * (0.32f - ny) / 0.32f;",
    "peek-look")
sub("                            dx += 0.028f * w * hand * (1f - ny / 0.42f);\n"
    "                            dy -= 0.020f * h * hand * (1f - nx / 0.26f);",
    "                            dx += 0.014f * w * hand * (1f - ny / 0.42f);\n"
    "                            dy -= 0.010f * h * hand * (1f - nx / 0.26f);",
    "peek-hand")

# 5) 走路时下身剪切从 2% 收到 1%
sub("                        dx += 0.020f * w * walkAmp * step * (ny - 0.55f) / 0.45f;",
    "                        dx += 0.010f * w * walkAmp * step * (ny - 0.55f) / 0.45f;",
    "walk-shear")

io.open(P, "w", encoding="utf-8").write(src)
for tag, ok in hits:
    print(("OK   " if ok else "MISS ") + tag)
print("all_ok=", all(ok for _, ok in hits))
