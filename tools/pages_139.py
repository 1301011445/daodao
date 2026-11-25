# -*- coding: utf-8 -*-
import io, shutil, os

R = r"F:\Daodao"
shutil.copyfile(os.path.join(R, "src", "_apk", "Dao.apk"), os.path.join(R, "道.apk"))
EXE = "https://aka.doubaocdn.com/s/VD9RhyLfuC"
APK = "https://aka.doubaocdn.com/s/SNZC9azVZP"
EXE_N = os.path.getsize(os.path.join(R, "道.exe"))
APK_N = os.path.getsize(os.path.join(R, "src", "_apk", "Dao.apk"))
EXE_B = str(EXE_N)
APK_B = str(APK_N)

p1 = r"C:\Users\LDY\Doubao\chats\2026-11-11\new-chat\vermanifest\index.html"
t = io.open(p1, encoding="utf-8").read()
t = t.replace('data-ver="138"', 'data-ver="139"')
t = t.replace("https://aka.doubaocdn.com/s/FE7Q2fZVoU", EXE).replace("https://aka.doubaocdn.com/s/QnewAqhfga", APK)
old = "<p>当前版本号：138（电脑 13,707,776 字节，手机 29,065,505 字节）</p>"
new = ("<p>当前版本号：139（电脑 {:,} 字节，手机 {:,} 字节）</p>\n".format(EXE_N, APK_N)
       + "<p>本次更新：6 号蓝发少女、7 号黑发少年的八帧走路换成真迈步的一套（脚前后错开约一个脚长，鞋底同一水平线）；"
         "形象评审 A8 从 FAIL 变成 PASS（步幅 58px / 49px，脚簇 2）。更新于 2026-11-26。</p>")
t = t.replace(old, new)
io.open(p1, "w", encoding="utf-8").write(t)
print("清单页:", 'data-ver="139"' in t, "当前版本号：139" in t)

p2 = r"C:\Users\LDY\Doubao\chats\2026-11-11\new-chat\道落地页\道_落地页_v069.html"
t = io.open(p2, encoding="utf-8").read()
t = t.replace('data-ver="138"', 'data-ver="139"')
t = t.replace("https://aka.doubaocdn.com/s/FE7Q2fZVoU", EXE).replace("https://aka.doubaocdn.com/s/QnewAqhfga", APK)
t = t.replace("v1.38", "v1.39")
t = t.replace('data-bytes="13707776"', 'data-bytes="%s"' % EXE_B).replace('data-bytes="29065505"', 'data-bytes="%s"' % APK_B)
t = t.replace("2026-11-26 更新：悬浮窗真机 180×360 px，App 选的形象会同步到悬浮窗",
              "2026-11-26 更新：6/7 号八帧走路换成真迈步，形象评审 A8 转 PASS")
# 体积文案跟着改
import re
t = re.sub(r"电脑 [\d.]+ MB", "电脑 %.1f MB" % (EXE_N / 1048576.0), t)
t = re.sub(r"手机 [\d.]+ MB", "手机 %.1f MB" % (APK_N / 1048576.0), t)
io.open(p2, "w", encoding="utf-8").write(t)
print("落地页:", 'data-ver="139"' in t, "count v1.39:", t.count("v1.39"), "字节:", EXE_B, APK_B)
