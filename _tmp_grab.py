from PIL import ImageGrab
im=ImageGrab.grab(bbox=(253,168,633,373))
im.save(r"F:\Daodao\_tmp_petregion.png")
cols=im.convert("RGB").getcolors(maxcolors=1000000)
cols.sort(reverse=True)
print("top colors:", cols[:8])