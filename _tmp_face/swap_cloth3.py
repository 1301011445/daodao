import io,re,os,base64,urllib.request
from PIL import Image
from collections import deque
base_p=r'F:\Daodao\_tmp_face\base93_dao.html'
src_p=r'F:\Daodao\src\_apk\assets\dao.html'
cloth=r'F:\Daodao\_tmp_face\cloth'
urls={
 'FACE':('FACES_7.png','https://aka.doubaocdn.com/s/D7eJpSr0RB'),
 'P0':('POSES_7_0.png','https://aka.doubaocdn.com/s/vmgDuNm5MH'),
 'P1':('POSES_7_1.png','https://aka.doubaocdn.com/s/Znoxlg9DLI'),
 'P2':('POSES_7_2.png','https://aka.doubaocdn.com/s/XxU8XXRvD8'),
 'P3':('POSES_7_3.png','https://aka.doubaocdn.com/s/3teJzYDJmi'),
 'P4':('POSES_7_4.png','https://aka.doubaocdn.com/s/EBVICTErfh'),
}
def keyout(im, near=232):
    im=im.convert('RGBA'); w,h=im.size
    px=im.load()
    bg=bytearray(w*h)
    for y in range(h):
        base=y*w
        for x in range(w):
            r,g,b,a=px[x,y]
            bg[base+x]=1 if (r>=near and g>=near and b>=near) else 0
    seen=bytearray(w*h)
    dq=deque()
    for x in range(w):
        for y in (0,h-1):
            i=y*w+x
            if bg[i] and not seen[i]: seen[i]=1; dq.append(i)
    for y in range(h):
        for x in (0,w-1):
            i=y*w+x
            if bg[i] and not seen[i]: seen[i]=1; dq.append(i)
    while dq:
        i=dq.popleft(); y,x=divmod(i,w)
        for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
            nx,ny=x+dx,y+dy
            if 0<=nx<w and 0<=ny<h:
                j=ny*w+nx
                if bg[j] and not seen[j]: seen[j]=1; dq.append(j)
    keys=list(im.getdata())
    out=[]
    for k,(r,g,b,a) in enumerate(keys):
        out.append((r,g,b,0) if seen[k] else (r,g,b,255))
    n=Image.new('RGBA',(w,h)); n.putdata(out)
    return n
TH=128
def maskbox(im):
    a=im.convert('RGBA').split()[-1].point(lambda v:255 if v>=TH else 0)
    return a.getbbox()
def norm(orig,new,tag):
    o=Image.open(orig).convert('RGBA'); ow,oh=o.size
    bo=maskbox(o); bn=maskbox(new)
    bh_o=bo[3]-bo[1]; bh_n=bn[3]-bn[1]
    k=bh_o/bh_n
    n2=new.resize((max(1,int(new.width*k)),max(1,int(new.height*k))),Image.LANCZOS)
    b2=maskbox(n2)
    dx=int(round((bo[0]+bo[2])/2-(b2[0]+b2[2])/2)); dy=int(round(bo[3]-b2[3]))
    c=Image.new('RGBA',(ow,oh),(0,0,0,0)); c.paste(n2,(dx,dy),n2)
    print(tag,'原',o.size,bo,'| 新mask',bn,'-> 落位',maskbox(c))
    return c
t={}
for tag,(fn,u) in urls.items():
    raw=io.open(os.path.join(cloth,'k_%s.raw'%tag),'wb'); raw.write(urllib.request.urlopen(u,timeout=40).read()); raw.close()
    n=Image.open(os.path.join(cloth,'k_%s.raw'%tag))
    if tag!='FACE':
        n=keyout(n)
        a=n.split()[-1]; h=a.histogram(); print(tag,'抠后 透明像素',h[0],'/',n.width*n.height)
    else:
        n=n.convert('RGBA')
    out=norm(os.path.join(cloth,fn),n,tag)
    out.save(os.path.join(cloth,'final_%s.png'%tag))
    buf=io.BytesIO(); out.save(buf,'PNG',optimize=True)
    t[tag]='data:image/png;base64,'+base64.b64encode(buf.getvalue()).decode('ascii')
    print('  ',tag,'png',len(buf.getvalue()))
cur=io.open(base_p,encoding='utf-8').read()
def ri(cur,marker,idx,newuri):
    i=cur.find(marker); e=cur.find('];',i); seg=cur[i:e]
    ms=list(re.finditer(r'"(data:image/(?:png|jpeg);base64,[^"]+)"',seg)); m=ms[idx]
    return cur[:i+m.start(1)]+newuri+cur[i+m.end(1):]
cur=ri(cur,'var FACES = [',7,t['FACE'])
for k in range(5): cur=ri(cur,'var POSES_7 = [',k,t['P%d'%k])
io.open(src_p,'w',encoding='utf-8',newline='\n').write(cur)
print('写回完成',len(cur))
