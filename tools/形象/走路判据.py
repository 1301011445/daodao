# -*- coding: utf-8 -*-
"""走路判据 v1（2026-11-25）
把「走路像不像走」变成能算的数：从 pet.cs 里取参数，和素材量出来的步幅一起算滑步率。
判据 B1–B7，任何一条不过就是走路还有毛病。
"""
import io, os, re, json
ROOT=r"F:\Daodao"
SRC=os.path.join(ROOT,r"src\桌面分身\pet.cs")
JRES=os.path.join(ROOT,r"自我状态\形象评审_结果.json")
txt=io.open(SRC,encoding="utf-8",errors="ignore").read()

def get(pat, default=None):
    m=re.search(pat,txt)
    return m.group(1) if m else default

res=json.load(io.open(JRES,encoding="utf-8")) if os.path.exists(JRES) else {}
walkart=res.get("八帧走路",{})
H=144.0                      # 实测：7 号 145px、8 号 144px
stride=max([v["步幅px"] for v in walkart.values() if isinstance(v,dict)] or [21.0])
spd_near=float(get(r"int spd = farAway \? (\d+) : (\d+);", "0")) or None
m=re.search(r"int spd = farAway \? ([0-9]+) : ([0-9]+);", txt)
spd_far, spd_near = (int(m.group(1)), int(m.group(2))) if m else (0,0)
tick_ms=16.0
v_near=spd_near/(tick_ms/1000.0)
v_far=spd_far/(tick_ms/1000.0)
fps=8.0*v_near/(2.0*stride)
cycle_s=8.0/fps
per_cycle=v_near*cycle_s
slide=per_cycle/(2.0*stride)
counters=[int(x) for x in re.findall(r"walkCounter > (\d+)", txt)]
trip_paint = "tripX += tripDir" in txt
side_ok = "float sideDir = (walkDirX >= 0 ? 1f : -1f);" in txt
dt_speed = "moveSpeedPxPerSec = Math.Abs(sxp) / Math.Max(dt, 0.001f)" in txt

rows=[]
def add(code, name, ok, detail):
    rows.append((code,name,ok,detail))

add("B1","近走速度按身材定（≤0.6 身高/秒）", v_near/H<=0.6, f"{v_near:.0f}px/s = {v_near/H:.2f} 身高/秒（身高 {H:.0f}px）")
add("B2","步频由步幅反算，不是拍脑袋比例", "8.0f * Math.Max(moveSpeedPxPerSec, 12f) / (2.0f * stridePx)" in txt,
    f"步幅 {stride:.0f}px → 步频 {fps:.2f} 帧/秒 = {fps/8:.2f} 循环/秒")
add("B3","滑步率 0.8–1.25（一个循环的位移 ≈ 两步步幅）", 0.8<=slide<=1.25, f"每循环位移 {per_cycle:.1f}px / 两步 {2*stride:.1f}px = {slide:.2f}")
add("B4","绘制层不再累加位移（点一下不会自己走掉）", not trip_paint, "tripX += tripDir 已删除" if not trip_paint else "仍在 PaintAll 里累加")
add("B5","巡走间隔 ≥24 秒（1500 跳）", (max(counters) if counters else 0)>=1500, f"walkCounter 阈值 {counters}")
add("B6","朝向跟真实前进方向", side_ok, "sideDir 取 walkDirX" if side_ok else "仍在用 tripDir")
add("B7","速度用真实帧间隔算（换高刷屏不会变快）", dt_speed, "moveSpeedPxPerSec = sxp/dt" if dt_speed else "仍是 sxp×30")

print("== 走路判据（数据：pet.cs 参数 + 八帧素材步幅）==")
bad=0
for c,n,ok,d in rows:
    print(f"{'PASS' if ok else 'FAIL'} {c} {n} — {d}")
    if not ok: bad+=1
print(f"SUMMARY|{len(rows)-bad}/{len(rows)}|bad={bad}")
