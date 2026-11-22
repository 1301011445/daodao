from PIL import Image, ImageFilter
im=Image.open(r"F:\Daodao\src\_apk\assets\ball_src.jpg")
print(im.mode, im.size)
im=im.convert("RGBA")
a=im.getchannel("A")
print("alpha extent", a.getextrema())
bbox=a.point(lambda v: 255 if v>8 else 0).getbbox()
print("bbox", bbox)
if bbox:
    im=im.crop(bbox)
# 裁成正方形（以脸部为中心偏上）
w,h=im.size
side=min(w,h)
left=max(0, (w-side)//2)
im=im.crop((left, 0, left+side, side)).resize((512,512), Image.LANCZOS)
im.save(r"F:\Daodao\src\_apk\assets\ball.png")
print("saved", im.size)
