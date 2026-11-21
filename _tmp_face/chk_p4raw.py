from PIL import Image
fn=r'F:\Daodao\_tmp_face\cloth\k_P4.raw'
im=Image.open(fn).convert('RGB')
for p in [(0,0),(3,3),(10,10),(600,40),(20,900),(700,1700),(1300,1750)]:
    print(p, im.getpixel(p))
mn=im.split()
print('min 通道直方图 前几档:', [mn[0].histogram()[i] for i in range(250,256)])
