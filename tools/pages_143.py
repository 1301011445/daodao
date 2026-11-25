# -*- coding: utf-8 -*-
"""v143：桌面端硬边（去粉毛）+ 走路时不铺脚下景；两页升到 143。"""
import io, os, re

R = r"F:\Daodao"
EXE = "https://aka.doubaocdn.com/s/meCX7PfmYT"
APK = "https://aka.doubaocdn.com/s/xxKayGhFZ4"
EXE_N = os.path.getsize(os.path.join(R, "道.exe"))
APK_N = os.path.getsize(os.path.join(R, "道.apk"))
print("字节：exe", EXE_N, "apk", APK_N)

p1 = r"C:\Users\LDY\Doubao\chats\2026-11-11\new-chat\vermanifest\index.html"
t = io.open(p1, encoding="utf-8").read()
t = t.replace('data-ver="142"', 'data-ver="143"')
t = t.replace("https://aka.doubaocdn.com/s/Y8dVlmWSQH", EXE)
t = t.replace("https://aka.doubaocdn.com/s/2Uq3YvtbdO", APK)
t = re.sub(r"<p>当前版本号：142（电脑 [\d,]+ 字节，手机 [\d,]+ 字节）</p>",
           "<p>当前版本号：143（电脑 {:,} 字节，手机 {:,} 字节）</p>".format(EXE_N, APK_N), t)
t = t.replace(
    "本次更新：手机悬浮窗放到 20% 屏高",
    "本次更新：桌面端立绘边缘统一夹成硬边（半透明像素和洋红残留全抠掉），窗口不再带一圈粉毛，"
    "看着不再是「抠下来贴上去的一层」；走路时不再铺脚下那块小景（景跟着窗口滑，最像贴片）；"
    "立绘先一次性缩到显示尺寸再 1:1 切片，切片边缘不再重复采样。"
    "手机悬浮窗放到 20% 屏高")
io.open(p1, "w", encoding="utf-8").write(t)
print("清单页 143:", 'data-ver="143"' in t, "当前版本号：143" in t, EXE in t, APK in t)

p2 = r"C:\Users\LDY\Doubao\chats\2026-11-11\new-chat\道落地页\道_落地页_v069.html"
t = io.open(p2, encoding="utf-8").read()
t = t.replace('data-ver="142"', 'data-ver="143"')
t = t.replace("https://aka.doubaocdn.com/s/Y8dVlmWSQH", EXE)
t = t.replace("https://aka.doubaocdn.com/s/2Uq3YvtbdO", APK)
t = t.replace("v1.42", "v1.43")
t = re.sub(r'data-bytes="\d+"', 'data-bytes="%d"' % EXE_N, t, count=1)
idx = t.find('data-bytes="%d"' % EXE_N) + len('data-bytes="%d"' % EXE_N)
m = re.search(r'data-bytes="\d+"', t[idx:])
if m:
    s0 = idx + m.start(); s1 = idx + m.end()
    t = t[:s0] + 'data-bytes="%d"' % APK_N + t[s1:]
t = t.replace("2026-11-25 更新：手机悬浮窗放大到 20% 屏高，加表情（开心/难过/生气/困）与单击轮演动作",
              "2026-11-25 更新：桌面立绘硬边去粉毛、走路不铺会滑的贴景；手机悬浮窗 20% 屏高 + 表情 + 轮演动作")
t = re.sub(r"电脑 [\d.]+ MB", "电脑 %.1f MB" % (EXE_N / 1048576.0), t)
t = re.sub(r"手机 [\d.]+ MB", "手机 %.1f MB" % (APK_N / 1048576.0), t)
io.open(p2, "w", encoding="utf-8").write(t)
print("落地页 143:", 'data-ver="143"' in t, "v1.43" in t, "count v1.43:", t.count("v1.43"),
      "exe字节", str(EXE_N) in t, "apk字节", str(APK_N) in t)
