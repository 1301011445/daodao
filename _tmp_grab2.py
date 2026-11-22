from PIL import ImageGrab
for name,box in (("phys",(380,252,950,560)),("log",(253,168,633,373))):
    im=ImageGrab.grab(bbox=box)
    im.save(r"F:\Daodao\_tmp_pet_%s.png"%name)
    cols=sorted(im.convert("RGB").getcolors(maxcolors=1000000),reverse=True)
    print(name,"size",im.size,"top",cols[:4])