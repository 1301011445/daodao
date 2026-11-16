import re
p = r'F:\Daodao\src\_apk\assets\dao.html'
s = open(p, encoding='utf-8').read()
s2 = re.sub(r'data:image/[a-z]+;base64,[A-Za-z0-9+/=]+', '<B64>', s)
lines = s2.split('\n')
for i, l in enumerate(lines, 1):
    if re.search(r'_kinds|_ks\b|WHO\s*=|var FY|var FW|TODAY_SP|_dp', l):
        t = l.strip()
        if len(t) > 400:
            t = t[:400] + '...'
        print(f'{i}|{t}')
