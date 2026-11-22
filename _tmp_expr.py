from PIL import Image
import os
for name in ["ball_happy","ball_sleep","ball_sur"]:
    im = Image.open(rf"F:\Daodao\_tmp_{name}.png").convert("RGBA")
    a = im.getchannel("A"); bbox = a.point(lambda v: 255 if v>8 else 0).getbbox()
    if bbox: im = im.crop(bbox)
    w,h = im.size; side = min(w,h)
    left = max(0,(w-side)//2)
    im = im.crop((left,0,left+side,side)).resize((320,320), Image.LANCZOS)
    im.save(rf"F:\Daodao\src\_apk\assets\{name}.png", optimize=True)
    print(name, im.size, round(os.path.getsize(rf"F:\Daodao\src\_apk\assets\{name}.png")/1024,1),"KB")
