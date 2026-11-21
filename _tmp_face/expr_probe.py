# -*- coding: utf-8 -*-
"""数一数手机页面 EXPRS 有几行、每行几张、各多大。"""
import re, io, base64
from PIL import Image
HTML = r'F:\Daodao\src\_apk\assets\dao.html'
html = io.open(HTML, encoding='utf-8').read()
i0 = html.index('var EXPRS = [')
# 括号配平找出数组结尾
depth = 0
for i in range(i0, len(html)):
    c = html[i]
    if c == '[':
        depth += 1
    elif c == ']':
        depth -= 1
        if depth == 0:
            end = i + 1
            break
block = html[i0:end]
rows = re.findall(r'\[(.*?)\]', block, re.S)
print('EXPRS 行数', len(rows))
for r, row in enumerate(rows):
    items = re.findall(r'"data:image/(webp|png);base64,([A-Za-z0-9+/=]+)"', row)
    sizes = []
    for ext, b64 in items:
        im = Image.open(io.BytesIO(base64.b64decode(b64)))
        sizes.append('%dx%d' % im.size)
    print(' 行%2d 张数%d %s %d 字节' % (r, len(items), ' '.join(sizes), len(row)))
