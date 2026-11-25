# -*- coding: utf-8 -*-
"""形象评审 v1（2026-11-25）
把「看着像不像」变成能跑的数字：A1 头身比 / A2 缩略五官 / A3 贴图表情残留 /
A6 全身完整 / A8 步态是否真迈步。数据全部来自 _bundle 里的立绘、八帧走路素材，
以及 道.exe --dump 现渲染出来的 selfcheck_*.png。
用法：E:\Python313\python.exe -X utf8 F:\Daodao\tools\形象\形象评审.py
"""
import io, json, os, re, sys, glob
import numpy as np
from PIL import Image

ROOT = r"F:\Daodao"
BUN = os.path.join(ROOT, r"src\桌面分身\_bundle")
SRC = os.path.join(ROOT, r"src\桌面分身")
OUT = os.path.join(ROOT, r"自我状态\形象评审_结果.json")
NAME = {0:"橘猫",1:"白兔",2:"狐狸",3:"熊猫",4:"恐龙少女",5:"企鹅",6:"蓝发少女",7:"黑发少年",
        8:"银发剑客",9:"紫发少女",10:"金发少女",11:"机甲",12:"白裙少女",13:"猫耳少年"}
WALK_OK = [0,1,2,3,4,5,6,7,8,9,10,11,12,13]

def alpha_mask(p):
    a = np.asarray(Image.open(p).convert("RGBA"))
    return a[:,:,3] > 20, a

def bbox(m):
    ys, xs = np.where(m)
    return int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())

def head_ratio(m):
    """头身比：取头顶到「脖子最窄处」为头高。用宽度剖面找颈部，找不到返回 None。"""
    x0,y0,x1,y1 = bbox(m)
    H = y1-y0+1
    widths = np.array([(lambda c: c.max()-c.min()+1 if c.size else 0)(np.where(m[y])[0]) for y in range(y0,y1+1)])
    topwin = max(3,int(H*0.22))
    hw = widths[:topwin].max()
    neck = None
    for i in range(int(topwin*0.45), int(H*0.6)):
        if 0 < widths[i] < 0.55*hw:
            neck = i; break
    return (H/neck if neck else None), H, neck, int(hw)

# ---------- 素材级：立绘 ----------
art = {}
for p in sorted(glob.glob(os.path.join(BUN,"face_*.png"))):
    nm = os.path.basename(p)
    m,_ = alpha_mask(p)
    if m.sum() < 50: continue
    x0,y0,x1,y1 = bbox(m)
    H = y1-y0+1
    edge = min(x0, y0, m.shape[1]-1-x1, m.shape[0]-1-y1)
    r,_,neck,hw = head_ratio(m)
    # A2：缩到 25% 后，五官区（头顶往下 22%）的梯度能量
    im = Image.open(p).convert("RGBA").resize((max(8,int(m.shape[1]*0.25)), max(8,int(m.shape[0]*0.25))), Image.LANCZOS)
    g = np.asarray(im.convert("L")).astype(np.float32)
    fy0,fy1 = int(y0*0.25), int((y0+H*0.22)*0.25)
    face = g[max(0,fy0):max(1,fy1), :]
    edges = float(np.abs(np.diff(face, axis=1)).mean()) if face.size else 0.0
    art[nm] = dict(H=int(H), 头高=neck, 头身比=round(r,2) if r else None, 触边=int(edge),
                   头宽=int(hw), 缩略五官梯度=round(edges,2), 尺寸=[int(m.shape[1]),int(m.shape[0])])

# ---------- 素材级：八帧走路 ----------
walk = {}
for sp in WALK_OK:
    frames = []
    for i in range(1,9):
        p = os.path.join(BUN,f"walk8_{sp}_{i}.png")
        if not os.path.exists(p): frames=[]; break
        m,a = alpha_mask(p)
        if m.sum()<50: frames=[]; break
        x0,y0,x1,y1 = bbox(m); H=y1-y0+1
        band = m[max(0,y1-int(H*0.10)):y1+1,:]
        cols = np.where(band.any(axis=0))[0]
        gaps = np.where(np.diff(cols)>2)[0] if cols.size else np.array([])
        segs = np.split(cols, gaps+1) if cols.size else []
        feet = [float(s.mean()) for s in segs]
        frames.append(dict(H=H, bottom=int(y1), cx=(x0+x1)/2.0, feet=feet, m=m))
    if not frames: continue
    foot_n = min(len(f["feet"]) for f in frames)
    # 步幅：两簇时的左右脚间距变化；单簇时用底带质心摆幅
    if foot_n >= 2:
        sep = [abs(f["feet"][0]-f["feet"][-1]) for f in frames]
        stride = round(max(sep)-min(sep),1)
    else:
        cxs = [ (f["feet"][0] if f["feet"] else 0) for f in frames]
        stride = round(max(cxs)-min(cxs),1)
    cx_drift = round(max(f["cx"] for f in frames)-min(f["cx"] for f in frames),1)
    bot_jit = max(f["bottom"] for f in frames)-min(f["bottom"] for f in frames)
    # 腿部区帧间差
    legd=[]
    for i in range(1,8):
        a0,a1 = frames[i-1]["m"], frames[i]["m"]
        Hh=min(a0.shape[0],a1.shape[0])
        leg0=a0[int(Hh*0.62):,:]; leg1=a1[int(Hh*0.62):,:]
        legd.append(float((leg0^leg1).sum()))
    walk[sp]=dict(脚簇数=foot_n, 步幅px=stride, 中心漂移px=cx_drift, 底边抖动px=int(bot_jit),
                  腿区帧差均值=round(float(np.mean(legd)),0), 高px=int(np.median([f["H"] for f in frames])))

