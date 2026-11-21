# -*- coding: utf-8 -*-
"""桌面 _bundle 的 14 张立绘拼联系表，跟手机端对照。"""
import os
from PIL import Image, ImageDraw
D = r'F:\Daodao\src\桌面分身\_bundle'
cell_w, cell_h, n = 110, 300, 14
sheet = Image.new('RGB', (n * cell_w, cell_h + 20), (24, 26, 34))
dr = ImageDraw.Draw(sheet)
for i in range(n):
    p = os.path.join(D, 'face_%d.png' % i)
    if not os.path.exists(p):
        continue
    im = Image.open(p).convert('RGBA')
    k = (cell_h - 24) / im.height
    im = im.resize((max(1, int(im.width * k)), cell_h - 24), Image.LANCZOS)
    x = i * cell_w + (cell_w - im.width) // 2
    bg = Image.new('RGBA', im.size, (232, 236, 244, 255))
    bg.alpha_composite(im)
    sheet.paste(bg.convert('RGB'), (x, 18))
    dr.text((i * cell_w + 4, 2), 'face_%d' % i, fill=(255, 230, 140))
sheet.save(r'F:\Daodao\_tmp_face\desktop_faces_sheet.png')
print(sheet.size)
