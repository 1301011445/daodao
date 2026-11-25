# -*- coding: utf-8 -*-
"""2026-11-25 骨链第二步：把走路摆动的相位从「按时间 t 算」改成「按当前帧号算」。
原因：八帧是 DrawWalkFrames 自己按位移速度调帧率播的（11.6fps 起，随速度变），
而切条摆动 ph=t*8.4 是按钟走的，两者一快一慢、还会随速度漂，腿在换帧、上身各摆各的 → 看着僵硬。
做法：DrawWalkFrames 里把当前相位写进 walkPhaseHint，DrawBmpAlpha 看到就用它。"""
import io

P = r"F:\Daodao\src\桌面分身\pet.cs"
src = io.open(P, encoding="utf-8").read()
hits = []

def sub(old, new, tag):
    global src
    if old not in src:
        hits.append((tag, 0)); return
    src = src.replace(old, new, 1); hits.append((tag, 1))

# 1) 字段
sub("    int poseIdx = 0;",
    "    int poseIdx = 0;\n"
    "    // 2026-11-25：走路时把「当前八帧相位」传进切条，让上身摆动跟换帧同频；-1 表示按时间算\n"
    "    float walkPhaseHint = -1f;", "field")

# 2) 走路调用前写入相位（8 帧 = 2π）
sub("        Rectangle r = new Rectangle(-hw, -hh, (int)baseW, hh);\n"
    "        DrawBmpAlpha(g, pb, r, 1f);\n"
    "        g.Restore(st);\n"
    "    }\n"
    "\n"
    "    // 跳舞：借八帧走路那套真手脚动作",
    "        Rectangle r = new Rectangle(-hw, -hh, (int)baseW, hh);\n"
    "        walkPhaseHint = ph * (float)(Math.PI / 4.0);   // 一轮 8 帧 = 2π\n"
    "        DrawBmpAlpha(g, pb, r, 1f);\n"
    "        walkPhaseHint = -1f;\n"
    "        g.Restore(st);\n"
    "    }\n"
    "\n"
    "    // 跳舞：借八帧走路那套真手脚动作", "hint-walk")

# 3) 切条内部优先用外部相位
sub("        float ph = t * (running ? 12.0f : 8.4f);",
    "        float ph = walkPhaseHint >= 0f ? walkPhaseHint : t * (running ? 12.0f : 8.4f);", "ph-use")

io.open(P, "w", encoding="utf-8").write(src)
for tag, ok in hits:
    print(("OK   " if ok else "MISS ") + tag)
print("all_ok=", all(ok for _, ok in hits))
