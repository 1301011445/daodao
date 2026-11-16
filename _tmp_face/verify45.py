import re
p = r'F:\Daodao\_tmp_face\apkcheck45\dao.html'
s = open(p, encoding='utf-8').read()
faces = s[s.index('var FACES = ['):s.index('];', s.index('var FACES = ['))]
print('包内 FACES 张数 =', faces.count('data:image'))
print('_ks   =', re.findall(r'var _ks = \[[^]]*\]', s)[0])
print('_kinds=', re.findall(r'var _kinds = \[[^]]*\]', s)[0])
print('WHO 项数 =', s[s.index('var WHO = ['):s.index('];', s.index('var WHO = ['))].count(',') + 1)
print('HTML_VER =', re.findall(r"var HTML_VER = '[^']*'", s))
print('页面字节 =', len(s.encode('utf-8')))
