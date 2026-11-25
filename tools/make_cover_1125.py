# -*- coding: utf-8 -*-
"""2026-11-25 小红书封面 v2：上面标题，中间立绘，下面是压暗的信息条（不压人物脚）。"""
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

OUT = r"F:\Daodao\推广草稿\2026-11-25-v116e-cover.png"
W, H = 1080, 1440
BG1, BG2 = (16, 24, 44), (8, 11, 22)

img = Image.new("RGB", (W, H), BG1)
d = ImageDraw.Draw(img)
for y in range(H):
    t = y / H
    d.line([(0, y), (W, y)], fill=tuple(int(BG1[i] * (1 - t) + BG2[i] * t) for i in range(3)))

glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
gd = ImageDraw.Draw(glow)
gd.ellipse((W * 0.10, H * 0.22, W * 1.02, H * 0.92), fill=(70, 110, 190, 60))
img = Image.alpha_composite(img.convert("RGBA"), glow.filter(ImageFilter.GaussianBlur(80))).convert("RGB")

f1 = ImageFont.truetype(r"C:\Windows\Fonts\msyhbd.ttc", 96)
f2 = ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", 42)
f3 = ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", 28)
f4 = ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", 26)

d = ImageDraw.Draw(img)
d.text((66, 78), "桌宠「道」", font=f1, fill=(238, 244, 255))
d.text((68, 200), "站着面向你 · 走路不再乱抖", font=f2, fill=(155, 195, 250))

# 标签放标题下方，别去挤人物
for i, tag in enumerate(["#桌宠", "#独立开发", "#AIGC"]):
    x = 68 + i * 190
    d.rounded_rectangle((x, 268, x + 168, 316), radius=24, fill=(88, 128, 208),
                        outline=(130, 172, 245), width=2)
    d.text((x + 20, 276), tag, font=f4, fill=(232, 241, 255))

# 立绘：高度压到 0.60H，脚底落在信息条上方
art = Image.open(r"F:\Daodao\src\_apk\assets\stand_6.png").convert("RGBA")
ah = int(H * 0.60)
aw = max(1, int(art.size[0] * ah / art.size[1]))
art = art.resize((aw, ah), Image.LANCZOS)
base = img.convert("RGBA")
base.alpha_composite(art, ((W - aw) // 2, H - ah - 170))
img = base.convert("RGB")

# 底部信息条：压暗一层，字压在条上而不是人物身上
bar = Image.new("RGBA", (W, 150), (6, 9, 18, 205))
img = Image.alpha_composite(img.convert("RGBA"), Image.new("RGBA", (W, H), (0, 0, 0, 0)))
c = img.convert("RGBA")
c.alpha_composite(bar, (0, H - 150))
img = c.convert("RGB")

d = ImageDraw.Draw(img)
d.text((66, H - 116), "自研 C# 桌宠 + Android 悬浮窗", font=f3, fill=(206, 220, 244))
d.text((66, H - 72), "形象用生成模型 · 动作逐帧调 · 音乐链路自修", font=f3, fill=(150, 170, 205))

img.save(OUT)
print(OUT, img.size, os.path.getsize(OUT) // 1024, "KB")
