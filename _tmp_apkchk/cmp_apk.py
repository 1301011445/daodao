# -*- coding: utf-8 -*-
"""比对：源 apk html / 打包进 apk 的 html 里，熊猫少女和魔法师少女到底是哪张图。"""
import re, io, base64, hashlib
from PIL import Image
WHO = ['橘猫少年','白兔少女','狐狸少女','熊猫少女','恐龙少女','企鹅少年','蓝发少女',
       '黑发少年','银发剑客','魔法师少女','古风少女','机械少年','白衫少年','青衫少女']
for tag, p in (('源', r'F:\Daodao\src\_apk\assets\dao.html'),
               ('apk内', r'F:\Daodao\_tmp_apkchk\dao.html')):
    html = io.open(p, encoding='utf-8', errors='ignore').read()
    print('== %s %d 字节 ==' % (tag, len(html)))
    faces = re.findall(r'"data:image/(webp|png);base64,([A-Za-z0-9+/=]+)"', html)
    print('   前 14 张：')
    for i in range(min(14, len(faces))):
        d = base64.b64decode(faces[i][1])
        im = Image.open(io.BytesIO(d))
        print('   %2d %-8s %-4s %s %6dB md5 %s' % (i, WHO[i], faces[i][0], im.size, len(d), hashlib.md5(d).hexdigest()[:10]))
    out = r'F:\Daodao\_tmp_apkchk\apk_face_%d.%s' % (3, 'webp')
    io.open(out, 'wb').write(base64.b64decode(faces[3][1]))
    out2 = r'F:\Daodao\_tmp_apkchk\apk_face_9.%s' % 'webp'
    io.open(out2, 'wb').write(base64.b64decode(faces[9][1]))

