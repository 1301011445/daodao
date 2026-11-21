# -*- coding: utf-8 -*-
"""修正 EXPRS：从 git 版原样取出 12 行，只把 4/5/8/9/10 五行换成桌面同一角色的表情图。"""
import io, os, re, base64
from PIL import Image

CUR = r'F:\Daodao\src\_apk\assets\dao.html'
HEAD = r'F:\Daodao\_tmp_face\gitver\dao_head.html'
BUNDLE = r'F:\Daodao\src\桌面分身\_bundle'
KEYS = ['happy', 'sad', 'angry', 'sleep']
EXPR_OK = [4, 5, 8, 9, 10]

def rows_of(text, head='var EXPRS = ['):
    i = text.index(head) + len(head)
    depth, i0, rows = 1, None, []
    while i < len(text):
        c = text[i]
        if c == '[':
            depth += 1
            if depth == 2:
                i0 = i + 1
        elif c == ']':
            if depth == 2 and i0 is not None:
                rows.append(text[i0:i])
                i0 = None
            depth -= 1
            if depth == 0:
                return rows, i + 2
        i += 1
    raise RuntimeError('EXPRS 括号没配平')

def span_of(text, head='var EXPRS = ['):
    i = text.index(head)
    depth = 0
    for j in range(i, len(text)):
        if text[j] == '[':
            depth += 1
        elif text[j] == ']':
            depth -= 1
            if depth == 0:
                return i, j + 2
    raise RuntimeError('no end')

def webp_b64(path, height, q):
    im = Image.open(path).convert('RGBA')
    k = height / float(im.height)
    im = im.resize((max(1, int(round(im.width * k))), height), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, 'WEBP', quality=q, method=6)
    return '"data:image/webp;base64,' + base64.b64encode(buf.getvalue()).decode('ascii') + '"'

head_rows, _ = rows_of(io.open(HEAD, encoding='utf-8').read())
print('git 版 EXPRS 行数', len(head_rows))
cur = io.open(CUR, encoding='utf-8').read()

new_rows = []
for r, row in enumerate(head_rows):
    if r in EXPR_OK:
        items = [webp_b64(os.path.join(BUNDLE, 'expr_%d_%s.png' % (r, k)), 380, 80) for k in KEYS]
        new_rows.append('  [' + ',\n   '.join(items) + ']')
    else:
        s = row.strip()
        s = re.sub(r'\s+', ' ', s)
        new_rows.append('  [' + s + ']')

a0, a1 = span_of(cur)
cur = cur[:a0] + 'var EXPRS = [\n' + ',\n'.join(new_rows) + '\n  ];' + cur[a1:]
io.open(CUR, 'w', encoding='utf-8', newline='').write(cur)
print('EXPRS 重建完成，页面 %.0f KB' % (len(cur.encode('utf-8')) / 1024.0))
