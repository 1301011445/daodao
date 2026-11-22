from PIL import Image
import numpy as np
im = Image.open(r"F:\Daodao\src\_apk\assets\ball_src.jpg").convert("RGB")
a = np.asarray(im).astype(np.int16)
# 近白背景→透明：四边连通用 flood
from collections import deque
h,w,_ = a.shape
mask = np.zeros((h,w),bool)
def nearwhite(y,x):
    r,g,b = a[y,x]
    return r>=232 and g>=232 and b>=232 and (max(r,g,b)-min(r,g,b))<=12
q=deque()
for x in range(w):
    for y in (0,h-1):
        if nearwhite(y,x) and not mask[y,x]: mask[y,x]=True; q.append((y,x))
for y in range(h):
    for x in (0,w-1):
        if nearwhite(y,x) and not mask[y,x]: mask[y,x]=True; q.append((y,x))
while q:
    y,x=q.popleft()
    for ny,nx in ((y-1,x),(y+1,x),(y,x-1),(y,x+1)):
        if 0<=ny<h and 0<=nx<w and not mask[ny,nx] and nearwhite(ny,nx):
            mask[ny,nx]=True; q.append((ny,nx))
out=np.dstack([np.asarray(im), np.where(mask,0,255).astype(np.uint8)])
img=Image.fromarray(out)
# 缩到 512 方形并轻微羽化边缘
img=img.resize((512,512), Image.LANCZOS)
img.save(r"F:\Daodao\src\_apk\assets\ball.png")
print("transparent ratio", float(mask.mean()))
