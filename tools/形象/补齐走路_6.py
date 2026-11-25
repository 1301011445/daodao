# -*- coding: utf-8 -*-
import importlib.util, math, os, sys, numpy as np
from PIL import Image
spec=importlib.util.spec_from_file_location("bone", r"F:\Daodao\tools\形象\分层骨骼_v134.py")
bone=importlib.util.module_from_spec(spec); sys.argv=["x"]
try: spec.loader.exec_module(bone)
except SystemExit: pass
A=r"F:\Daodao\src\_apk\assets"; W,H=192,384
src=Image.open(os.path.join(A,"stand_6.png")).convert("RGBA")
base,cut,_=bone.build(src)
# 去掉底图里残留的原腿/原鞋，避免转腿后出现两双鞋
legmask=np.zeros((H,W),bool)
for k in ("legL","legR"):
    a=np.array(cut[k])[...,3]>30
    legmask|=a
# 只擦下半身（hip 以下），上半身不动
y0=int(H*0.45)
legmask[:y0,:]=False
b=np.array(base); b[legmask,3]=0
base=Image.fromarray(b,"RGBA")
AD,OFF=24,0.5
frames=[]
for i in range(8):
    ph=2*math.pi*((i+OFF)/8)
    body=Image.new("RGBA",(W,H),(0,0,0,0)); body.alpha_composite(base)
    for k,ang in (("legL",AD*math.sin(ph)),("legR",-AD*math.sin(ph)),
                  ("armL",-11*math.sin(ph)),("armR",11*math.sin(ph))):
        if abs(ang)<0.5: body.alpha_composite(cut[k])
        else:
            jx,jy=bone.pivot(k,W,H)
            body.alpha_composite(cut[k].rotate(ang,resample=Image.BICUBIC,center=(jx,jy),fillcolor=(0,0,0,0)))
    dy=-2 if i in (1,2,5,6) else 0
    f=Image.new("RGBA",(W,H),(0,0,0,0)); f.alpha_composite(body,(0,dy))
    frames.append(f)
for i,f in enumerate(frames): f.save(os.path.join(A,f"walk8_6_{i+1}.png"))
sheet=Image.new("RGBA",(W*8,H),(0,0,0,0))
for i,f in enumerate(frames): sheet.paste(f,(i*W,0),f)
sheet.save(os.path.join(A,"walk8_6.png"))
# 拼图
out=Image.new("RGB",(W*4,H*2),(250,250,250))
for i,f in enumerate(frames):
    bg=Image.new("RGBA",(W,H),(250,250,250,255)); bg.alpha_composite(f)
    out.paste(bg.convert("RGB"),((i%4)*W,(i//4)*H))
out.save(r"F:\Daodao\_diag_look\走路_6号蓝发少女_138.png")
print("rewritten")
