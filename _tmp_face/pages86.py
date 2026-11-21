import io
m = r"C:\Users\LDY\Doubao\chats\2026-11-11\new-chat\vermanifest\index.html"
l = r"C:\Users\LDY\Doubao\chats\2026-11-11\new-chat\道落地页\道_落地页_v069.html"
APK = "https://aka.doubaocdn.com/s/3lPW2VauvA"
EXE = "https://aka.doubaocdn.com/s/5Do7LRrMAe"
OLD_APK = "https://aka.doubaocdn.com/s/o0FQHhYKwq"
OLD_EXE = "https://aka.doubaocdn.com/s/aQU4YPnTWD"
def rw(p, pairs):
    s = io.open(p, encoding="utf-8").read()
    for a, b in pairs:
        if a in s:
            s = s.replace(a, b); print("  改  ", a[:60])
        else:
            print("  已是最新/未命中 ", a[:60])
    io.open(p, "w", encoding="utf-8").write(s)
print("清单页:")
rw(m, [('data-ver="84"', 'data-ver="86"'), (OLD_EXE, EXE), (OLD_APK, APK),
       ('当前版本号：84（电脑 13,171,712 字节，手机 13,943,044 字节）',
        '当前版本号：86（电脑 13,171,200 字节，手机 13,398,198 字节）')])
print("落地页:")
rw(l, [('data-ver="84"', 'data-ver="86"'), (OLD_EXE, EXE), (OLD_APK, APK),
       ('道.exe · v0.84', '道.exe · v0.86'), ('道.apk · v0.84', '道.apk · v0.86'),
       ('版本 0.71 · 2026-11-20', '版本 0.86 · 2026-11-21')])
