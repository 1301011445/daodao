import glob, os, sys
from PIL import Image, ImageDraw

d = r'F:\Daodao\temp_ride'
frames = sorted(glob.glob(os.path.join(d, '_ride_mv*.png')))
crop = (80, 10, 300, 235)
scale = 2
w = (crop[2]-crop[0])*scale
h = (crop[3]-crop[1])*scale
ims = []
for f in frames:
    im = Image.open(f).convert('RGB').crop(crop).resize((w, h), Image.LANCZOS)
    ims.append(im)

# 横向拼条
pad = 6
sheet = Image.new('RGB', (w*len(ims) + pad*(len(ims)-1), h+26), (24,24,28))
dr = ImageDraw.Draw(sheet)
for i, im in enumerate(ims):
    x = i*(w+pad)
    sheet.paste(im, (x, 24))
    dr.text((x+4, 6), f'f{i}', fill=(230,230,230))
sheet.save(os.path.join(d, 'ride_sheet.png'))

# 动图（慢放：每帧 80ms）
ims[0].save(os.path.join(d, 'ride_anim.gif'), save_all=True, append_images=ims[1:], duration=80, loop=0)
print('OK', len(ims), w, h)
