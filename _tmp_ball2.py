from PIL import Image, ImageDraw
im = Image.open(r"F:\Daodao\src\_apk\assets\walk8.png").convert("RGBA")
FW=192; FH=384
fr = im.crop((0,0,FW,FH)).convert("RGBA")
# keying：与 Java 同规则（这里直接四边连通清近白）
px = fr.load()
def nw(c):
    r,g,b,a=c
    return a>=60 and r>=225 and g>=225 and b>=225 and (max(r,g,b)-min(r,g,b))<=14
seen=[[False]*FW for _ in range(FH)]; st=[]
for x in range(FW):
    for y in (0,FH-1):
        if nw(px[x,y]) and not seen[y][x]: seen[y][x]=True; st.append((x,y))
for y in range(FH):
    for x in (0,FW-1):
        if nw(px[x,y]) and not seen[y][x]: seen[y][x]=True; st.append((x,y))
while st:
    x,y=st.pop(); px[x,y]=(0,0,0,0)
    for nx,ny in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
        if 0<=nx<FW and 0<=ny<FH and not seen[ny][nx] and nw(px[nx,ny]):
            seen[ny][nx]=True; st.append((nx,ny))
side=int(FW*0.52); x0=int(FW*0.26); y0=int(FH*0.045)
head = fr.crop((x0,y0,x0+side,y0+side))
bs = 143*3
bg = Image.new("RGBA",(bs,bs),(238,244,255,255))
face = head.resize((int(bs*1.04),int(bs*1.04)), Image.LANCZOS)
mask = Image.new("L",(bs,bs),0); ImageDraw.Draw(mask).ellipse([2,2,bs-3,bs-3], fill=255)
bg.paste(face, (-int(bs*0.02), int(bs*0.03)), face)
out = Image.composite(bg, Image.new("RGBA",(bs,bs),(0,0,0,0)), mask)
ImageDraw.Draw(out).ellipse([2,2,bs-3,bs-3], outline=(175,198,234,255), width=4)
out.save(r"C:\Users\LDY\Doubao\chats\2026-11-11\new-chat\浮窗_小圆球_预览.png")
print("head crop", x0,y0,side)
