# -*- coding: utf-8 -*-
"""v135 发页：两个页面统一到 135 + 新短链 + 体积"""
import io, os, re, shutil

EXE = 'https://aka.doubaocdn.com/s/6T6Oz5Iz6P'
APK = 'https://aka.doubaocdn.com/s/UCn7XVPtXA'
EXE_B = 13702144
APK_B = 29065505
VER = '135'
VNAME = '1.35'
EXE_MB = '%.1f MB' % (EXE_B / 1048576.0)
APK_MB = '%.1f MB' % (APK_B / 1048576.0)

M = r'C:\Users\LDY\Doubao\chats\2026-11-11\new-chat\vermanifest\index.html'
L = r'C:\Users\LDY\Doubao\chats\2026-11-11\new-chat\道落地页\道_落地页_v069.html'


def save(p, s):
    bak = p + '.bak_135'
    if not os.path.exists(bak):
        shutil.copy2(p, bak)
    io.open(p, 'w', encoding='utf-8', newline='').write(s)
    print('WROTE', p, len(s))


# ---- 清单页 ----
s = io.open(M, encoding='utf-8').read()
s2 = re.sub(r'data-ver="\d+"', 'data-ver="%s"' % VER, s, count=1)
s2 = re.sub(r'data-exe="[^"]+"', 'data-exe="%s"' % EXE, s2, count=1)
s2 = re.sub(r'data-apk="[^"]+"', 'data-apk="%s"' % APK, s2, count=1)
s2 = re.sub(r'当前版本号：\d+（电脑 [\d,]+ 字节，手机 [\d,]+ 字节）',
            '当前版本号：%s（电脑 %s 字节，手机 %s 字节）' % (VER, format(EXE_B, ','), format(APK_B, ',')),
            s2, count=1)
assert 'data-ver="%s"' % VER in s2
save(M, s2)

# ---- 落地页 ----
s = io.open(L, encoding='utf-8').read()
s2 = re.sub(r'data-ver="\d+"', 'data-ver="%s"' % VER, s, count=1)
s2 = re.sub(r'data-exe="[^"]+"', 'data-exe="%s"' % EXE, s2, count=1)
s2 = re.sub(r'data-apk="[^"]+"', 'data-apk="%s"' % APK, s2, count=1)
s2 = re.sub(r'<span class="vbadge">v[\d.]+</span>电脑 [\d.]+ MB<span class="dot">·</span>手机 [\d.]+ MB',
            '<span class="vbadge">v%s</span>电脑 %s<span class="dot">·</span>手机 %s' % (VNAME, EXE_MB, APK_MB),
            s2, count=1)
s2 = re.sub(r'道\.exe · v[\d.]+ · <span class="sz">[\d.]+ MB</span>',
            '道.exe · v%s · <span class="sz">%s</span>' % (VNAME, EXE_MB), s2, count=1)
s2 = re.sub(r'道\.apk · v[\d.]+ · <span class="sz">[\d.]+ MB</span>',
            '道.apk · v%s · <span class="sz">%s</span>' % (VNAME, APK_MB), s2, count=1)
s2 = re.sub(r'版本 [\d.]+ · 日期', '版本 %s · 日期' % VER, s2)
for need in ('data-ver="%s"' % VER, EXE, APK, 'v%s' % VNAME):
    assert need in s2, need
save(L, s2)
print('PAGE135_OK')
