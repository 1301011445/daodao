# -*- coding: utf-8 -*-
"""v141：两页换成 v141 短链与字节数，角标/正文/更新说明一起改（只改 Windows 侧文案 + 版本号）。"""
import io, os, re

R = r"F:\Daodao"
EXE = "https://aka.doubaocdn.com/s/Fali2ly4Jv"
APK = "https://aka.doubaocdn.com/s/426Klj5RoP"
EXE_N = os.path.getsize(os.path.join(R, "道.exe"))
APK_N = os.path.getsize(os.path.join(R, "道.apk"))
print("字节：exe", EXE_N, "apk", APK_N)

p1 = r"C:\Users\LDY\Doubao\chats\2026-11-11\new-chat\vermanifest\index.html"
t = io.open(p1, encoding="utf-8").read()
t = t.replace('data-ver="140"', 'data-ver="141"')
t = t.replace("https://aka.doubaocdn.com/s/vOZ4r4KyTr", EXE)
t = t.replace("https://aka.doubaocdn.com/s/qn2DBTSnP6", APK)
t = re.sub(r"<p>当前版本号：140（电脑 [\d,]+ 字节，手机 [\d,]+ 字节）</p>",
           "<p>当前版本号：141（电脑 {:,} 字节，手机 {:,} 字节）</p>".format(EXE_N, APK_N), t)
t = t.replace(
    "本次更新：生活动作只留「骑坐骑」",
    "本次更新：桌面端坐骑改成画在身前、按身高 0.70 定尺的真马（人骑在马上，马身盖住脚踝）；"
    "兜底那只像蜗牛的椭圆小兽彻底删掉，没贴图就什么都不画；无调用的御剑/跳舞绘制代码也清了。"
    "生活动作只留「骑坐骑」")
io.open(p1, "w", encoding="utf-8").write(t)
print("清单页 141:", 'data-ver="141"' in t, "当前版本号：141" in t, EXE in t, APK in t)

p2 = r"C:\Users\LDY\Doubao\chats\2026-11-11\new-chat\道落地页\道_落地页_v069.html"
t = io.open(p2, encoding="utf-8").read()
t = t.replace('data-ver="140"', 'data-ver="141"')
t = t.replace("https://aka.doubaocdn.com/s/vOZ4r4KyTr", EXE)
t = t.replace("https://aka.doubaocdn.com/s/qn2DBTSnP6", APK)
t = t.replace("v1.40", "v1.41")
t = re.sub(r'data-bytes="\d+"', 'data-bytes="%d"' % EXE_N, t, count=1)
idx = t.find('data-bytes="%d"' % EXE_N) + len('data-bytes="%d"' % EXE_N)
m = re.search(r'data-bytes="\d+"', t[idx:])
if m:
    s0 = idx + m.start(); s1 = idx + m.end()
    t = t[:s0] + 'data-bytes="%d"' % APK_N + t[s1:]
t = t.replace("2026-11-25 更新：生活动作只留骑坐骑，其他场景全部下线；贴边探头不再来回抽",
              "2026-11-25 更新：桌面端坐骑改画在身前、按身高 0.70 定尺的真马；像蜗牛的椭圆小兽已删")
t = re.sub(r"电脑 [\d.]+ MB", "电脑 %.1f MB" % (EXE_N / 1048576.0), t)
t = re.sub(r"手机 [\d.]+ MB", "手机 %.1f MB" % (APK_N / 1048576.0), t)
io.open(p2, "w", encoding="utf-8").write(t)
print("落地页 141:", 'data-ver="141"' in t, "v1.41" in t, "count v1.41:", t.count("v1.41"),
      "exe字节", str(EXE_N) in t, "apk字节", str(APK_N) in t)
