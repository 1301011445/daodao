import io,re,os,base64,urllib.request
from PIL import Image, ImageChops
base_p=r'F:\Daodao\_tmp_face\base93_dao.html'
src_p=r'F:\Daodao\src\_apk\assets\dao.html'
cloth=r'F:\Daodao\_tmp_face\cloth'
urls={
 'FACE':('FACES_7.png','https://aka.doubaocdn.com/s/D7eJpSr0RB'),
 'P0':('POSES_7_0.png','https://aka.doubaocdn.com/s/qG4EbLj8QT'),
 'P1':('POSES_7_1.png','https://aka.doubaocdn.com/s/uUddKIOVjH'),
 'P2':('POSES_7_2.png','https://aka.doubaocdn.com/s/zqdcFt0A5t'),
 'P3':('POSES_7_3.png','https://aka.doubaocdn.com/s/GflEWGbYES'),
 'P4':('POSES_7_4.png','https://aka.doubaocdn.com/s/lZAUMSxzTP'),
}
TH=128
def maskbox(im):
    a=im.convert('RGBA').split()[-1].point(lambda v: 255 if v>=TH else 0)
    return a.getbbox(), a
def norm(orig_path,url,tag):
    o=Image.open(orig_path).convert('RGBA'); ow,oh=o.size
    raw=urllib.request.urlopen(url,timeout=40).read()
    tmp=os.path.join(cloth,'raw_%s.png'%tag); io.open(tmp,'wb').write(raw)
    n=Image.open(tmp).convert('RGBA')
    bo,_=maskbox(o); bn,_=maskbox(n)
    print(tag,'orig',o.size,'mask',bo,'| new',n.size,'mask',bn)
    bh_o=bo[3]-bo[1]; bh_n=bn[3]-bn[1]
    k=bh_o/bh_n
    n2=n.resize((int(n.width*k),int(n.height*k)),Image.LANCZOS)
    b2,_=maskbox(n2)
    cx_o=(bo[0]+bo[2])/2; cx_n=(b2[0]+b2[2])/2
    dx=int(round(cx_o-cx_n)); dy=int(round(bo[3]-b2[3]))
    canvas=Image.new('RGBA',(ow,oh),(0,0,0,0))
    canvas.paste(n2,(dx,dy),n2)
    b3,am=maskbox(canvas)
    corner=am.getpixel((0,0))
    print('   结果 mask',b3,'目标',bo,'角落 alpha',corner)
    out=os.path.join(cloth,'norm2_%s.png'%tag); canvas.save(out)
    return canvas
t={}
for tag,(fn,u) in urls.items():
    im=norm(os.path.join(cloth,fn),u,tag)
    buf=io.BytesIO(); im.save(buf,'PNG',optimize=True)
    t[tag]='data:image/png;base64,'+base64.b64encode(buf.getvalue()).decode('ascii')
    print(tag,'png 字节',len(buf.getvalue()))
cur=io.open(base_p,encoding='utf-8').read()
def replace_idx(cur,marker,idx,newuri):
    i=cur.find(marker); seg_end=cur.find('];',i); seg=cur[i:seg_end]
    ms=list(re.finditer(r'"(data:image/(?:png|jpeg);base64,[^"]+)"',seg))
    m=ms[idx]
    return cur[:i+m.start(1)]+newuri+cur[i+m.end(1):]
cur=replace_idx(cur,'var FACES = [',7,t['FACE'])
for k in range(5):
    cur=replace_idx(cur,'var POSES_7 = [',k,t['P%d'%k])
io.open(src_p,'w',encoding='utf-8',newline='\n').write(cur)
print('写回完成',len(cur))
