import numpy as np
from PIL import Image
from collections import deque

SRC = r'F:\Daodao\src\_apk\assets\walk8.png'
a = np.array(Image.open(SRC).convert('RGBA'))
H, W = a.shape[:2]
FR = 8
fw, fh = W // FR, H
out = a.copy()

def close_mask(m, it=1):
    for _ in range(it):
        d = m.copy()
        d[1:, :] |= m[:-1, :]; d[:-1, :] |= m[1:, :]
        d[:, 1:] |= m[:, :-1]; d[:, :-1] |= m[:, 1:]
        d[1:, 1:] |= m[:-1, :-1]; d[:-1, :-1] |= m[1:, 1:]
        d[1:, :-1] |= m[:-1, 1:]; d[:-1, 1:] |= m[1:, :-1]
        m = d
    return m

for k in range(FR):
    fr = a[:, k*fw:(k+1)*fw]
    r = fr[:, :, 0].astype(int); g = fr[:, :, 1].astype(int); b = fr[:, :, 2].astype(int)
    mx = np.maximum(np.maximum(r, g), b); mn = np.minimum(np.minimum(r, g), b)
    white = (mn >= 200) & ((mx - mn) <= 18)
    # 先把白的缝隙合一下，避免白鞋/白裙从缝里和底连上
    wc = close_mask(white, 1)
    seen = np.zeros((fh, fw), bool); q = deque()
    for x in range(fw):
        for y in (0, fh-1):
            if wc[y, x] and not seen[y, x]: seen[y, x] = True; q.append((y, x))
    for y in range(fh):
        for x in (0, fw-1):
            if wc[y, x] and not seen[y, x]: seen[y, x] = True; q.append((y, x))
    while q:
        y, x = q.popleft()
        for dy, dx in ((1,0),(-1,0),(0,1),(0,-1)):
            ny, nx = y+dy, x+dx
            if 0 <= ny < fh and 0 <= nx < fw and wc[ny, nx] and not seen[ny, nx]:
                seen[ny, nx] = True; q.append((ny, nx))
    bg = seen
    obj = ~bg
    d = obj.copy()
    edge = np.zeros_like(obj)
    edge[1:, :] |= obj[1:, :] & bg[:-1, :]
    edge[:-1, :] |= obj[:-1, :] & bg[1:, :]
    edge[:, 1:] |= obj[:, 1:] & bg[:, :-1]
    edge[:, :-1] |= obj[:, :-1] & bg[:, 1:]
    alpha = np.where(obj, 255, 0).astype(np.uint8)
    # 贴着底的一圈：按它有多白折算半透明，白边就淡下去不再是一道白墙
    halo = edge & ((mn > 205) | ((mx - mn) < 55))
    a_edge = np.clip((255 - mn) * 6, 90, 245).astype(np.uint8)
    alpha[halo] = a_edge[halo]
    fr2 = fr.copy(); fr2[:, :, 3] = alpha
    out[:, k*fw:(k+1)*fw] = fr2
    print('frame %d obj=%d halo=%d' % (k, int(obj.sum()), int(halo.sum())))

Image.fromarray(out).save(r'F:\Daodao\_walk8_clean.png')
pre = np.zeros((fh, fw*FR, 4), np.uint8); pre[:] = (34, 38, 47, 255)
clean = out
for k in range(FR):
    s = clean[:, k*fw:(k+1)*fw]; mm = s[:, :, 3] > 0
    pre[:, k*fw:(k+1)*fw][mm] = s[mm]
Image.fromarray(pre).save(r'C:\Users\LDY\Doubao\chats\2026-11-11\new-chat\浮窗_描边修复_预览.png')
print('done')
