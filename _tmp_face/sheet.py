from PIL import Image
rows=[('FACE','final2_FACE.png'),('P0','final3_P0.png'),('P1','final3_P1.png'),('P2','final3_P2.png'),('P3','final3_P3.png'),('P4','final2_P4.png')]
h=340; scaled=[]
for t,f in rows:
    im=Image.open(r'F:\Daodao\_tmp_face\cloth\%s'%f).convert('RGBA')
    k=h/im.height; scaled.append(im.resize((max(1,int(im.width*k)),h),Image.LANCZOS))
W=sum(s.width for s in scaled)+10*(len(scaled)+1)
sheet=Image.new('RGB',(W,h+20),(70,110,150))
x=10
for s in scaled:
    sheet.paste(s,(x,10),s); x+=s.width+10
sheet.save(r'F:\Daodao\_tmp_face\cloth\sheet3.png'); print(sheet.size)
