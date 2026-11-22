import numpy as np
from PIL import Image

src = r'F:\Daodao\_tmp_peek2.png'
im = Image.open(src).convert('RGBA')
a = np.array(im)
al = a[:, :, 3].astype(int)
new_a = np.where(al > 18, 255, 0).astype(np.uint8)
# 边缘半透明保留原值，只是把极淡的噪点清掉
new_a[(al > 18) & (al < 60)] = al[(al > 18) & (al < 60)]
out = np.dstack([a[:, :, :3], new_a])
img = Image.fromarray(out)
bbox = img.getbbox()
img = img.crop(bbox)
w, h = img.size
scale = min(512.0 / w, 1024.0 / h)
nw, nh = int(round(w * scale)), int(round(h * scale))
img = img.resize((nw, nh), Image.LANCZOS)
canvas = Image.new('RGBA', (512, 1024), (0, 0, 0, 0))
canvas.alpha_composite(img, ((512 - nw) // 2, 1024 - nh))
canvas.save(r'F:\Daodao\src\_apk\assets\peek.png')
pre = Image.new('RGBA', canvas.size, (34, 38, 47, 255))
pre.alpha_composite(canvas)
pre.save(r'C:\Users\LDY\Doubao\chats\2026-11-11\new-chat\浮窗_探头扒框_预览.png')
px = np.array(canvas)
print('opaque frac', round(float((px[:, :, 3] > 40).mean()), 3), 'size', canvas.size)
print('left edge', round(float((px[:, 0:6, 3] > 40).mean()), 3))
