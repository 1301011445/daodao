# 程序版本：v0.1 | 2026-11-22 | 一次性：升 0.108（两端版本号）+ 桌面 _bundle 立绘去紫边前先备份
import io, re, shutil, os

# 1) 版本号 107 -> 108
p = r'F:\Daodao\src\桌面分身\pet.cs'
s = io.open(p, encoding='utf-8').read()
a = 'public const int APP_VER = 107;'
assert a in s
io.open(p, 'w', encoding='utf-8').write(s.replace(a, 'public const int APP_VER = 108;', 1))
print('pet.cs APP_VER -> 108')

p = r'F:\Daodao\src\_apk\AndroidManifest.xml'
s = io.open(p, encoding='utf-8').read()
s2 = s.replace('android:versionCode="107"', 'android:versionCode="108"', 1)
s2 = s2.replace('android:versionName="0.107"', 'android:versionName="0.108"', 1)
assert s2 != s
io.open(p, 'w', encoding='utf-8').write(s2)
print('AndroidManifest -> 108 / 0.108')

p = r'F:\Daodao\src\_apk\assets\dao.html'
s = io.open(p, encoding='utf-8').read()
m = re.search(r"HTML_VER\s*=\s*'(\d+)'", s)
print('HTML_VER 原值', m.group(1))
assert m.group(1) == '107'
s = s.replace("HTML_VER = '107'", "HTML_VER = '108'", 1) if "HTML_VER = '107'" in s else re.sub(r"HTML_VER\s*=\s*'107'", "HTML_VER = '108'", s, count=1)
io.open(p, 'w', encoding='utf-8').write(s)
print('dao.html HTML_VER -> 108')
