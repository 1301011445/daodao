import re, os, shutil, base64

p = r'F:\Daodao\src\_apk\assets\dao.html'
shutil.copy2(p, r'F:\Daodao\_tmp_face\dao.html.v45.bak')
raw = open(p, 'rb').read()
bom = raw.startswith(b'\xef\xbb\xbf')
s = raw.decode('utf-8-sig')

i = s.index('var FACES = [')
j = s.index('];', i)
seg = s[i:j]
pat = re.compile(r'"data:image/[a-z]+;base64,[A-Za-z0-9+/=]+"')
items = pat.findall(seg)
print('FACES 项数 =', len(items))
assert len(items) == 14, '项数不对'

new = {}
for sp in ('06', '07', '08', '11'):
    fp = r'F:\Daodao\_tmp_face\for_apk_%s.png' % sp
    b64 = base64.b64encode(open(fp, 'rb').read()).decode()
    new[int(sp)] = '"data:image/png;base64,%s"' % b64
    print('准备替换索引', int(sp), os.path.getsize(fp), '字节')

pos = 0
out = seg
for k, it in enumerate(items):
    idx = seg.index(it, pos)
    if k in new:
        seg = seg[:idx] + new[k] + seg[idx + len(it):]
        pos = idx + len(new[k])
    else:
        pos = idx + len(it)
s = s[:i] + seg + s[j:]

old_ver = "var HTML_VER = '45';"
assert s.count(old_ver) == 1
s = s.replace(old_ver, "var HTML_VER = '46';")

open(p, 'w', encoding='utf-8-sig' if bom else 'utf-8', newline='').write(s)
print('新页面字节 =', len(s.encode('utf-8')), '| BOM =', bom)

# 版本号
m = r'F:\Daodao\src\_apk\AndroidManifest.xml'
raw = open(m, 'rb').read()
bom2 = raw.startswith(b'\xef\xbb\xbf')
t = raw.decode('utf-8-sig')
t = t.replace('versionCode="45"', 'versionCode="46"').replace('versionName="45.0"', 'versionName="46.0"')
open(m, 'wb').write((b'\xef\xbb\xbf' if bom2 else b'') + t.encode('utf-8'))
print('manifest:', re.findall(r'versionCode="\d+"', t), re.findall(r'versionName="[^"]*"', t))

c = r'F:\Daodao\src\桌面分身\pet.cs'
raw = open(c, 'rb').read()
bom3 = raw.startswith(b'\xef\xbb\xbf')
cs = raw.decode('utf-8-sig')
assert cs.count('public const int APP_VER = 45;') == 1
cs = cs.replace('public const int APP_VER = 45;', 'public const int APP_VER = 46;')
open(c, 'wb').write((b'\xef\xbb\xbf' if bom3 else b'') + cs.encode('utf-8'))
print('APP_VER:', re.findall(r'public const int APP_VER = \d+;', cs))
