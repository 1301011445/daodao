# -*- coding: utf-8 -*-
"""把 dao.html 里内嵌的立绘拆成单张 webp，方便逐个检查/替换。"""
import re, os, base64, io
from PIL import Image

SRC = r'F:\Daodao\src\_apk\assets\dao.html'
OUT = r'F:\Daodao\_tmp_face\faces'
os.makedirs(OUT, exist_ok=True)
html = io.open(SRC, encoding='utf-8').read()
faces = re.findall(r'"data:image/webp;base64,([A-Za-z0-9+/=]+)"', html)
WHO = ['橘猫少年','白兔少女','狐狸少女','熊猫少女','恐龙少女','企鹅少年','蓝发少女',
       '黑发少年','银发剑客','魔法师少女','古风少女','机械少年','白衫少年','青衫少女']
print('内嵌立绘 %d 张' % len(faces))
for i, b64 in enumerate(faces):
    data = base64.b64decode(b64)
    p = os.path.join(OUT, 'f%02d.webp' % i)
    io.open(p, 'wb').write(data)
    im = Image.open(io.BytesIO(data))
    print('f%02d %-8s %s %5d B' % (i, WHO[i] if i < len(WHO) else '?', im.size, len(data)))
