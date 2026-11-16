import re
p = r'F:\Daodao\_tmp_face\apkcheck46\dao.html'
s = open(p, encoding='utf-8').read()
faces = s[s.index('var FACES = ['):s.index('];', s.index('var FACES = ['))]
print('包内 FACES 张数 =', faces.count('data:image'))
print('_ks =', re.findall(r'var _ks = \[[^]]*\]', s)[0])
print('HTML_VER =', re.findall(r"var HTML_VER = '[^']*'", s))
print('WHO 项数 =', s[s.index('var WHO = ['):s.index('];', s.index('var WHO = ['))].count(',') + 1)
print('页面字节 =', len(s.encode('utf-8')))
