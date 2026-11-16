import re
p = r'F:\Daodao\src\_apk\assets\dao.html'
s = open(p, encoding='utf-8').read()
# 把 base64 折叠，便于看代码
s2 = re.sub(r'data:image/[a-z]+;base64,[A-Za-z0-9+/=]+', '<B64>', s)
lines = s2.split('\n')
for i, l in enumerate(lines, 1):
    if re.search(r'FACES|POSES|WALKS|SWORDFLY|faceIdx|curFace|species|HTML_VER', l):
        t = l.strip()
        if len(t) > 260:
            t = t[:260] + '...'
        print(f'{i}|{t}')
