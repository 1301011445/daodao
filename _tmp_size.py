from PIL import Image, ImageDraw, ImageFilter, ImageFont
FONT=ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", 16, index=0)
FONT2=ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", 20, index=0)
art=Image.open(r"F:\Daodao\src\_apk\assets\walk8.png").convert("RGBA").crop((0,0,192,384))
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
pet=art.crop((10,6,182,382))
pet.putalpha(pet.getchannel("A").filter(ImageFilter.MinFilter(3)))
pet=pet.resize((90,180), Image.LANCZOS)
W,H=640,470
bg=Image.new("RGB",(W,H),(38,42,62)); d=ImageDraw.Draw(bg)
icons=[("大神","网"),("梦幻西游","梦"),("小米电视","视"),("电视","TV"),("超级小爱","AI"),("道","DAO")]
for i,(t,s) in enumerate(icons):
    cx=80+(i%3)*170; cy=75+(i//3)*200
    d.rounded_rectangle([cx-46,cy-46,cx+46,cy+46],20,fill=(62,68,96))
    d.text((cx-18,cy-12),s,font=FONT,fill=(220,230,250))
    d.text((cx-len(t)*8,cy+58),t,font=FONT,fill=(190,200,225))
d.text((30,H-42),"方的是桌面图标（92px），右边是新尺寸的她：90×180px",font=FONT2,fill=(205,215,238))
bg.paste(pet,(500,H-260),pet)
bg.save(r"C:\Users\LDY\Doubao\chats\2026-11-11\new-chat\手机尺寸_对比_预览.png")
print("ok")
names=[("ball.png","平常"),("ball_happy.png","开心"),("ball_sleep.png","困"),("ball_sur.png","惊讶")]
bs=230
sheet=Image.new("RGB",(bs*4, bs+50),(242,247,255)); dd=ImageDraw.Draw(sheet)
for i,(n,lbl) in enumerate(names):
    im=Image.open(rf"F:\Daodao\src\_apk\assets\{n}").convert("RGBA").resize((bs,bs), Image.LANCZOS)
    mask=Image.new("L",(bs,bs),0); ImageDraw.Draw(mask).ellipse([0,0,bs-1,bs-1],fill=255)
    base=Image.new("RGB",(bs,bs),(238,244,255))
    base.paste(im,(0,0),Image.composite(im,Image.new("RGBA",(bs,bs),(0,0,0,0)),mask))
    sheet.paste(base,(i*bs,0))
    dd.text((i*bs+bs//2-20,bs+12),lbl,font=FONT2,fill=(60,70,95))
sheet.save(r"C:\Users\LDY\Doubao\chats\2026-11-11\new-chat\球表情_四态_预览.png")
print("ok2")
