# -*- coding: utf-8 -*-
"""桌面 48 张表情图（12 形象 × 4 情绪）拼联系表，看清哪些是「人形同角色」、哪些是「动物卡通」。"""
import os
from PIL import Image, ImageDraw
D = r'F:\Daodao\src\桌面分身\_bundle'
KEYS = ['happy', 'sad', 'angry', 'sleep']
cell_w, cell_h = 90, 200
sheet = Image.new('RGB', (cell_w * 12, cell_h * 4 + 24), (24, 26, 34))
dr = ImageDraw.Draw(sheet)
for i in range(12):
    for r, k in enumerate(KEYS):
        p = os.path.join(D, 'expr_%d_%s.png' % (i, k))
        x0, y0 = i * cell_w, r * cell_h + 20
        if not os.path.exists(p):
            dr.text((x0 + 6, y0 + 80), 'missing', fill=(255, 120, 120))
            continue
        im = Image.open(p).convert('RGBA')
        kk = (cell_h - 10) / im.height
        im = im.resize((max(1, int(im.width * kk)), cell_h - 10), Image.LANCZOS)
        bg = Image.new('RGBA', im.size, (232, 236, 244, 255))
        bg.alpha_composite(im)
        sheet.paste(bg.convert('RGB'), (x0 + (cell_w - im.width) // 2, y0))
        dr.text((x0 + 3, y0 + 2), '%d/%s' % (i, k), fill=(255, 230, 140))
sheet.save(r'F:\Daodao\_tmp_face\expr_sheet.png')
print(sheet.size)
