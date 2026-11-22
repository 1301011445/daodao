from PIL import Image
im=Image.open(r"F:\Daodao\src\_apk\assets\ball_src.jpg").convert("RGB")
px=im.load(); w,h=im.size
for pt in [(0,0),(w-1,0),(0,h-1),(w-1,h-1),(w//2,4),(20,h//2)]:
    print(pt, px[pt])
