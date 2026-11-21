# -*- coding: utf-8 -*-
"""全部内嵌图拼成一张带编号的联系表，先看清哪个位置是卡通熊猫。"""
import re, io, base64
from PIL import Image, ImageDraw
HTML = r'F:\Daodao\src\_apk\assets\dao.html'
html = io.open(HTML, encoding='utf-8').read()
items = [(m[0], m[1]) for m in re.findall(r'"data:image/(webp|png);base64,([A-Za-z0-9+/=]+)"', html)]
print('共 %d 张' % len(items))
cell_w, cell_h, cols = 112, 176, 10
rows = (len(items) + cols - 1) // cols
sheet = Image.new('RGB', (cols * cell_w, rows * cell_h), (24, 26, 34))
dr = ImageDraw.Draw(sheet)
for i, (ext, b64) in enumerate(items):
    try:
        im = Image.open(io.BytesIO(base64.b64decode(b64))).convert('RGBA')
        im.thumbnail((cell_w - 12, cell_h - 26))
        x = (i % cols) * cell_w + (cell_w - im.width) // 2
        y = (i // cols) * cell_h + 18
        bg = Image.new('RGBA', im.size, (232, 236, 244, 255))
        bg.alpha_composite(im)
        sheet.paste(bg.convert('RGB'), (x, y))
    except Exception:
        dr.text(((i % cols) * cell_w + 8, (i // cols) * cell_h + 60), 'ERR', fill=(255, 120, 120))
    dr.text(((i % cols) * cell_w + 6, (i // cols) * cell_h + 3), str(i), fill=(255, 230, 140))
sheet.save(r'F:\Daodao\_tmp_face\all_faces_sheet.png')
print('联系表已写：', sheet.size)
