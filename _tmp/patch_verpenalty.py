# -*- coding: utf-8 -*-
import io, shutil, os
p = r'F:\Daodao\tools\版本奖惩.py'
bak = p + '.bak_20261122'
if not os.path.exists(bak):
    shutil.copy2(p, bak)
s = io.open(p, encoding='utf-8').read()

old_land = "LANDING = os.path.join(ROOT, '引导页_src', 'index.html')"
new_land = ("LANDING = r'C:\\Users\\LDY\\Doubao\\chats\\2026-11-11\\new-chat\\道落地页\\道_落地页_v069.html'  "
            "# 2026-11-22 改：原 引导页_src\\index.html 是旧副本（data-ver 停在 69）")
old_on = "ONLINE = 'https://4mf81m04wehh3.doubao.link/app/app_17hnj8acgs2'"
new_on = ("ONLINE = 'https://4mf81m04wehh3.doubao.link/app/app_17jdxkgf27q'  "
          "# 2026-11-22 改：旧 app_17hnj8acgs2 线上还是 62，已换现用落地页 app")

for a, b in ((old_land, new_land), (old_on, new_on)):
    if a not in s:
        print('NOT FOUND:', a[:40])
    s = s.replace(a, b)
io.open(p, 'w', encoding='utf-8').write(s)
print('patched ->', p, 'bak ->', bak)
