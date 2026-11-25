# -*- coding: utf-8 -*-
"""v127 版本修正（精确替换）"""
import re

def fix(path, pat, repl):
    s = open(path, encoding='utf-8').read()
    s2, k = re.subn(pat, repl, s)
    open(path, 'w', encoding='utf-8').write(s2)
    print(path.split('\\')[-1], '替换', k, '->', re.search(pat, s2).group(0))

fix(r'F:\Daodao\src\桌面分身\pet.cs', r'APP_VER\s*=\s*\d+', 'APP_VER = 127')
fix(r'F:\Daodao\src\_apk\AndroidManifest.xml', r'android:versionCode="\d+"', 'android:versionCode="127"')
fix(r'F:\Daodao\src\_apk\AndroidManifest.xml', r'android:versionName="[^"]*"', 'android:versionName="1.27"')
fix(r'F:\Daodao\src\_apk\assets\dao.html', r"HTML_VER\s*=\s*'[^']*'", "HTML_VER = '127'")
fix(r'F:\Daodao\道-随身版.html', r"HTML_VER\s*=\s*'[^']*'", "HTML_VER = '127'")

v1 = re.search(r'APP_VER\s*=\s*(\d+)', open(r'F:\Daodao\src\桌面分身\pet.cs', encoding='utf-8').read()).group(1)
m = open(r'F:\Daodao\src\_apk\AndroidManifest.xml', encoding='utf-8').read()
v2 = re.search(r'versionCode="(\d+)"', m).group(1)
v3 = re.search(r'versionName="([^"]*)"', m).group(1)
v4 = re.search(r"HTML_VER\s*=\s*'([^']*)'", open(r'F:\Daodao\src\_apk\assets\dao.html', encoding='utf-8').read()).group(1)
v5 = re.search(r"HTML_VER\s*=\s*'([^']*)'", open(r'F:\Daodao\道-随身版.html', encoding='utf-8').read()).group(1)
print('VER', v1, v2, v3, v4, v5, 'PASS' if (v1, v2, v3, v4, v5) == ('127', '127', '1.27', '127', '127') else 'FAIL')
