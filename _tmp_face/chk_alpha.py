import io,urllib.request
from PIL import Image
u='https://aka.doubaocdn.com/s/D7eJpSr0RB'
raw=urllib.request.urlopen(u,timeout=30).read()
fn=r'F:\Daodao\_tmp_face\cloth\new_face.png'
io.open(fn,'wb').write(raw)
im=Image.open(fn)
print('size',im.size,'mode',im.mode)
if im.mode in ('RGBA','LA'):
    a=im.convert('RGBA').split()[-1]
    print('alpha corner',a.getpixel((0,0)),a.getpixel((im.width-1,0)))
    print('alpha min/max',a.getextrema())
else:
    print('无 alpha 通道，四角颜色',im.convert('RGB').getpixel((0,0)),im.convert('RGB').getpixel((im.width-1,im.height-1)))
