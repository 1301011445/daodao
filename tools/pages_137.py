# -*- coding: utf-8 -*-
import io
EXE="https://aka.doubaocdn.com/s/WOTOC311ae"
APK="https://aka.doubaocdn.com/s/vvpEr6hTIJ"
EXE_B="13707776"; APK_B="29065505"

# ---- 清单页 ----
p1=r"C:\Users\LDY\Doubao\chats\2026-11-11\new-chat\vermanifest\index.html"
t=io.open(p1,encoding="utf-8").read()
t=t.replace('data-ver="136"','data-ver="137"')
t=t.replace("https://aka.doubaocdn.com/s/Cnf1l8Ior4",EXE).replace("https://aka.doubaocdn.com/s/DtYKgapMJM",APK)
t=t.replace("<p>当前版本号：135（电脑 13,702,144 字节，手机 29,065,505 字节）</p>",
            "<p>当前版本号：137（电脑 13,707,776 字节，手机 29,065,505 字节）</p>\n<p>本次更新：手机悬浮窗放大到 15% 屏高，App 里选的形象/坐骑同步到悬浮窗，骑云·鹤·剑会上下飘着飞。更新于 2026-11-25。</p>")
io.open(p1,"w",encoding="utf-8").write(t)
print("清单页:", 'data-ver="137"' in t, "137（电脑" in t)

# ---- 落地页 ----
p2=r"C:\Users\LDY\Doubao\chats\2026-11-11\new-chat\道落地页\道_落地页_v069.html"
t=io.open(p2,encoding="utf-8").read()
t=t.replace('data-ver="136"','data-ver="137"')
t=t.replace("https://aka.doubaocdn.com/s/Cnf1l8Ior4",EXE).replace("https://aka.doubaocdn.com/s/DtYKgapMJM",APK)
t=t.replace("v1.36","v1.37")
t=t.replace('data-bytes="13171712"','data-bytes="%s"'%EXE_B).replace('data-bytes="13943044"','data-bytes="%s"'%APK_B)
t=t.replace("<span class=\"vbadge\">v1.37</span>电脑 13.1 MB<span class=\"dot\">·</span>手机 27.7 MB<span class=\"dot\">·</span>2026-11-25",
            "<span class=\"vbadge\">v1.37</span>电脑 13.1 MB<span class=\"dot\">·</span>手机 27.7 MB<span class=\"dot\">·</span>2026-11-25 更新：悬浮窗放大一倍能看清脸")
io.open(p2,"w",encoding="utf-8").write(t)
print("落地页:", 'data-ver="137"' in t, t.count("v1.37"), "更新：悬浮窗" in t)
