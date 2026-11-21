import io,os,urllib.request,shutil
from PIL import Image, ImageFilter, ImageOps
from collections import deque
cloth=r'F:\Daodao\_tmp_face\cloth'; bundle=r'F:\Daodao\src\桌面分身\_bundle'
def dl(url,name):
    p=os.path.join(cloth,name)
    if not os.path.exists(p):
        io.open(p,'wb').write(urllib.request.urlopen(url,timeout=40).read())
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
            if seen[k]: op[x,y]=(0,0,0,0)
            else:
                if g>max(r,bb): g=max(r,bb)
                op[x,y]=(r,g,bb,255)
    out.putalpha(out.split()[-1].filter(ImageFilter.GaussianBlur(0.6)))
    return out
TH=128
def mbox(im):
    return im.split()[-1].point(lambda v:255 if v>=TH else 0).getbbox()
def place(new, target_path):
    o=Image.open(target_path).convert('RGBA'); ow,oh=o.size
    bn=mbox(new)
    k=oh/(bn[3]-bn[1])
    n2=new.resize((max(1,int(new.width*k)),max(1,int(new.height*k))),Image.LANCZOS)
    b2=mbox(n2)
    c=Image.new('RGBA',(ow,oh),(0,0,0,0))
    c.paste(n2,(int(round(ow/2-(b2[0]+b2[2])/2)), oh-b2[3]), n2)
    c.save(target_path); return c.size
srcs={
 'face_7.png':('FACE',None),
 'pose_7_stand.png':('P0',None),
 'pose_7_wave.png':('P1',None),
 'pose_7_walk.png':('P2',None),
 'pose_7_cheer.png':('P3',None),
 'pose_7_sit.png':('P4',None),
 'expr_7_happy.png':('E1','https://aka.doubaocdn.com/s/nVzuzD9lQG'),
 'expr_7_angry.png':('E2','https://aka.doubaocdn.com/s/a7fmbPKib0'),
 'expr_7_sad.png':('E3','https://aka.doubaocdn.com/s/IUPgUmV7Oe'),
 'expr_7_sleep.png':('E4','https://aka.doubaocdn.com/s/r9jdJjxP8T'),
 'walk8_7_3.png':('W3','https://aka.doubaocdn.com/s/NPQsdE9j0K'),
 'walk8_7_4.png':('W4','https://aka.doubaocdn.com/s/isQodX4k8L'),
}
fins={'FACE':'final2_FACE.png','P0':'final3_P0.png','P1':'final3_P1.png','P2':'final3_P2.png','P3':'final3_P3.png','P4':'final2_P4.png'}
for fn,(tag,u) in srcs.items():
    if tag in fins: im=Image.open(os.path.join(cloth,fins[tag]).convert('RGBA') if False else os.path.join(cloth,fins[tag])).convert('RGBA')
    else: im=keygreen(dl(u,'b_%s.png'%tag))
    print(fn, place(im, os.path.join(bundle,fn)))
# 走路帧1/2 = 新图，5-8 = 1-4 水平镜像
w1=keygreen(dl('https://aka.doubaocdn.com/s/Fv2h27TXVp','b_W1.png'))
w2=keygreen(dl('https://aka.doubaocdn.com/s/3wE12JeOCj','b_W2.png'))
print('walk1', place(w1, os.path.join(bundle,'walk8_7_1.png')))
print('walk2', place(w2, os.path.join(bundle,'walk8_7_2.png')))
print('walk5', place(ImageOps.mirror(w1), os.path.join(bundle,'walk8_7_5.png')))
print('walk6', place(ImageOps.mirror(w2), os.path.join(bundle,'walk8_7_6.png')))
print('walk7', place(ImageOps.mirror(keygreen(dl('https://aka.doubaocdn.com/s/NPQsdE9j0K','b_W3.png'))), os.path.join(bundle,'walk8_7_7.png')))
print('walk8', place(ImageOps.mirror(keygreen(dl('https://aka.doubaocdn.com/s/isQodX4k8L','b_W4.png'))), os.path.join(bundle,'walk8_7_8.png')))
# 对照图
tags=['face_7.png','pose_7_stand.png','pose_7_wave.png','pose_7_walk.png','pose_7_cheer.png','pose_7_sit.png','expr_7_happy.png','expr_7_angry.png','expr_7_sad.png','expr_7_sleep.png','walk8_7_1.png','walk8_7_3.png']
h=300; sc=[]
for t in tags:
    im=Image.open(os.path.join(bundle,t)).convert('RGBA'); k=h/im.height
    sc.append(im.resize((max(1,int(im.width*k)),h),Image.LANCZOS))
W=sum(x.width for x in sc)+8*(len(sc)+1)
sh=Image.new('RGB',(W,h+16),(60,100,140)); x=8
for s in sc: sh.paste(s,(x,8),s); x+=s.width+8
sh.save(os.path.join(cloth,'bundle_new.png')); print(sh.size)
