from PIL import Image
for fn in [r'F:\Daodao\_tmp_face\cloth\POSES_7_4.png', r'F:\Daodao\_tmp_face\cloth\norm2_P4.png', r'F:\Daodao\_tmp_face\cloth\norm2_P0.png']:
    im=Image.open(fn).convert('RGBA')
    a=im.split()[-1]
    h=a.histogram()
    z=h[0]; full=h[255]
    print(fn, im.size, 'alpha=0 像素', z, 'alpha=255 像素', full, '总像素', im.width*im.height)
    print('  左上像素 RGBA', im.getpixel((0,0)), '中部', im.getpixel((im.width//2, im.height//2)))
