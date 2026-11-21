# -*- coding: utf-8 -*-
from PIL import Image, ImageDraw, ImageFont
a = Image.open(r'F:\Daodao\src\桌面分身\_bundle\expr_3_sleep.png').convert('RGBA')
b = Image.open(r'F:\Daodao\_tmp_face\cur_F03.webp').convert('RGBA')
H = 400
def fit(im):
    k = H / float(im.height)
    return im.resize((max(1, int(im.width * k)), H), Image.LANCZOS)
a = fit(a); b = fit(b)
f = ImageFont.truetype(r'C:\Windows\Fonts\msyh.ttc', 16)
gap = 26
W = a.width + b.width + gap + 40
s = Image.new('RGB', (W, H + 46), (248, 250, 255))
s.paste(Image.new('RGB', a.size, (255, 255, 255)), (20, 38)); s.paste(a, (20, 38), a)
x2 = 20 + a.width + gap
s.paste(Image.new('RGB', b.size, (255, 255, 255)), (x2, 38)); s.paste(b, (x2, 38), b)
d = ImageDraw.Draw(s)
d.text((20, 10), '改前：睡着就变熊猫', font=f, fill=(150, 40, 40))
d.text((x2, 10), '改后：一直是本人', font=f, fill=(30, 90, 60))
s.save(r'F:\Daodao\_tmp_face\panda_before_after3.png')
print(s.size)
