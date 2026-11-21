import io,re,os,base64,urllib.request
from PIL import Image
src_p=r'F:\Daodao\src\_apk\assets\dao.html'
cloth=r'F:\Daodao\_tmp_face\cloth'
urls={
 'FACE':(os.path.join(cloth,'FACES_7.png'),'https://aka.doubaocdn.com/s/D7eJpSr0RB'),
 'P0':(os.path.join(cloth,'POSES_7_0.png'),'https://aka.doubaocdn.com/s/qG4EbLj8QT'),
 'P1':(os.path.join(cloth,'POSES_7_1.png'),'https://aka.doubaocdn.com/s/uUddKIOVjH'),
 'P2':(os.path.join(cloth,'POSES_7_2.png'),'https://aka.doubaocdn.com/s/zqdcFt0A5t'),
 'P3':(os.path.join(cloth,'POSES_7_3.png'),'https://aka.doubaocdn.com/s/GflEWGbYES'),
 'P4':(os.path.join(cloth,'POSES_7_4.png'),'https://aka.doubaocdn.com/s/lZAUMSxzTP'),
}
def bbox(im):
    a=im.convert('RGBA').split()[-1]
    return a.getbbox()
def norm(orig_path,url,tag):
    o=Image.open(orig_path).convert('RGBA')
    raw=urllib.request.urlopen(url,timeout=40).read()
    tmp=os.path.join(cloth,'raw_%s.png'%tag)
    io.open(tmp,'wb').write(raw)
    n=Image.open(tmp).convert('RGBA')
    bo=bbox(o); bn=bbox(n)
    print(tag,'orig',o.size,'bbox',bo,'| new',n.size,'bbox',bn)
    if not bo or not bn: return o
    ow,oh=o.size; bw_o=bo[2]-bo[0]; bh_o=bo[3]-bo[1]
    bw_n=bn[2]-bn[0]; bh_n=bn[3]-bn[1]
    k=bh_o/bh_n
    nw=int(n.width*k); nh=int(n.height*k)
    n2=n.resize((nw,nh),Image.LANCZOS)
    b2=bbox(n2)
    # 目标：新图人的脚底 = 原图人的脚底；左右中心对齐
    cx_o=(bo[0]+bo[2])/2; cx_n=(b2[0]+b2[2])/2
    dx=int(round(cx_o-cx_n)); dy=int(round(bo[3]-b2[3]))
    canvas=Image.new('RGBA',(ow,oh),(0,0,0,0))
    canvas.paste(n2,(dx,dy),n2)
    # 落到原尺寸后校对 bbox 高度误差
    b3=bbox(canvas)
    print('   normalized bbox',b3,'目标',bo)
    out=os.path.join(cloth,'norm_%s.png'%tag)
    canvas.save(out)
    return canvas
def datauri(im):
    buf=io.BytesIO(); im.save(buf,'PNG',optimize=True)
    return 'data:image/png;base64,'+base64.b64encode(buf.getvalue()).decode('ascii'), len(buf.getvalue())
targets={}
for tag,(p,u) in urls.items():
    target=norm(p,u,tag)
    du,bn=datauri(target)
    targets[tag]=du
    print(tag,'新 png 字节',bn,'data uri 长度',len(du))
src=io.open(src_p,encoding='utf-8').read()
def swap(marker,idx,newuri):
    i=src.find(marker); seg_end=src.find('];',i)
    seg=src[i:seg_end]
    ms=list(re.finditer(r'"(data:image/(?:png|jpeg);base64,[^"]+)"',seg))
    m=ms[idx]
    return src[:i+m.start(1)] + newuri + src[i+m.end(1):]
s1=swap('var FACES = [',7,targets['FACE'])
s2=s1
for k in range(5):
    s2=swap('var POSES_7 = [',k,targets['P%d'%k]) if k==0 else s2
# 逐个替换姿势，需要每次重新定位
cur=s1
for k in range(5):
    i=cur.find('var POSES_7 = ['); seg_end=cur.find('];',i)
    seg=cur[i:seg_end]
    ms=list(re.finditer(r'"(data:image/(?:png|jpeg);base64,[^"]+)"',seg))
    m=ms[k]
    cur=cur[:i+m.start(1)] + targets['P%d'%k] + cur[i+m.end(1):]
io.open(src_p,'w',encoding='utf-8',newline='\n').write(cur)
print('写回完成，文件字节', len(cur))
