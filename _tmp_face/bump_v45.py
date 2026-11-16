import re
# AndroidManifest
m = r'F:\Daodao\src\_apk\AndroidManifest.xml'
raw = open(m, 'rb').read()
bom = raw.startswith(b'\xef\xbb\xbf')
t = raw.decode('utf-8-sig')
t2 = t.replace('versionCode="44"', 'versionCode="45"').replace('versionName="44.0"', 'versionName="45.0"')
assert t2 != t, 'manifest 没变'
open(m, 'wb').write((b'\xef\xbb\xbf' if bom else b'') + t2.encode('utf-8'))
print('manifest:', re.findall(r'versionCode="\d+"', t2), re.findall(r'versionName="[^"]*"', t2))

# pet.cs
p = r'F:\Daodao\src\桌面分身\pet.cs'
raw = open(p, 'rb').read()
bom = raw.startswith(b'\xef\xbb\xbf')
s = raw.decode('utf-8-sig')
old = 'public const int APP_VER = 44;'
assert s.count(old) == 1, 'APP_VER 不对: %d' % s.count(old)
s = s.replace(old, 'public const int APP_VER = 45;')
open(p, 'wb').write((b'\xef\xbb\xbf' if bom else b'') + s.encode('utf-8'))
print('APP_VER:', re.findall(r'public const int APP_VER = \d+;', s))
