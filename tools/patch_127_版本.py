# -*- coding: utf-8 -*-
"""v127 版本五处同号"""
import re

FILES = [
    (r'F:\Daodao\src\桌面分身\pet.cs', r'(APP_VER\s*=\s*)(\d+)'),
    (r'F:\Daodao\src\_apk\AndroidManifest.xml', r'(android:versionCode=")(\d+)(")'),
    (r'F:\Daodao\src\_apk\AndroidManifest.xml', r'(android:versionName=")1\.(\d+)(")'),
    (r'F:\Daodao\src\_apk\assets\dao.html', r"(HTML_VER\s*=\s*')1\.(\d+)(')"),
    (r'F:\Daodao\道-随身版.html', r"(HTML_VER\s*=\s*')1\.(\d+)(')"),
]
for path, pat in FILES:
    s = open(path, encoding='utf-8').read()
    m = re.search(pat, s)
    if not m:
        print('MISS', path, pat)
        continue
    if 'versionCode' in pat:
        new = m.group(1) + '127' + m.group(3)
    else:
        new = m.group(1) + '127' + m.group(m.lastindex)
    s2 = s[:m.start()] + new + s[m.end():]
    open(path, 'w', encoding='utf-8').write(s2)
    print('SET', path.split('\\')[-1], '->', new)

checks = {
    'pet.cs APP_VER': re.search('APP_VER\\s*=\\s*(\\d+)', open(FILES[0][0], encoding='utf-8').read()).group(1),
    'manifest': re.search('versionCode="(\\d+)"', open(FILES[1][0], encoding='utf-8').read()).group(1),
    'dao.html': re.search("HTML_VER\\s*=\\s*'(\\d+).", open(FILES[3][0], encoding='utf-8').read()).group(1),
}
print('VER', {k: v for k, v in checks.items()}, 'PASS' if all(v == '127' for v in checks.values()) else 'FAIL')
