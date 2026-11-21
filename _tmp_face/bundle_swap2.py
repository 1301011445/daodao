import io,os,re,base64,urllib.request
from PIL import Image, ImageFilter, ImageOps
from collections import deque
cloth=r'F:\Daodao\_tmp_face\cloth'; bundle=r'F:\Daodao\src\桌面分身\_bundle'
base_p=r'F:\Daodao\_tmp_face\base93_dao.html'; src_p=r'F:\Daodao\src\_apk\assets\dao.html'
def dl(url,name):
    p=os.path.join(cloth,name)
    if not os.path.exists(p): io.open(p,'wb').write(urllib.request.urlopen(url,timeout=40).read())
    return Image.open(p).convert('RGBA')
def keygreen(im,tol=30,dark=95):
    w,h=im.size; px=im.load(); cand=bytearray(w*h); seen=bytearray(w*h)
    for y in range(h):
        b=y*w
        for x in range(w):
            r,g,bb,a=px[x,y]
            if g-max(r,bb)>tol and min(r,bb)<dark: cand[b+x]=1
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
            k=b+x; r,g,bb,a=px[x,y]
            if seen[k]: op[x,y]=(r,g,bb,0)
            else:
                if g>max(r,bb): g=max(r,bb)
                op[x,y]=(r,g,bb,255)
    out.putalpha(out.split()[-1].filter(ImageFilter.GaussianBlur(0.6)))
    return out
def fill_holes(im):
    w,h=im.size; px=im.load(); al=im.split()[-1].load()
    trans=bytearray(w*h); outer=bytearray(w*h)
    for y in range(h):
        b=y*w
        for x in range(w):
            if al[x,y]<128: trans[b+x]=1
    dq=deque()
    for x in range(w):
        for y in (0,h-1):
            i=y*w+x
            if trans[i] and not outer[i]: outer[i]=1; dq.append(i)
    for y in range(h):
        for x in (0,w-1):
            i=y*w+x
            if trans[i] and not outer[i]: outer[i]=1; dq.append(i)
    while dq:
        i=dq.popleft(); y,x=divmod(i,w)
        for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
            nx,ny=x+dx,y+dy
            if 0<=nx<w and 0<=ny<h:
                j=ny*w+nx
                if trans[j] and not outer[j]: outer[j]=1; dq.append(j)
    filled=0
    for y in range(h):
        b=y*w
        for x in range(w):
            k=b+x
            if trans[k] and not outer[k]:
                r,g,bb,a=px[x,y]
                px[x,y]=(r,g,bb,255); filled+=1
    return im, filled
TH=128
def mbox(im): return im.split()[-1].point(lambda v:255 if v>=TH else 0).getbbox()
def norm_to(orig_path,new):
    o=Image.open(orig_path).convert('RGBA'); ow,oh=o.size
    bo=mbox(o); bn=mbox(new)
    k=(bo[3]-bo[1])/(bn[3]-bn[1])
    n2=new.resize((max(1,int(new.width*k)),max(1,int(new.height*k))),Image.LANCZOS)
    b2=mbox(n2)
    c=Image.new('RGBA',(ow,oh),(0,0,0,0))
    c.paste(n2,(int(round((bo[0]+bo[2])/2-(b2[0]+b2[2])/2)), int(round(bo[3]-b2[3]))), n2)
    return c
# 1) web 姿势 P0-P3 重做（保色、补洞、归一）
weburls={'P0':('POSES_7_0.png','https://aka.doubaocdn.com/s/fyWi7L85RZ'),
 'P1':('POSES_7_1.png','https://aka.doubaocdn.com/s/n1houcPOj7'),
 'P2':('POSES_7_2.png','https://aka.doubaocdn.com/s/EoOtDBSzh4'),
 'P3':('POSES_7_3.png','https://aka.doubaocdn.com/s/1po4kWVpik')}
