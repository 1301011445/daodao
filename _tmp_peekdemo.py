from PIL import Image, ImageDraw, ImageFont
art=Image.open(r"F:\Daodao\src\_apk\assets\walk8.png").convert("RGBA").crop((0,0,192,384))
# 同一套 keyWhite 抠白底
from collections import deque
px=art.load(); W,H=art.size
def nw(c):
    r,g,b,a=c; return a>=60 and r>=225 and g>=225 and b>=225 and (max(r,g,b)-min(r,g,b))<=14
seen=[[False]*W for _ in range(H)]; q=deque()
for x in range(W):
    for y in (0,H-1):
        if nw(px[x,y]): seen[y][x]=True; q.append((x,y))
for y in range(H):
    for x in (0,W-1):
        if nw(px[x,y]) and not seen[y][x]: seen[y][x]=True; q.append((x,y))
while q:
    x,y=q.popleft(); px[x,y]=(0,0,0,0)
    for nx,ny in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
        if 0<=nx<W and 0<=ny<H and not seen[ny][nx] and nw(px[nx,ny]):
            seen[ny][nx]=True; q.append((nx,ny))
pet=art.crop((10,8,182,380))
pet=pet.resize((int(pet.width*0.92), int(pet.height*0.92)), Image.LANCZOS)
PW,PH=pet.size
panel_w, panel_h = 240, 460
edge_x = 200   # 面板里"屏幕右边缘"的位置
fr=[0.0,0.5,1.0,0.5]
labels=["藏着（半身）","往外探","探出来","缩回去"]
out=Image.new("RGB",(panel_w*4, panel_h),(24,26,40))
d=ImageDraw.Draw(out)
for i,f in enumerate(fr):
    # 桌面底色
    d.rectangle([i*panel_w, 0, (i+1)*panel_w-1, panel_h-1], fill=(52,58,86))
    # 屏幕外区域更暗
    d.rectangle([i*panel_w+edge_x, 0, (i+1)*panel_w-1, panel_h-1], fill=(18,20,30))
    rest_x = edge_x - PW//2
    out_x  = edge_x - PW
    x = int(rest_x + (out_x-rest_x)*f)
    y = panel_h - PH - 10
    # 脚下阴影
    d.ellipse([i*panel_w+x+PW*0.24, y+PH-12, i*panel_w+x+PW*0.76, y+PH+2], fill=(30,32,44))
    out.paste(pet,(i*panel_w+x, y),pet)
    # 边框线
    d.line([i*panel_w+edge_x, 0, i*panel_w+edge_x, panel_h], fill=(120,140,190), width=2)
out.save(r"C:\Users\LDY\Doubao\chats\2026-11-11\new-chat\浮窗_探头四段_预览.png")
print("ok", out.size)

