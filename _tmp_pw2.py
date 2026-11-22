import ctypes
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception as e:
    print("dpi err",e)
from ctypes import wintypes
from PIL import Image
u=ctypes.windll.user32; gdi=ctypes.windll.gdi32
h=u.FindWindowW(None,"DaoPetWindow")
r=wintypes.RECT(); u.GetWindowRect(h,ctypes.byref(r))
w,hgt=r.right-r.left,r.bottom-r.top
print("rect",r.left,r.top,w,hgt)
hdc=u.GetWindowDC(h); mdc=gdi.CreateCompatibleDC(hdc)
bmp=gdi.CreateCompatibleBitmap(hdc,w,hgt); gdi.SelectObject(mdc,bmp)
ok=u.PrintWindow(h,mdc,2)
class BIH(ctypes.Structure):
    _fields_=[("biSize",ctypes.c_uint32),("biWidth",ctypes.c_int32),("biHeight",ctypes.c_int32),("biPlanes",ctypes.c_uint16),("biBitCount",ctypes.c_uint16),("biCompression",ctypes.c_uint32),("biSizeImage",ctypes.c_uint32),("biXPelsPerMeter",ctypes.c_int32),("biYPelsPerMeter",ctypes.c_int32),("biClrUsed",ctypes.c_uint32),("biClrImportant",ctypes.c_uint32)]
bi=BIH(); bi.biSize=ctypes.sizeof(bi); bi.biWidth=w; bi.biHeight=-hgt; bi.biPlanes=1; bi.biBitCount=32
buf=ctypes.create_string_buffer(w*hgt*4)
gdi.GetDIBits(mdc,bmp,0,hgt,buf,ctypes.byref(bi),0)
im=Image.frombuffer("RGBA",(w,hgt),buf,"raw","BGRA",0,1).convert("RGB")
im.save(r"F:\Daodao\_tmp_petwindow2.png")
cols=sorted(im.getcolors(maxcolors=1000000),reverse=True)
print("ok",ok,"top",cols[:4])