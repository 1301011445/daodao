# -*- coding: utf-8 -*-
"""2026-11-25 坐骑：把程序画的「几个椭圆」换成真的手办质感坐骑贴图（mount.png），
椭圆那套留着当兜底（图没有时照旧画）。"""
import io

P = r"F:\Daodao\src\桌面分身\pet.cs"
s = io.open(P, encoding="utf-8").read()
ok = []


def rep(tag, old, new):
    global s
    if old not in s:
        ok.append((tag, False))
        return
    s = s.replace(old, new, 1)
    ok.append((tag, True))


# 1) 字段 + 载入函数
rep("fields",
    "    // ================= 曲库与播放",
    "    // 2026-11-25：坐骑改成真贴图（骨架\\mount.png 或 exe 目录 mount.png），没有就退回程序画的椭圆兽\n"
    "    Bitmap mountArt = null;\n"
    "    bool mountTried = false;\n"
    "    Bitmap GetMountArt()\n"
    "    {\n"
    "        if (mountTried) return mountArt;\n"
    "        mountTried = true;\n"
    "        try\n"
    "        {\n"
    "            Stream ms = ResStream(\"mount.png\");\n"
    "            if (ms != null) { using (Stream m2 = ms) { mountArt = new Bitmap(m2); } }\n"
    "            else\n"
    "            {\n"
    "                string mp1 = Path.Combine(Path.GetDirectoryName(Application.ExecutablePath), \"骨架\\\\mount.png\");\n"
    "                string mp2 = Path.Combine(Path.GetDirectoryName(Application.ExecutablePath), \"mount.png\");\n"
    "                if (File.Exists(mp1)) mountArt = new Bitmap(mp1);\n"
    "                else if (File.Exists(mp2)) mountArt = new Bitmap(mp2);\n"
    "            }\n"
    "        }\n"
    "        catch { mountArt = null; }\n"
    "        return mountArt;\n"
    "    }\n"
    "\n"
    "    // ================= 曲库与播放")

# 2) 骑坐骑分支：先试贴图，没有才画椭圆
rep("branch-open",
    "            else if (actKind == 3)\n"
    "            {\n"
    "                // 骑坐骑：身下一匹矮脚小兽，四条腿交替倒腾，尾巴左右甩",
    "            else if (actKind == 3)\n"
    "            {\n"
    "                Bitmap mt = GetMountArt();\n"
    "                if (mt != null && !mt.Disposed)\n"
    "                {\n"
    "                    // 真贴图：脚底贴地，body 轻颠（每步一下），riding 时人踩在鞍上\n"
    "                    float mh = targetH * 0.34f;\n"
    "                    float mw = mh * mt.Width / (float)mt.Height;\n"
    "                    float bob2 = (float)Math.Sin(t * 6.4f) * targetH * 0.012f;\n"
    "                    float lx2 = -mw * 0.5f + (float)Math.Sin(t * 3.1f) * targetH * 0.006f;\n"
    "                    g.DrawImage(mt, new RectangleF(lx2, 8f + slide - mh + bob2, mw, mh));\n"
    "                }\n"
    "                else\n"
    "                {\n"
    "                // 兜底：身下一匹矮脚小兽，四条腿交替倒腾，尾巴左右甩")

rep("branch-close",
    "            }\n"
    "            else if (actKind == 7)",
    "                }\n"
    "            }\n"
    "            else if (actKind == 7)")

io.open(P, "w", encoding="utf-8").write(s)
for tag, good in ok:
    print(("OK   " if good else "MISS ") + tag)
print("all_ok=", all(g for _, g in ok))
