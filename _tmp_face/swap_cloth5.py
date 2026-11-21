import io,re,os,base64,urllib.request
from PIL import Image, ImageFilter
from collections import deque
base_p=r'F:\Daodao\_tmp_face\base93_dao.html'; src_p=r'F:\Daodao\src\_apk\assets\dao.html'; cloth=r'F:\Daodao\_tmp_face\cloth'
greens={
 'P0':('POSES_7_0.png','https://aka.doubaocdn.com/s/fyWi7L85RZ'),
 'P1':('POSES_7_1.png','https://aka.doubaocdn.com/s/n1houcPOj7'),
 'P2':('POSES_7_2.png','https://aka.doubaocdn.com/s/EoOtDBSzh4'),
 'P3':('POSES_7_3.png','https://aka.doubaocdn.com/s/1po4kWVpik'),
}
def keyout_green(im, tol=24):
    w,h=im.size; px=im.load()
    cand=bytearray(w*h); seen=bytearray(w*h)
    for y in range(h):
        b=y*w
        for x in range(w):
            r,g,bb,a=px[x,y]
            if g-max(r,bb) > tol: cand[b+x]=1
    dq=deque()
    for x in range(w):
        for y in (0,h-1):
            i=y*w+x
            if cand[i]: seen[i]=1; dq.append(i)
    for y in range(h):
        for x in (0,w-1):
            i=y*w+x
            if cand[i] and not seen[i]: seen[i]=1; dq.append(i)
    while dq:
        i=dq.popleft(); y,x=divmod(i,w)
        for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
            nx,ny=x+dx,y+dy
            if 0<=nx<w and 0<=ny<h:
                j=ny*w+nx
                if cand[j] and not seen[j]: seen[j]=1; dq.append(j)
    out=Image.new('RGBA',(w,h)); op=out.load()
    for y in range(h):
        b=y*w
        for x in range(w):
            k=b+x
            if seen[k]:
                op[x,y]=(0,0,0,0)
            else:
                r,g,bb,a=px[x,y]
                ex=g-max(r,bb)
                al=255 if ex<=0 else max(0,int(255*(1-ex/tol)))
                op[x,y]=(r,g,bb,al)
    al=out.split()[-1].filter(ImageFilter.GaussianBlur(0.8))
    out.putalpha(al); return out
TH=128
def maskbox(im):
    a=im.convert('RGBA').split()[-1].point(lambda v:255 if v>=TH else 0); return a.getbbox()
def norm(orig,new):
    o=Image.open(orig).convert('RGBA'); ow,oh=o.size
    bo=maskbox(o); bn=maskbox(new)
    bh_o=bo[3]-bo[1]; bh_n=bn[3]-bn[1]; k=bh_o/bh_n
    n2=new.resize((max(1,int(new.width*k)),max(1,int(new.height*k))),Image.LANCZOS)
    b2=maskbox(n2)
    dx=int(round((bo[0]+bo[2])/2-(b2[0]+b2[2])/2)); dy=int(round(bo[3]-b2[3]))
    c=Image.new('RGBA',(ow,oh),(0,0,0,0)); c.paste(n2,(dx,dy),n2)
    return c
t={}
for tag,(fn,u) in greens.items():
    p=os.path.join(cloth,'g_%s.png'%tag); io.open(p,'wb').write(urllib.request.urlopen(u,timeout=40).read())
    out=norm(os.path.join(cloth,fn),keyout_green(Image.open(p).convert('RGBA')))
    out.save(os.path.join(cloth,'final3_%s.png'%tag))
    hist=out.split()[-1].histogram()
    print(tag,'绿幕抠后透明 %.1f%%'%(sum(hist[:16])/(out.width*out.height)*100))
    buf=io.BytesIO(); out.save(buf,'PNG',optimize=True)
    t[tag]='data:image/png;base64,'+base64.b64encode(buf.getvalue()).decode('ascii')
# P4 沿用白色版结果
for tag,srcf in (('P4','final2_P4.png'),('FACE','final2_FACE.png')):
    im=Image.open(os.path.join(cloth,srcf)).convert('RGBA')
    buf=io.BytesIO(); im.save(buf,'PNG',optimize=True)
    t[tag]='data:image/png;base64,'+base64.b64encode(buf.getvalue()).decode('ascii')
cur=io.open(base_p,encoding='utf-8').read()
def ri(cur,marker,idx,newuri):
    i=cur.find(marker); e=cur.find('];',i); seg=cur[i:e]
    ms=list(re.finditer(r'"(data:image/(?:png|jpeg);base64,[^"]+)"',seg)); m=ms[idx]
    return cur[:i+m.start(1)]+newuri+cur[i+m.end(1):]
cur=ri(cur,'var FACES = [',7,t['FACE'])
for k in range(5): cur=ri(cur,'var POSES_7 = [',k,t['P%d'%k])
io.open(src_p,'w',encoding='utf-8',newline='\n').write(cur)
print('写回完成',len(cur))
