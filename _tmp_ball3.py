from PIL import Image, ImageDraw
art=Image.open(r"F:\Daodao\src\_apk\assets\ball.png").convert("RGBA")
bs=143*3
bg=Image.new("RGBA",(bs,bs),(238,244,255,255))
s=max(bs/art.width, bs/art.height)
dw,dh=art.width*s, art.height*s
face=art.resize((int(dw),int(dh)), Image.LANCZOS)
bg.paste(face,(int((bs-dw)/2), int((bs-dh)/2 - bs*0.06)), face)
mask=Image.new("L",(bs,bs),0); ImageDraw.Draw(mask).ellipse([2,2,bs-3,bs-3], fill=255)
out=Image.composite(bg, Image.new("RGBA",(bs,bs),(0,0,0,0)), mask)
ImageDraw.Draw(out).ellipse([2,2,bs-3,bs-3], outline=(175,198,234,255), width=4)
out.save(r"C:\Users\LDY\Doubao\chats\2026-11-11\new-chat\浮窗_新球头像_预览.png")
print("ok")
