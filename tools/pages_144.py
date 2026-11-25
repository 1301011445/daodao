# -*- coding: utf-8 -*-
"""v144：桌面端改逐像素 alpha（软边回来、棱角消失）；挥手换整张抬手立绘（不再切 48 条横带硬推）。两页升到 144。"""
import io, os, re

R = r"F:\Daodao"
EXE = "https://aka.doubaocdn.com/s/zOrhwIUbuK"
APK = "https://aka.doubaocdn.com/s/H8ZktvVVCI"
EXE_N = os.path.getsize(os.path.join(R, "道.exe"))
APK_N = os.path.getsize(os.path.join(R, "道.apk"))
print("字节：exe", EXE_N, "apk", APK_N)

p1 = r"C:\Users\LDY\Doubao\chats\2026-11-11\new-chat\vermanifest\index.html"
t = io.open(p1, encoding="utf-8").read()
t = t.replace('data-ver="143"', 'data-ver="144"')
t = t.replace("https://aka.doubaocdn.com/s/meCX7PfmYT", EXE)
t = t.replace("https://aka.doubaocdn.com/s/xxKayGhFZ4", APK)
t = re.sub(r"<p>当前版本号：143（电脑 [\d,]+ 字节，手机 [\d,]+ 字节）</p>",
           "<p>当前版本号：144（电脑 {:,} 字节，手机 {:,} 字节）</p>".format(EXE_N, APK_N), t)
i0 = t.find("<p>本次更新：")
i1 = t.find("</p>", i0)
new_up = ("<p>本次更新：桌面端不再用洋红透明键，改成逐像素 alpha 上屏——立绘边缘的软边和抗锯齿回来了，"
          "发梢衣摆不再有粉毛，也不再有硬边夹出来的楼梯锯齿；挥手改成整张抬手立绘（同一形象的真动作图），"
          "不再把身体切成 48 条横带各自横向硬推，肩线和裙摆不再错位，看着不再「身体被切开」。")
if i0 > 0 and i1 > i0:
    t = t[:i0] + new_up + t[i1:]
io.open(p1, "w", encoding="utf-8").write(t)
print("清单页 144:", 'data-ver="144"' in t, "当前版本号：144" in t, EXE in t, APK in t)

p2 = r"C:\Users\LDY\Doubao\chats\2026-11-11\new-chat\道落地页\道_落地页_v069.html"
t = io.open(p2, encoding="utf-8").read()
t = t.replace('data-ver="143"', 'data-ver="144"')
t = t.replace("https://aka.doubaocdn.com/s/meCX7PfmYT", EXE)
t = t.replace("https://aka.doubaocdn.com/s/xxKayGhFZ4", APK)
t = t.replace("v1.43", "v1.44")
t = re.sub(r'data-bytes="\d+"', 'data-bytes="%d"' % EXE_N, t, count=1)
idx = t.find('data-bytes="%d"' % EXE_N) + len('data-bytes="%d"' % EXE_N)
m = re.search(r'data-bytes="\d+"', t[idx:])
if m:
    s0 = idx + m.start(); s1 = idx + m.end()
    t = t[:s0] + 'data-bytes="%d"' % APK_N + t[s1:]
t = t.replace("2026-11-25 更新：桌面立绘硬边去粉毛、走路不铺会滑的贴景；手机悬浮窗 20% 屏高 + 表情 + 轮演动作",
              "2026-11-25 更新：桌面改逐像素 alpha，边缘软回来、没有锯齿棱角；挥手换整张抬手立绘，不再切条扭曲")
t = re.sub(r"电脑 [\d.]+ MB", "电脑 %.1f MB" % (EXE_N / 1048576.0), t)
t = re.sub(r"手机 [\d.]+ MB", "手机 %.1f MB" % (APK_N / 1048576.0), t)
io.open(p2, "w", encoding="utf-8").write(t)
print("落地页 144:", 'data-ver="144"' in t, "v1.44" in t, "count v1.44:", t.count("v1.44"),
      "exe字节", str(EXE_N) in t, "apk字节", str(APK_N) in t)
