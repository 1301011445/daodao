# -*- coding: utf-8 -*-
"""2026-11-25 手机端两件事：
1) 白边：keyWhite 只清了"从四边连通过来"的纯白，紧贴人物的那圈半透明白混色没处理，就是用户看到的白边。
   改成 matteInPlace：泛洪清底 + 边缘 2 圈「按白度估 alpha + 去白」。
2) 动作：悬浮窗原来只会走和挥手。加 挥手/点头/小跳/蹲一下 四个网格动作，自己按拍子挑一个演，
   并且手机里点「换动作」会真的让桌面那只动（走 DaoNative.petAct）。
"""
import io

OV = r"F:\Daodao\src\_apk\src\com\daodao\pet\DaoOverlay.java"
BR = r"F:\Daodao\src\_apk\src\com\daodao\pet\DaoBridge.java"
HTML = r"F:\Daodao\道-随身版.html"
log = []


def edit(path, pairs):
    s = io.open(path, encoding="utf-8").read()
    for tag, old, new in pairs:
        if old not in s:
            log.append((tag, 0))
            continue
        s = s.replace(old, new, 1)
        log.append((tag, 1))
    io.open(path, "w", encoding="utf-8").write(s)


# ---------------- DaoOverlay ----------------
edit(OV, [
    ("fields",
     "        private long nextIdleWave = 0;       // 自己每隔 8~15 分钟抬手挥一次，白天才挥",
     "        private long nextIdleWave = 0;       // 自己每隔 8~15 分钟抬手挥一次，白天才挥\n"
     "        // 2026-11-25：原来只会走路和挥手，戳它也没别的反应，所以看着「不会做动作」。\n"
     "        // 加四个网格动作（挥手 / 点头 / 小跳 / 蹲一下），自己按拍子演，也能被「换动作」叫起来。\n"
     "        private long hopUntil = 0;\n"
     "        private long squatUntil = 0;\n"
     "        private long nextActAt = 0;\n"
     "        private int lastAct = -1;\n"
     "        static final int ACT_WAVE = 0, ACT_NOD = 1, ACT_HOP = 2, ACT_SQUAT = 3;"),

    ("live-ref",
     "        PetView() {\n"
     "            super(DaoOverlay.this);\n"
     "            setLayerType(View.LAYER_TYPE_HARDWARE, null);\n"
     "            reloadSheet();\n"
     "        }",
     "        PetView() {\n"
     "            super(DaoOverlay.this);\n"
     "            setLayerType(View.LAYER_TYPE_HARDWARE, null);\n"
     "            sLive = this;\n"
     "            reloadSheet();\n"
     "        }"),

    ("matte-sheet",
     "            if (sheet != null && !sheet.isRecycled()) keyWhite();",
     "            if (sheet != null && !sheet.isRecycled()) matteInPlace(sheet);"),

    ("matte-stand",
     '            standArt = loadOpt("stand_" + art + ".png");',
     '            standArt = loadOpt("stand_" + art + ".png");\n'
     "            if (standArt != null && !standArt.isRecycled()) matteInPlace(standArt);"),

    ("matte-peek",
     '            peekArt = loadOpt("peek.png");',
     '            peekArt = loadOpt("peek.png");\n'
     "            if (peekArt != null && !peekArt.isRecycled()) matteInPlace(peekArt);"),

    ("keywhite-fringe",
     "                sheet.setPixels(px, 0, w, 0, 0, w, h);\n"
     "            } catch (Exception e) { }",
     "                deFringe(px, w, h, seen);      // 紧贴人物的那圈白混色，不清掉就是白边\n"
     "                sheet.setPixels(px, 0, w, 0, 0, w, h);\n"
     "            } catch (Exception e) { }"),

    ("new-methods",
     "        boolean nearWhite(int c) {",
     "        /** 白底素材统一处理：泛洪清底 + 边缘去白。\n"
     "         *  立绘/站姿/探头这几张都不是透明底，边缘那圈是「白+人物色」的混色，\n"
     "         *  只把纯白挖掉，剩下的混色圈挂在深色桌面上就是一道白边。 */\n"
     "        void matteInPlace(Bitmap b) {\n"
     "            try {\n"
     "                int w = b.getWidth(), h = b.getHeight();\n"
     "                int[] px = new int[w * h];\n"
     "                b.getPixels(px, 0, w, 0, 0, w, h);\n"
     "                boolean[] bg = new boolean[w * h];\n"
     "                int[] q = new int[w * h];\n"
     "                int head = 0, tail = 0;\n"
     "                for (int x = 0; x < w; x++) {\n"
     "                    tail = pushIfWhite(px, bg, q, tail, x, x);\n"
     "                    tail = pushIfWhite(px, bg, q, tail, x, (h - 1) * w + x);\n"
     "                }\n"
     "                for (int y = 0; y < h; y++) {\n"
     "                    tail = pushIfWhite(px, bg, q, tail, y, y * w);\n"
     "                    tail = pushIfWhite(px, bg, q, tail, y, y * w + w - 1);\n"
     "                }\n"
     "                while (head < tail) {\n"
     "                    int idx = q[head++];\n"
     "                    px[idx] = 0;\n"
     "                    int x = idx % w, y = idx / w;\n"
     "                    if (x > 0) tail = pushIfWhite(px, bg, q, tail, x - 1, idx - 1);\n"
     "                    if (x < w - 1) tail = pushIfWhite(px, bg, q, tail, x + 1, idx + 1);\n"
     "                    if (y > 0) tail = pushIfWhite(px, bg, q, tail, x, idx - w);\n"
     "                    if (y < h - 1) tail = pushIfWhite(px, bg, q, tail, x, idx + w);\n"
     "                }\n"
     "                deFringe(px, w, h, bg);\n"
     "                b.setPixels(px, 0, w, 0, 0, w, h);\n"
     "            } catch (Exception e) { }\n"
     "        }\n"
     "\n"
     "        /** 沿已清掉的底色向内走两圈：这几圈像素是背景白和人物色的混色，\n"
     "         *  按白度估半透明 alpha，再按 alpha 把混进去的白扣掉，边上就干净了。 */\n"
     "        void deFringe(int[] px, int w, int h, boolean[] bg) {\n"
     "            for (int pass = 0; pass < 2; pass++) {\n"
     "                int[] cp = px.clone();\n"
     "                for (int y = 0; y < h; y++) {\n"
     "                    for (int x = 0; x < w; x++) {\n"
     "                        int idx = y * w + x;\n"
     "                        if (bg[idx]) continue;\n"
     "                        boolean nb = (x > 0 && bg[idx - 1]) || (x < w - 1 && bg[idx + 1])\n"
     "                                || (y > 0 && bg[idx - w]) || (y < h - 1 && bg[idx + w]);\n"
     "                        if (!nb) continue;\n"
     "                        int c = cp[idx];\n"
     "                        int a = c >>> 24;\n"
     "                        if (a < 40) continue;\n"
     "                        int r = (c >> 16) & 0xFF, g = (c >> 8) & 0xFF, bl = c & 0xFF;\n"
     "                        int lum = Math.min(r, Math.min(g, bl));\n"
     "                        int mx = Math.max(r, Math.max(g, bl));\n"
     "                        if (mx - lum > 28 || lum < 140) continue;      // 只处理接近白的混色\n"
     "                        float s = (255 - lum) / 78f;\n"
     "                        if (s > 1f) s = 1f;\n"
     "                        if (s < 0.04f) s = 0.04f;\n"
     "                        float inv = s < 0.10f ? 0.10f : s;\n"
     "                        int rr = (int) Math.max(0, Math.min(255, (r - 255f * (1f - s)) / inv));\n"
     "                        int gg = (int) Math.max(0, Math.min(255, (g - 255f * (1f - s)) / inv));\n"
     "                        int bb = (int) Math.max(0, Math.min(255, (bl - 255f * (1f - s)) / inv));\n"
     "                        px[idx] = ((int) (a * s) << 24) | (rr << 16) | (gg << 8) | bb;\n"
     "                        bg[idx] = true;                              // 已处理 → 往外再扩一圈\n"
     "                    }\n"
     "                }\n"
     "            }\n"
     "        }\n"
     "\n"
     "        boolean nearWhite(int c) {"),

    ("hop-vars",
     "            if (walking && walkDir < 0) { c.translate(w, 0); c.scale(-1f, 1f); }",
     "            // 小跳 / 蹲一下：整只抬起来或压下去，脚底始终贴着原来的地平线\n"
     "            float hop = 0f, squash = 1f;\n"
     "            if (nowMs < hopUntil) {\n"
     "                float pr = 1f - (hopUntil - nowMs) / 900f;\n"
     "                hop = (float) Math.sin(pr * Math.PI) * h * 0.085f;\n"
     "            }\n"
     "            if (nowMs < squatUntil) {\n"
     "                float pr = 1f - (squatUntil - nowMs) / 1600f;\n"
     "                squash = 1f - 0.085f * (float) Math.sin(pr * Math.PI);\n"
     "            }\n"
     "            if (walking && walkDir < 0) { c.translate(w, 0); c.scale(-1f, 1f); }"),

    ("stand-hop",
     "            } else if (vm != MODE_PEEK && !walking && standArt != null && !standArt.isRecycled()) {\n"
     "                drawWarp(c, standArt, 0, bob, w, h + bob, tick / 30.0, 0f, false, false, waveAmp, nodAmp);",
     "            } else if (vm != MODE_PEEK && !walking && standArt != null && !standArt.isRecycled()) {\n"
     "                int dyAct = (int) (h * (1f - squash));\n"
     "                drawWarp(c, standArt, 0, bob - (int) hop + dyAct, w, (int) (h * squash) + bob,\n"
     "                        tick / 30.0, 0f, false, false, waveAmp, nodAmp);"),

    ("idle-act-call",
     "                    try { pv.idleWaveIfDue(); } catch (Exception e) { }",
     "                    try { pv.idleWaveIfDue(); } catch (Exception e) { }\n"
     "                    try { pv.idleActIfDue(); } catch (Exception e) { }"),

    ("play-action",
     "        // 打招呼：戳它一定应一声；平时二十来分钟自己冒一句（只白天，晚上别吵）",
     "        /** 演一个动作。0 挥手 1 点头 2 小跳 3 蹲一下；外面（手机「换动作」）也走这里。 */\n"
     "        void playAction(int k) {\n"
     "            long now = System.currentTimeMillis();\n"
     "            lastAct = k;\n"
     "            if (k == ACT_WAVE) waveUntil = now + WAVE_MS;\n"
     "            else if (k == ACT_NOD) nodUntil = now + 1400;\n"
     "            else if (k == ACT_HOP) hopUntil = now + 900;\n"
     "            else if (k == ACT_SQUAT) squatUntil = now + 1600;\n"
     "            postInvalidate();\n"
     "        }\n"
     "\n"
     "        /** 站着待着的时候，每隔十几二十秒自己演一个动作，别一直像个静物。 */\n"
     "        void idleActIfDue() {\n"
     "            long now = System.currentTimeMillis();\n"
     "            if (walking) { nextActAt = now + 8000; return; }\n"
     "            if (nextActAt == 0) { nextActAt = now + 7000; return; }\n"
     "            if (now < nextActAt) return;\n"
     "            nextActAt = now + (long) ((13 + Math.random() * 13) * 1000);\n"
     "            int hh = java.util.Calendar.getInstance().get(java.util.Calendar.HOUR_OF_DAY);\n"
     "            if (vm != MODE_FULL) return;\n"
     "            if (hh < 7 || hh > 22) return;\n"
     "            int k = (int) (Math.random() * 4);\n"
     "            if (k == lastAct) k = (k + 1) % 4;      // 别连着演同一个\n"
     "            playAction(k);\n"
     "        }\n"
     "\n"
     "        // 打招呼：戳它一定应一声；平时二十来分钟自己冒一句（只白天，晚上别吵）"),
])

