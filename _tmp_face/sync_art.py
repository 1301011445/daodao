# -*- coding: utf-8 -*-
"""把手机端的立绘和「能换表情的五只」的表情图换成桌面同一套高清手办图（webp），
其余形象的表情套不动（页面已按白名单不启用）。"""
import io, os, re, base64
from PIL import Image

HTML = r'F:\Daodao\src\_apk\assets\dao.html'
BUNDLE = r'F:\Daodao\src\桌面分身\_bundle'
KEYS = ['happy', 'sad', 'angry', 'sleep']
EXPR_OK = [4, 5, 8, 9, 10]

def webp_bytes(path, height, q):
    im = Image.open(path).convert('RGBA')
    k = height / float(im.height)
    im = im.resize((max(1, int(round(im.width * k))), height), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, 'WEBP', quality=q, method=6)
    return buf.getvalue()

def enc(b):
    return '"data:image/webp;base64,' + base64.b64encode(b).decode('ascii') + '"'

html = io.open(HTML, encoding='utf-8').read()

def block_range(text, head):
    i0 = text.index(head)
    depth = 0
    for i in range(i0, len(text)):
        if text[i] == '[':
            depth += 1
        elif text[i] == ']':
            depth -= 1
            if depth == 0:
                return i0, i + 2          # 含 ];
    raise RuntimeError('找不到 ' + head)

# --- FACES：14 张全部换桌面高清图 ---
total_new = 0
face_lines = []
for i in range(14):
    b = webp_bytes(os.path.join(BUNDLE, 'face_%d.png' % i), 420, 82)
    total_new += len(b)
    face_lines.append('    ' + enc(b))
a0, a1 = block_range(html, 'var FACES = [')
html = html[:a0] + 'var FACES = [\n' + ',\n'.join(face_lines) + '\n  ];' + html[a1:]

# --- EXPRS：只换 4/5/8/9/10 五行，其余保留原样 ---
e0, e1 = block_range(html, 'var EXPRS = [')
old_block = html[e0:e1]
rows = re.findall(r'\[(.*?)\]', old_block, re.S)
assert len(rows) == 12, 'EXPRS 行数不是 12'
new_rows = []
for r, row in enumerate(rows):
    if r in EXPR_OK:
        items = []
        for k in KEYS:
            b = webp_bytes(os.path.join(BUNDLE, 'expr_%d_%s.png' % (r, k)), 380, 80)
            total_new += len(b)
            items.append(enc(b))
        new_rows.append('  [' + ',\n   '.join(items) + ']')
    else:
        new_rows.append('  [' + row.strip() + ']')
html = html[:e0] + 'var EXPRS = [\n' + ',\n'.join(new_rows) + '\n  ];' + html[e1:]

io.open(HTML, 'w', encoding='utf-8', newline='').write(html)
print('换图完成：新图合计 %.0f KB，页面 %.0f KB' % (total_new / 1024.0, len(html.encode('utf-8')) / 1024.0))
