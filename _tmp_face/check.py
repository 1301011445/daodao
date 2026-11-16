import re
p = r'F:\Daodao\_tmp_face\apkcheck\dao.html'
s = open(p, encoding='utf-8').read()
i = s.index('var FACES = [')
j = s.index('];', i)
print('faces_in_apk =', s[i:j].count('data:image'))
print('HTML_VER =', re.findall(r"var HTML_VER = '([^']*)'", s))
print('page_bytes =', len(s.encode('utf-8')))