# 静态入口：外面调
s = io.open(OV, encoding="utf-8").read()
if "private static PetView sLive" not in s:
    s = s.replace("    // ---------------- 画 ----------------",
                  "    // ---------------- 画 ----------------\n"
                  "    private static PetView sLive;   // 当前挂着的悬浮窗，供「换动作」这类外部调用\n"
                  "    /** 外部（手机主界面「换动作」按钮）让桌面上的那只动一下。 */\n"
                  "    static boolean sendAction(int k) {\n"
                  "        PetView v = sLive;\n"
                  "        if (v == null) return false;\n"
                  "        v.playAction(k);\n"
                  "        return true;\n"
                  "    }\n", 1)
    log.append(("sLive-method", 1))
io.open(OV, "w", encoding="utf-8").write(s)

# ---------------- DaoBridge ----------------
edit(BR, [
    ("bridge-act",
     "    @JavascriptInterface\n"
     "    public void warmUp() {\n",
     "    /** 2026-11-25：手机主界面「换动作」也去指挥桌面那只，不然点了只有页面里的人换姿势，浮窗纹丝不动。 */\n"
     "    @JavascriptInterface\n"
     "    public void petAct(final String name) {\n"
     "        int k = DaoOverlay.ACT_WAVE;\n"
     "        if (\"fly\".equals(name)) k = DaoOverlay.ACT_HOP;\n"
     "        else if (\"ride\".equals(name)) k = DaoOverlay.ACT_SQUAT;\n"
     "        else if (\"tea\".equals(name)) k = DaoOverlay.ACT_NOD;\n"
     "        else if (\"tv\".equals(name)) k = DaoOverlay.ACT_SQUAT;\n"
     "        else if (\"skate\".equals(name)) k = DaoOverlay.ACT_HOP;\n"
     "        else if (\"dance\".equals(name)) k = DaoOverlay.ACT_WAVE;\n"
     "        try { DaoOverlay.sendAction(k); } catch (Throwable e) { }\n"
     "    }\n"
     "\n"
     "    @JavascriptInterface\n"
     "    public void warmUp() {\n"),
])

# ---------------- dao.html ----------------
edit(HTML, [
    ("html-act",
     "    actKind = actOfMode(m); actAmt = 1;\n"
     "    sceneIdx = sceneForAct(actKind);\n"
     "    say(ACT_WORDS[m]);",
     "    actKind = actOfMode(m); actAmt = 1;\n"
     "    sceneIdx = sceneForAct(actKind);\n"
     "    try { if (window.DaoNative && DaoNative.petAct) DaoNative.petAct(m); } catch (e) {}\n"
     "    say(ACT_WORDS[m]);"),
])

for tag, ok in log:
    print(("OK   " if ok else "MISS ") + tag)
print("all_ok=", all(ok for _, ok in log))
