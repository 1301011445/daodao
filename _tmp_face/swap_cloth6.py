import io,re,os,base64
from PIL import Image, ImageFilter
from collections import deque
base_p=r'F:\Daodao\_tmp_face\base93_dom.html'.replace('dom','dao'); src_p=r'F:\Daodao\src\_apk\assets\dao.html'; cloth=r'F:\Daodao\_tmp_face\cloth'
greens={'P0':'POSES_7_0.png','P1':'POSES_7_1.png','P2':'POSES_7_2.png','P3':'POSES_7_3.png'}
def keyout_green(im, tol=30, dark=95):
    w,h=im.size; px=im.load()
    cand=bytearray(w*h); seen=bytearray(w*h)
    for y in range(h):
        b=y*w
        for x in range(w):
            r,g,bb,a=px[x,y]
            if g-max(r,bb) > tol and min(r,bb) < dark: cand[b+x]=1
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
            r,g,bb,a=px[x,y]
            if seen[k]:
                op[x,y]=(0,0,0,0); continue
            ex=g-max(r,bb)
            # 去绿边：非背景但绿色轻微占优，压掉一点绿
            if ex>0: g=max(r,bb)
            op[x,y]=(r,g,bb,255)
    al=out.split()[-1].filter(ImageFilter.GaussianBlur(0.8)); out.putalpha(al)
    return out
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
    c=Image.new('RGBA',(ow,oh),(0,0,0,0)); c.paste(n2,(dx,dy),n2); return c
t={}
for tag,fn in greens.items():
    raw=Image.open(os.path.join(cloth,'g_%s.png'%tag)).convert('RGBA')
    out=norm(os.path.join(cloth,fn),keyout_green(raw))
    out.save(os.path.join(cloth,'final4_%s.png'%tag))
    hist=out.split()[-1].histogram(); print(tag,'透明 %.1f%%'%(sum(hist[:16])/(out.width*out.height)*100))
    buf=io.BytesIO(); out.save(buf,'PNG',optimize=True)
    t[tag]='data:image/png;base64,'+base64.b64encode(buf.getvalue()).decode('ascii')
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
io.open(src_p,'w',encoding='utf-8',newline='\n').write(cur); print('写回完成',len(cur))
from PIL import Image as I
rows=[('FACE','final2_FACE.png'),('P0','final4_P0.png'),('P1','final4_P1.png'),('P2','final4_P2.png'),('P3','final4_P3.png'),('P4','final2_P4.png')]
h=340; sc=[]
for tt,ff in rows:
    im=I.open(os.path.join(cloth,ff)).convert('RGBA'); k=h/im.height
    sc.append(im.resize((max(1,int(im.width*k)),h),I.LANCZOS))
W=sum(s.width for s in sc)+10*(len(sc)+1)
sheet=I.new('RGB',(W,h+20),(70,110,150)); x=10
for s in sc: sheet.paste(s,(x,10),s); x+=s.width+10
sheet.save(os.path.join(cloth,'sheet4.png')); print('sheet ok')
