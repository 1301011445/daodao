# -*- coding: utf-8 -*-
"""对比两端 html 里的立绘：桌面分身 vs apk assets，看熊猫/魔法师是不是同一个。"""
import re, io, base64, hashlib, os
from PIL import Image

WHO = ['橘猫少年','白兔少女','狐狸少女','熊猫少女','恐龙少女','企鹅少年','蓝发少女',
       '黑发少年','银发剑客','魔法师少女','古风少女','机械少年','白衫少年','青衫少女']
for tag, p in (('桌面', r'F:\Daodao\src\桌面分身\dao.html'), ('apk', r'F:\Daodao\src\_apk\assets\dao.html')):
    html = io.open(p, encoding='utf-8').read()
    faces = re.findall(r'"data:image/webp;base64,([A-Za-z0-9+/=]+)"', html)
    print('== %s：%d 张内嵌 ==' % (tag, len(faces)))
    for i in range(min(14, len(faces))):
        d = base64.b64decode(faces[i])
        im = Image.open(io.BytesIO(d))
        print('  %2d %-8s %s %6dB md5 %s' % (i, WHO[i], im.size, len(d), hashlib.md5(d).hexdigest()[:10]))
