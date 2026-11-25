# -*- coding: utf-8 -*-
"""2026-11-25 配图 3、4：多向站姿 / 手机界面（文案按实际状态写，不夸大）。"""
import os
from PIL import Image, ImageDraw, ImageFont

W, H, D = 1080, 1440, r"F:\Daodao\推广草稿"
f_t = ImageFont.truetype(r"C:\Windows\Fonts\msyhbd.ttc", 46)
f_s = ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", 28)


def canvas(title, sub):
    im = Image.new("RGB", (W, H), (13, 19, 34))
    d = ImageDraw.Draw(im)
    d.text((60, 66), title, font=f_t, fill=(232, 241, 255))
    d.text((62, 132), sub, font=f_s, fill=(140, 172, 214))
    return im, d


# 3. 多向站姿
im, d = canvas("同一只形象 · 多向站姿", "生成模型补出左45 / 正 / 右45，侧身和厚度有了")
src = Image.open(r"F:\Daodao\形象\_gen_3views_v2.png").convert("RGBA")
sh = 860
tw = min(1010, int(src.size[0] * sh / src.size[1]))
src = src.resize((tw, int(sh)), Image.LANCZOS)
im.paste(src, ((W - tw) // 2, 290), src)
d.text((62, 1210), "多视图已生成；程序里的朝向切换还没接上，列为下一步", font=f_s, fill=(160, 185, 218))
p3 = os.path.join(D, "2026-11-25-img3-views.png")
im.save(p3)

# 4. 手机界面
im, d = canvas("手机端主界面 · 五个按钮都在", "人物缩放 0.94× → 1.72×，头顶空出一大块的问题收了一半")
ui = Image.open(r"F:\Daodao\形象\_ui412d.png").convert("RGB")
uh = 1060
uw = int(ui.size[0] * uh / ui.size[1])
ui = ui.resize((uw, uh), Image.LANCZOS)
im.paste(ui, ((W - uw) // 2, 290))
p4 = os.path.join(D, "2026-11-25-img4-ui.png")
im.save(p4)
for p in (p3, p4):
    print(p, Image.open(p).size, os.path.getsize(p) // 1024, "KB")
