# -*- coding: utf-8 -*-
"""v128 版本五处同号（精确替换）"""
import re

def fix(path, pat, repl, label):
    s = open(path, encoding='utf-8').read()
    s2, k = re.subn(pat, repl, s)
    open(path, 'w', encoding='utf-8').write(s2)
    print(label, '替换', k, '->', re.search(pat, s2).group(0))

fix(r'F:\Daodao\src\桌面分身\pet.cs', r'APP_VER\s*=\s*\d+', 'APP_VER = 128', 'pet.cs')
fix(r'F:\Daodao\src\_apk\AndroidManifest.xml', r'android:versionCode="\d+"', 'android:versionCode="128"', 'manifest code')
fix(r'F:\Daodao\src\_apk\AndroidManifest.xml', r'android:versionName="[^"]*"', 'android:versionName="1.28"', 'manifest name')
fix(r'F:\Daodao\src\_apk\assets\dao.html', r"HTML_VER\s*=\s*'[^']*'", "HTML_VER = '128'", 'dao.html')
fix(r'F:\Daodao\道-随身版.html', r"HTML_VER\s*=\s*'[^']*'", "HTML_VER = '128'", '随身版')

v = [re.search(r'APP_VER\s*=\s*(\d+)', open(r'F:\Daodao\src\桌面分身\pet.cs', encoding='utf-8').read()).group(1),
     re.search(r"versionCode=\"(\d+)\"", open(r'F:\Daodao\src\_apk\AndroidManifest.xml', encoding='utf-8').read()).group(1),
     re.search(r"HTML_VER\s*=\s*'([^']*)'", open(r'F:\Daodao\src\_apk\assets\dao.html', encoding='utf-8').read()).group(1),
     re.search(r"HTML_VER\s*=\s*'([^']*)'", open(r'F:\Daodao\道-随身版.html', encoding='utf-8').read()).group(1)]
print('VER', v, 'PASS' if v == ['128', '128', '128', '128'] else 'FAIL')
