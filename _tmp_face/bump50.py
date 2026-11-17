# -*- coding: utf-8 -*-
import re

# pet.cs：APP_VER 49 → 50
p1 = r'F:\Daodao\src\桌面分身\pet.cs'
s1 = open(p1, 'rb').read().decode('utf-8-sig')
m = re.search(r'(APP_VER\s*=\s*)49(\s*;)', s1)
assert m, 'pet.cs APP_VER 未命中'
s1 = s1[:m.start()] + m.group(1) + '50' + m.group(2) + s1[m.end():]
open(p1, 'wb').write(s1.encode('utf-8'))
print('pet.cs APP_VER ->', re.findall(r'APP_VER\s*=\s*(\d+)', s1)[:1])

# dao.html：HTML_VER 49 → 50
p2 = r'F:\Daodao\src\_apk\assets\dao.html'
s2 = open(p2, 'rb').read().decode('utf-8')
m2 = re.search(r"(HTML_VER\s*=\s*['\"])49(['\"])", s2)
assert m2, 'dao.html HTML_VER 未命中'
s2 = s2[:m2.start()] + m2.group(1) + '50' + m2.group(2) + s2[m2.end():]
open(p2, 'wb').write(s2.encode('utf-8'))
print('dao.html HTML_VER ->', re.findall(r"HTML_VER\s*=\s*['\"](\d+)", s2)[:1])

# AndroidManifest：versionCode / versionName 49 → 50
p3 = r'F:\Daodao\src\_apk\AndroidManifest.xml'
raw3 = open(p3, 'rb').read()
bom3 = raw3.startswith(b'\xef\xbb\xbf')
s3 = raw3.decode('utf-8-sig')
s3 = s3.replace('android:versionCode="49"', 'android:versionCode="50"', 1)
s3 = s3.replace('android:versionName="49.0"', 'android:versionName="50.0"', 1)
open(p3, 'wb').write((b'\xef\xbb\xbf' if bom3 else b'') + s3.encode('utf-8'))
print('manifest ->', re.findall(r'android:versionCode="(\d+)"', s3)[:1], re.findall(r'android:versionName="([^"]*)"', s3)[:1])
