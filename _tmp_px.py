from PIL import Image
p = r"F:\Daodao\src\_apk\assets\walk8.png"
im = Image.open(p).convert("RGBA")
W,H = im.size
print("size", W, H, "frames", W//8)
px = im.load()
# 背景色估计：左上角
print("corner", px[0,0], px[W-1,0], px[0,H-1])
# 第0帧非白占比与 bbox
fw = W//8
def bbox(f):
    x0,y0,x1,y1 = fw, H, 0, 0
    n = 0
    for y in range(0,H,2):
        for x in range(f*fw, (f+1)*fw, 2):
            r,g,b,a = px[x,y]
            if a > 20 and not (r>240 and g>240 and b>240):
                n += 1
                if x<x0: x0=x
                if y<y0: y0=y
                if x>x1: x1=x
                if y>y1: y1=y
    return (x0,y0,x1,y1,n)
b = bbox(0)
print("frame0 bbox(rel)", b[0]-0, b[1], b[2], b[3], "count", b[4])
print("head guess: x", b[0], "-", b[2], " y", b[1], "-", b[1]+(b[3]-b[1])//3)
# 背景是否纯白
w = sum(1 for y in range(0,H,4) for x in range(0,W,4) if px[x,y][3]>20 and px[x,y][:3]>(240,240,240))
tot = sum(1 for y in range(0,H,4) for x in range(0,W,4) if px[x,y][3]>20)
print("white-ish ratio", round(w/max(1,tot),3))
