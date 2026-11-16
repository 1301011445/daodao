import base64, shutil, os

p = r'F:\Daodao\src\_apk\assets\dao.html'
bak = p + '.v43.bak'
if not os.path.exists(bak):
    shutil.copy2(p, bak)
    print('backup ->', bak)

s = open(p, encoding='utf-8').read()
print('bytes before', len(s.encode('utf-8')))
print('bom', s.startswith('\ufeff'))

b12 = base64.b64encode(open(r'F:\Daodao\_tmp_face\for_apk_12.png', 'rb').read()).decode()
b13 = base64.b64encode(open(r'F:\Daodao\_tmp_face\for_apk_13.png', 'rb').read()).decode()

i = s.index('var FACES = [')
j = s.index('];', i)
seg = s[i:j]
print('faces 段长度', len(seg), '现有图数', seg.count('data:image'))

ins = ',\n    "data:image/png;base64,' + b12 + '",\n    "data:image/png;base64,' + b13 + '"'
new = s[:j] + ins + s[j:]

old_ver = "var HTML_VER = '38';"
if old_ver in new:
    new = new.replace(old_ver, "var HTML_VER = '44';", 1)
    print('HTML_VER 38 -> 44')
else:
    print('警告：HTML_VER 锚点没找到')

open(p, 'w', encoding='utf-8', newline='').write(new)
print('bytes after', len(new.encode('utf-8')))
print('新 FACES 图数', new[i:new.index('];', i)].count('data:image'))
