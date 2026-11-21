# -*- coding: utf-8 -*-
"""查 14 张立绘的 webp 编码格式：哪张是 VP8L/VP8X，哪张是普通有损 VP8。"""
import re, io, base64
from PIL import Image
HTML = r'F:\Daodao\src\_apk\assets\dao.html'
html = io.open(HTML, encoding='utf-8').read()
faces = [m[1] for m in re.findall(r'"data:image/(webp|png);base64,([A-Za-z0-9+/=]+)"', html)]
WHO = ['橘猫少年','白兔少女','狐狸少女','熊猫少女','恐龙少女','企鹅少年','蓝发少女',
       '黑发少年','银发剑客','魔法师少女','古风少女','机械少年','白衫少年','青衫少女']
for i in range(14):
    d = base64.b64decode(faces[i])
    riff = d[:4]
    chunks = []
    pos = 12
    while pos + 8 <= len(d):
        fourcc = d[pos:pos + 4].decode('ascii', 'ignore')
        size = int.from_bytes(d[pos + 4:pos + 8], 'little')
        chunks.append(fourcc.strip())
        pos += 8 + size + (size & 1)
        if size == 0 and fourcc == 'VP8X':
            pass
    im = Image.open(io.BytesIO(d))
    print('%2d %-8s %-5s %s size=%-9s chunks=%s' % (i, WHO[i], riff.decode('ascii','ignore'), im.size, len(d), '/'.join(chunks)))
