from PIL import Image, ImageDraw, ImageFont, ImageFilter
import os
W,H=1080,1440
# 底色：深夜到清晨的渐变
bg=Image.new("RGB",(W,H),(22,28,46))
d=ImageDraw.Draw(bg)
for y in range(H):
    t=y/H
    r=int(22+(196-22)*t*0.55); g=int(28+(206-28)*t*0.55); b=int(46+(232-46)*t*0.55)
    d.line([(0,y),(W,y)], fill=(r,g,b))
# 顶部一团柔光
glow=Image.new("RGB",(W,H),(0,0,0)); gd=ImageDraw.Draw(glow)
gd.ellipse([W*0.35,H*0.05,W*0.95,H*0.45], fill=(255,255,255))
glow=glow.filter(ImageFilter.GaussianBlur(180))
bg=Image.blend(bg, Image.blend(bg, glow, 0.28), 0.6)
d=ImageDraw.Draw(bg)

font_big=ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", 108, index=0)
font_sm=ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", 52, index=0)

# 文字
d.text((90,150),"喊一声",font=font_sm,fill=(210,220,240))
d.text((88,230),"「道」",font=font_big,fill=(255,255,255))
d.text((88,370),"它就应了",font=font_big,fill=(255,255,255))
d.text((92,520),"不点它，也会听见你在叫",font=font_sm,fill=(196,208,232))

# 人物：站姿，从右侧边缘探头
art=Image.open(r"F:\Daodao\src\_apk\assets\walk8.png").convert("RGBA").crop((0,0,192,384))
# 抠白底
from collections import deque
px=art.load(); AW,AH=art.size
def nw(c):
    r,g,b,a=c; return a>=60 and r>=225 and g>=225 and b>=225 and (max(r,g,b)-min(r,g,b))<=14
seen=[[False]*AW for _ in range(AH)]; q=deque()
for x in range(AW):
    for y in (0,AH-1):
        if nw(px[x,y]): seen[y][x]=True; q.append((x,y))
for y in range(AH):
    for x in (0,AW-1):
        if nw(px[x,y]) and not seen[y][x]: seen[y][x]=True; q.append((x,y))
while q:
    x,y=q.popleft(); px[x,y]=(0,0,0,0)
    for nx,ny in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
        if 0<=nx<AW and 0<=ny<AH and not seen[ny][nx] and nw(px[nx,ny]):
            seen[ny][nx]=True; q.append((nx,ny))
pet=art.crop((8,6,184,382))
# 去掉抠图留下的白边：把 alpha 往里收 1px 再轻羽化，避免暗底上出现白圈
from PIL import ImageFilter as _IF
_a=pet.getchannel("A").filter(_IF.MinFilter(3)).filter(_IF.GaussianBlur(0.6))
pet.putalpha(_a)
ph=1050
pet=pet.resize((int(pet.width*ph/pet.height), ph), Image.LANCZOS)
# 半身探出：右边切掉一点
x=W-pet.width+60; y=H-ph-40
# 阴影
sh=Image.new("RGBA",(W,H),(0,0,0,0)); ImageDraw.Draw(sh).ellipse([x+pet.width*0.15,y+ph-70,x+pet.width*0.9,y+ph-10],fill=(10,12,20,120))
sh=sh.filter(ImageFilter.GaussianBlur(30))
bg=Image.alpha_composite(bg.convert("RGBA"),sh)
bg.paste(pet,(x,y),pet)
# 圆球头像
ball=Image.open(r"F:\Daodao\src\_apk\assets\ball.png").convert("RGBA").resize((300,300), Image.LANCZOS)
bx,by=110,H-390
mask=Image.new("L",(300,300),0); ImageDraw.Draw(mask).ellipse([0,0,299,299],fill=255)
bg.paste(ball,(bx,by),Image.composite(ball,Image.new("RGBA",(300,300),(0,0,0,0)),mask))
d2=ImageDraw.Draw(bg)
d2.ellipse([bx,by,bx+300,by+300], outline=(175,198,234,255), width=6)

out=bg.convert("RGB")
out.save(r"F:\Daodao\推广草稿\2026-11-22-cover.png")
print("saved", out.size)

