import io,urllib.request
from PIL import Image
u='https://aka.doubaocdn.com/s/EBVICTErfh'
fn=r'F:\Daodao\_tmp_face\cloth\raw_P4b.png'
io.open(fn,'wb').write(urllib.request.urlopen(u,timeout=40).read())
im=Image.open(fn).convert('RGBA')
a=im.split()[-1]; h=a.histogram()
print('size',im.size,'alpha0',h[0],'alpha255',h[255],'corner',im.getpixel((0,0)))
