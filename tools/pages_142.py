# -*- coding: utf-8 -*-
"""v142：两页升到 142（手机悬浮窗放大 + 表情 + 单击轮演动作），换短链与字节数。"""
import io, os, re

R = r"F:\Daodao"
EXE = "https://aka.doubaocdn.com/s/Y8dVlmWSQH"
APK = "https://aka.doubaocdn.com/s/2Uq3YvtbdO"
EXE_N = os.path.getsize(os.path.join(R, "道.exe"))
APK_N = os.path.getsize(os.path.join(R, "道.apk"))
print("字节：exe", EXE_N, "apk", APK_N)

p1 = r"C:\Users\LDY\Doubao\chats\2026-11-11\new-chat\vermanifest\index.html"
t = io.open(p1, encoding="utf-8").read()
t = t.replace('data-ver="141"', 'data-ver="142"')
t = t.replace("https://aka.doubaocdn.com/s/Fali2ly4Jv", EXE)
t = t.replace("https://aka.doubaocdn.com/s/426Klj5RoP", APK)
t = re.sub(r"<p>当前版本号：141（电脑 [\d,]+ 字节，手机 [\d,]+ 字节）</p>",
           "<p>当前版本号：142（电脑 {:,} 字节，手机 {:,} 字节）</p>".format(EXE_N, APK_N), t)
t = t.replace(
    "本次更新：桌面端坐骑改成画在身前",
    "本次更新：手机悬浮窗放到 20% 屏高（480px，球头像 56dp），轮廓和脸都看得清；"
    "加了表情系统（开心/难过/生气/困，22 点后自动困脸）；单击悬浮窗会轮演招手→点头→小跳→蹲一下，动作带表情。"
    "桌面端坐骑改成画在身前")
io.open(p1, "w", encoding="utf-8").write(t)
print("清单页 142:", 'data-ver="142"' in t, "当前版本号：142" in t, EXE in t, APK in t)

p2 = r"C:\Users\LDY\Doubao\chats\2026-11-11\new-chat\道落地页\道_落地页_v069.html"
t = io.open(p2, encoding="utf-8").read()
t = t.replace('data-ver="141"', 'data-ver="142"')
t = t.replace("https://aka.doubaocdn.com/s/Fali2ly4Jv", EXE)
t = t.replace("https://aka.doubaocdn.com/s/426Klj5RoP", APK)
t = t.replace("v1.41", "v1.42")
t = re.sub(r'data-bytes="\d+"', 'data-bytes="%d"' % EXE_N, t, count=1)
idx = t.find('data-bytes="%d"' % EXE_N) + len('data-bytes="%d"' % EXE_N)
m = re.search(r'data-bytes="\d+"', t[idx:])
if m:
    s0 = idx + m.start(); s1 = idx + m.end()
    t = t[:s0] + 'data-bytes="%d"' % APK_N + t[s1:]
t = t.replace("2026-11-25 更新：桌面端坐骑改画在身前、按身高 0.70 定尺的真马；像蜗牛的椭圆小兽已删",
              "2026-11-25 更新：手机悬浮窗放大到 20% 屏高，加表情（开心/难过/生气/困）与单击轮演动作")
t = re.sub(r"电脑 [\d.]+ MB", "电脑 %.1f MB" % (EXE_N / 1048576.0), t)
t = re.sub(r"手机 [\d.]+ MB", "手机 %.1f MB" % (APK_N / 1048576.0), t)
io.open(p2, "w", encoding="utf-8").write(t)
print("落地页 142:", 'data-ver="142"' in t, "v1.42" in t, "count v1.42:", t.count("v1.42"),
      "exe字节", str(EXE_N) in t, "apk字节", str(APK_N) in t)
