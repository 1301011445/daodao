# -*- coding: utf-8 -*-
"""2026-11-25：手机端悬浮窗——贴边也打招呼（挥手），并且一露面就先应一声正视图。"""
import io

P = r"F:\Daodao\src\_apk\src\com\daodao\pet\DaoOverlay.java"
src = io.open(P, encoding="utf-8").read()
hits = []

def sub(old, new, tag):
    global src
    if old not in src:
        hits.append((tag, 0)); return
    src = src.replace(old, new, 1); hits.append((tag, 1))

# 1) 挥手不再只限满身：贴边站着也能抬手（看起来像在侧边跟你打招呼）
sub("            if (vm == MODE_FULL && !walking && nowMs < waveUntil && waveUntil - nowMs <= WAVE_MS) {",
    "            if ((vm == MODE_FULL || vm == MODE_PEEK) && !walking && nowMs < waveUntil && waveUntil - nowMs <= WAVE_MS) {",
    "wave-any-mode")

# 2) 贴边那条绘制调用把 waveAmp 传进去（原来固定 0f）
sub("                drawWarp(c, peekArt, 0, bob, w, h + bob, tick / 30.0, 0f, false, true, 0f, 0f);",
    "                drawWarp(c, peekArt, 0, bob, w, h + bob, tick / 30.0, 0f, false, true, waveAmp, 0f);",
    "peek-wave-arg")

# 3) 一露面就打招呼（只第一次挂上去时，强制一次，不看时段、不看 20 分钟限流）
sub("        if (!added) {\n            try {\n                wm.addView(pv, lp);\n                added = true;",
    "        if (!added) {\n            try {\n                wm.addView(pv, lp);\n                added = true;\n"
    "                // 2026-11-25：浮窗刚挂到桌面上的那一下，先抬手打个招呼再站定\n"
    "                try { pv.greet(true); } catch (Exception e) { }",
    "greet-on-show")

io.open(P, "w", encoding="utf-8").write(src)
for tag, ok in hits:
    print(("OK   " if ok else "MISS ") + tag)
print("all_ok=", all(ok for _, ok in hits))
