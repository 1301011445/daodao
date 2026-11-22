from PIL import Image
im = Image.open(r"F:\Daodao\src\_apk\assets\walk8.png").convert("RGBA")
W,H = im.size; FW = W//8; FH = H
fr = im.crop((0,0,FW,FH)); px = fr.load()
# 肤色：r>200, g 165-215, b 150-200, 且 r>b
xs=[]; ys=[]
for y in range(0, int(FH*0.42)):
    for x in range(FW):
        r,g,b,a = px[x,y]
        if a>60 and r>200 and 160<g<225 and 140<b<205 and r>b+18:
            xs.append(x); ys.append(y)
if xs:
    print("face bbox", min(xs), min(ys), max(xs), max(ys))
    cx = (min(xs)+max(xs))//2; hh = max(ys)-min(ys)
    print("face center x=", cx, " height=", hh)
    side = int(hh*1.55)
    print("square side=", side, " -> x0=", cx-side//2, " y0=", min(ys)-int(hh*0.35))
    print("as fractions: x0=%.3f y0=%.3f side=%.3f of fw/fh" % ((cx-side//2)/FW, (min(ys)-int(hh*0.35))/FH, side/FW))
