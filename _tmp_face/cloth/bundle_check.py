from PIL import Image
fs=[r'F:\Daodao\src\桌面分身\_bundle\face_7.png',r'F:\Daodao\src\桌面分身\_bundle\pose_7_stand.png',r'F:\Daodao\src\桌面分身\_bundle\walk8_7_1.png',r'F:\Daodao\src\桌面分身\_bundle\expr_7_happy.png',r'F:\Daodao\src\桌面分身\_bundle\pose_7_sit.png']
h=340; sc=[]
for f in fs:
    im=Image.open(f).convert('RGBA'); k=h/im.height
    sc.append(im.resize((max(1,int(im.width*k)),h),Image.LANCZOS))
W=sum(x.width for x in sc)+10*(len(sc)+1)
sh=Image.new('RGB',(W,h+20),(60,100,140)); x=10
for s in sc: sh.paste(s,(x,10),s); x+=s.width+10
sh.save(r'F:\Daodao\_tmp_face\cloth\bundle_check.png'); print(sh.size)
