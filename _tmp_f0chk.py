from PIL import Image
im=Image.open(r"F:\Daodao\src\_apk\assets\walk8.png").convert("RGBA")
f=im.crop((0,0,192,384))
a=f.getchannel("A"); print("frame0 alpha bbox", a.point(lambda v:255 if v>8 else 0).getbbox())
p=Image.new("RGBA",(192,384),(255,0,255,255)); p.paste(f,(0,0),f)
p.convert("RGB").resize((192,384)).save(r"C:\Users\LDY\Doubao\chats\2026-11-11\new-chat\_f0_check.png")
print("ok")
