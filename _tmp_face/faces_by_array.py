# -*- coding: utf-8 -*-
"""按 FACES 数组本身取图（不是全文正则），并把 14 张各导一份，确认谁是谁。"""
import re, io, base64, os
from PIL import Image
HTML = r'F:\Daodao\src\_apk\assets\dao.html'
OUT = r'F:\Daodao\_tmp_face\faces2'
os.makedirs(OUT, exist_ok=True)
html = io.open(HTML, encoding='utf-8').read()
i0 = html.index('var FACES = [')
i1 = html.index('];', i0)
block = html[i0:i1]
items = re.findall(r'"data:image/(webp|png);base64,([A-Za-z0-9+/=]+)"', block)
WHO = ['橘猫少年','白兔少女','狐狸少女','熊猫少女','恐龙少女','企鹅少年','蓝发少女',
       '黑发少年','银发剑客','魔法师少女','古风少女','机械少年','白衫少年','青衫少女']
print('FACES 条目 %d' % len(items))
for i, (ext, b64) in enumerate(items):
    d = base64.b64decode(b64)
    p = os.path.join(OUT, 'F%02d.%s' % (i, 'webp' if ext == 'webp' else 'png'))
    io.open(p, 'wb').write(d)
    im = Image.open(io.BytesIO(d))
    print('%2d %-8s %s %s %6dB' % (i, WHO[i] if i < len(WHO) else '?', ext, im.size, len(d)))