t={}
for tag,(fn,u) in weburls.items():
    im=keygreen(dl(u,'g_%s.png'%tag))
    im,fh=fill_holes(im)
    out=norm_to(os.path.join(cloth,fn),im)
    out.save(os.path.join(cloth,'final5_%s.png'%tag))
    hist=out.split()[-1].histogram()
    print(tag,'补洞%d px'%fh,'透明 %.1f%%'%(sum(hist[:16])/(out.width*out.height)*100))
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
cur=cur.replace("HTML_VER='93'","HTML_VER='94'")
cur=ri(cur,'var FACES = [',7,t['FACE'])
for k in range(5): cur=ri(cur,'var POSES_7 = [',k,t['P%d'%k])
io.open(src_p,'w',encoding='utf-8',newline='\n').write(cur); print('web 写回',len(cur))
# 2) 桌面 bundle 重做
def place(new, target_path):
    o=Image.open(target_path).convert('RGBA'); ow,oh=o.size
    bn=mbox(new); k=oh/(bn[3]-bn[1])
    n2=new.resize((max(1,int(new.width*k)),max(1,int(new.height*k))),Image.LANCZOS)
    b2=mbox(n2)
    c=Image.new('RGBA',(ow,oh),(0,0,0,0))
    c.paste(n2,(int(round(ow/2-(b2[0]+b2[2])/2)), oh-b2[3]), n2)
    c.save(target_path); return c.size
for fn,tag in (('face_7.png','FACE'),('pose_7_stand.png','P0'),('pose_7_wave.png','P1'),('pose_7_walk.png','P2'),('pose_7_cheer.png','P3'),('pose_7_sit.png','P4')):
    sf='final2_%s.png'%tag if tag in ('FACE','P4') else 'final5_%s.png'%tag
    print(fn, place(Image.open(os.path.join(cloth,sf)).convert('RGBA'), os.path.join(bundle,fn)))
for fn,tag,u in (('expr_7_happy.png','E1','https://aka.doubaocdn.com/s/nVzuzD9lQG'),
 ('expr_7_angry.png','E2','https://aka.doubaocdn.com/s/a7fmbPKib0'),
 ('expr_7_sad.png','E3','https://aka.doubaocdn.com/s/IUPgUmV7Oe'),
 ('expr_7_sleep.png','E4','https://aka.doubaocdn.com/s/r9jdJjxP8T'),
 ('walk8_7_3.png','W3','https://aka.doubaocdn.com/s/NPQsdE9j0K'),
 ('walk8_7_4.png','W4','https://aka.doubaocdn.com/s/isQodX4k8L'),
 ('walk8_7_1.png','W1','https://aka.doubaocdn.com/s/Fv2h27TXVp'),
 ('walk8_7_2.png','W2','https://aka.doubaocdn.com/s/3wE12JeOCj')):
    im=keygreen(dl(u,'b_%s.png'%tag)); im,fh=fill_holes(im)
    print(fn,'补洞%d'%fh, place(im, os.path.join(bundle,fn)))
for src,dst,mir in (('walk8_7_1.png','walk8_7_5.png',True),('walk8_7_2.png','walk8_7_6.png',True),('walk8_7_3.png','walk8_7_7.png',True),('walk8_7_4.png','walk8_7_8.png',True)):
    im=Image.open(os.path.join(bundle,src)).convert('RGBA')
    if mir: im=ImageOps.mirror(im)
    im.save(os.path.join(bundle,dst))
print('bundle 完成')
tags=['face_7.png','pose_7_stand.png','pose_7_wave.png','pose_7_walk.png','pose_7_cheer.png','pose_7_sit.png','walk8_7_1.png','walk8_7_2.png','walk8_7_3.png','walk8_7_4.png','expr_7_happy.png','expr_7_angry.png']
h=300; sc=[]
for tt in tags:
    im=Image.open(os.path.join(bundle,tt)).convert('RGBA'); k=h/im.height
    sc.append(im.resize((max(1,int(im.width*k)),h),Image.LANCZOS))
W=sum(x.width for x in sc)+8*(len(sc)+1)
sh=Image.new('RGB',(W,h+16),(60,100,140)); x=8
for s in sc: sh.paste(s,(x,8),s); x+=s.width+8
sh.save(os.path.join(cloth,'bundle_new2.png')); print(sh.size)