# ---------- 渲染级：--dump 现渲染 ----------
dump = {}
try:
    for sp, pat in ((7,"selfcheck_walk%d.png"),(8,"selfcheck_walk8_%d.png"),(6,"selfcheck_walk6_%d.png")):
        fr=[]
        for i in range(8):
            p = os.path.join(ROOT, pat % i)
            if not os.path.exists(p): break
            a = np.asarray(Image.open(p).convert("RGB")).astype(np.int16)
            mm = ~((a[:,:,0]>200)&(a[:,:,2]>200)&(a[:,:,1]<90))
            x0,y0,x1,y1 = bbox(mm)
            fr.append(dict(cx=(x0+x1)/2.0, bottom=int(y1), H=int(y1-y0+1)))
        if len(fr)==8:
            dump[sp]=dict(中心摆幅px=round(max(f["cx"] for f in fr)-min(f["cx"] for f in fr),1),
                          底边抖动px=int(max(f["bottom"] for f in fr)-min(f["bottom"] for f in fr)),
                          底边=int(max(f["bottom"] for f in fr)), 高px=int(np.median([f["H"] for f in fr])))
except Exception as e:
    dump["err"]=str(e)

# ---------- A3：贴图表情残留 ----------
bad_tokens = ["腮红","泪滴","怒纹","汗滴","DrawFaceExpr","DrawTear","DrawFaceBubble"]
hits=[]
for p in [os.path.join(SRC,"pet.cs"), os.path.join(ROOT,"dao.html"),
          os.path.join(ROOT,r"src\_apk\assets\dao.html")]:
    if not os.path.exists(p): continue
    txt = io.open(p,encoding="utf-8",errors="ignore").read()
    # 注释里写这些名字是"已经删掉"的说明，不算残留：先剥掉块注释和行注释再数
    txt = re.sub(r"\*.*?\*/", "", txt, flags=re.S)
    txt = re.sub(r"//[^\n]*", "", txt)
    for t in bad_tokens:
        n = txt.count(t)
        if n: hits.append(f"{os.path.basename(p)}:{t}={n}")
res = {"日期":"2026-11-25","立绘":art,"八帧走路":walk,"现渲染":dump,"A3残留":hits}
os.makedirs(os.path.dirname(OUT), exist_ok=True)
io.open(OUT,"w",encoding="utf-8").write(json.dumps(res,ensure_ascii=False,indent=1))

# ---------- 判定 ----------
print("== A1 头身比（6.5–8.0）==")
bad=[]
for k,v in art.items():
    r=v["头身比"]
    st = "PASS" if (r and 6.5<=r<=8.0) else ("NA" if not r else "FAIL")
    if st=="FAIL": bad.append(k)
    print(f"  {k:16s} H={v['H']:3d} 头高={str(v['头高']):>3s} 头身比={str(r):>5s} {st}")
print(f"  A1: {len(art)-len(bad)}/{len(art)} PASS（头身比>8 的：{len(bad)} 张）")

print("== A6 全身完整（素材四边留白 ≥1px，渲染时脚不触底）==")
e_bad=[k for k,v in art.items() if v["触边"]<1]
print(f"  素材触边张数={len(e_bad)}  {e_bad[:6]}")
if dump:
    for sp,v in dump.items():
        if isinstance(v,dict):
            print(f"  渲染 sp{sp}: 高{v['高px']}px 底边y={v['底边']} 距画布底 {205-v['底边']}px")

print("== A8 步态（脚要分开、要迈、不能横向漂）==")
for sp,v in walk.items():
    foot_ok = v["脚簇数"]>=2
    stride_ok = v["步幅px"]>=6
    print(f"  sp{sp:2d} {NAME.get(sp,''):5s} 脚簇={v['脚簇数']} 步幅={v['步幅px']:>5.1f}px "
          f"中心漂={v['中心漂移px']:>4.1f}px 底抖={v['底边抖动px']}px 腿区帧差={v['腿区帧差均值']:.0f} "
          f"{'PASS' if foot_ok and stride_ok else 'FAIL'}")

print("== 现渲染侧向摆幅（应 ≈2×摆幅且反复，不是单向漂）==")
for sp,v in dump.items():
    if isinstance(v,dict):
        h=v["高px"]; amp=v["中心摆幅px"]/2.0/h*100
        print(f"  sp{sp}: 单向摆幅 {v['中心摆幅px']/2:.1f}px = 身高 {amp:.1f}%（阈值 ≤3%） {'PASS' if amp<=3 else 'FAIL'}")

print("== A3 贴图表情残留（必须 0）==")
print("  " + ("PASS 全清" if not hits else "FAIL " + "; ".join(hits)))


