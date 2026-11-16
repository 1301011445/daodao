# -*- coding: utf-8 -*-
import re, os

# 1) 音色表补齐到 14 条（13 白衫少年、14 青衫少女）
vp = r'F:\Daodao\src\桌面分身\_bundle\voices.txt'
raw = open(vp, 'rb').read()
bom = raw.startswith(b'\xef\xbb\xbf')
lines = [l for l in raw.decode('utf-8-sig').split('\n') if l.strip()]
while len(lines) < 12:
    lines.append('zh-CN-XiaoxiaoNeural')
lines = lines[:12] + ['zh-CN-YunyeNeural', 'zh-CN-XiaomengNeural']
open(vp, 'wb').write((b'\xef\xbb\xbf' if bom else b'') + ('\n'.join(lines) + '\n').encode('utf-8'))
print('voices 行数 =', len(lines))

# 2) 版本 47 -> 48
c = r'F:\Daodao\src\桌面分身\pet.cs'
raw = open(c, 'rb').read(); b3 = raw.startswith(b'\xef\xbb\xbf')
cs = raw.decode('utf-8-sig')
assert cs.count('public const int APP_VER = 47;') == 1
open(c, 'wb').write((b'\xef\xbb\xbf' if b3 else b'') + cs.replace('public const int APP_VER = 47;', 'public const int APP_VER = 48;').encode('utf-8'))

m = r'F:\Daodao\src\_apk\AndroidManifest.xml'
raw = open(m, 'rb').read(); b2 = raw.startswith(b'\xef\xbb\xbf')
t = raw.decode('utf-8-sig')
t = t.replace('versionCode="47"', 'versionCode="48"').replace('versionName="47.0"', 'versionName="48.0"')
open(m, 'wb').write((b'\xef\xbb\xbf' if b2 else b'') + t.encode('utf-8'))

h = r'F:\Daodao\src\_apk\assets\dao.html'
raw = open(h, 'rb').read(); b1 = raw.startswith(b'\xef\xbb\xbf')
s = raw.decode('utf-8-sig')
assert s.count("var HTML_VER = '47';") == 1
s = s.replace("var HTML_VER = '47';", "var HTML_VER = '48';", 1)
assert 'function daoSelfCheck' in s
open(h, 'wb').write((b'\xef\xbb\xbf' if b1 else b'') + s.encode('utf-8'))

print('APP_VER/versionCode/HTML_VER ->', re.findall(r'public const int APP_VER = \d+;', cs),
      re.findall(r'versionCode="\d+"', t), re.findall(r"var HTML_VER = '\d+'", s))
