# -*- coding: utf-8 -*-
"""v145：桌面坐骑改成真骑姿立绘（ride_*.png），臀落鞍面、人坐在鞍上，不再用站姿杵在马背上。两页升到 145。"""
import io, os, re

R = r"F:\Daodao"
EXE = "https://aka.doubaocdn.com/s/MWp2UcMjtT"
APK = "https://aka.doubaocdn.com/s/UrjlJ4Ke2T"
EXE_N = os.path.getsize(os.path.join(R, "道.exe"))
APK_N = os.path.getsize(os.path.join(R, "道.apk"))
print("字节：exe", EXE_N, "apk", APK_N)

p1 = r"C:\Users\LDY\Doubao\chats\2026-11-11\new-chat\vermanifest\index.html"
t = io.open(p1, encoding="utf-8").read()
t = t.replace('data-ver="144"', 'data-ver="145"')
t = t.replace("https://aka.doubaocdn.com/s/zOrhwIUbuK", EXE)
t = t.replace("https://aka.doubaocdn.com/s/H8ZktvVVCI", APK)
t = re.sub(r"<p>当前版本号：144（电脑 [\d,]+ 字节，手机 [\d,]+ 字节）</p>",
           "<p>当前版本号：145（电脑 {:,} 字节，手机 {:,} 字节）</p>".format(EXE_N, APK_N), t)
i0 = t.find("<p>本次更新：")
i1 = t.find("</p>", i0)
new_up = ("<p>本次更新：桌面坐骑改用真骑姿立绘（ride_0~13.png）：腿是分开坐下的，臀部按每只形象实测的比例"
          "落在鞍面上，人往左挪到鞍心（鞍在贴图里比图中心偏左 0.048 图宽），马画在人后面，"
          "不再出现「人笔直站在马背上、脚悬空」的样子；另外桌面立绘边缘走逐像素 alpha，软边不再被夹成锯齿。")
if i0 > 0 and i1 > i0:
    t = t[:i0] + new_up + t[i1:]
io.open(p1, "w", encoding="utf-8").write(t)
print("清单页 145:", 'data-ver="145"' in t, "当前版本号：145" in t, EXE in t, APK in t)

p2 = r"C:\Users\LDY\Doubao\chats\2026-11-11\new-chat\道落地页\道_落地页_v069.html"
t = io.open(p2, encoding="utf-8").read()
t = t.replace('data-ver="144"', 'data-ver="145"')
t = t.replace("https://aka.doubaocdn.com/s/zOrhwIUbuK", EXE)
t = t.replace("https://aka.doubaocdn.com/s/H8ZktvVVCI", APK)
t = t.replace("v1.44", "v1.45")
t = re.sub(r'data-bytes="\d+"', 'data-bytes="%d"' % EXE_N, t, count=1)
idx = t.find('data-bytes="%d"' % EXE_N) + len('data-bytes="%d"' % EXE_N)
m = re.search(r'data-bytes="\d+"', t[idx:])
if m:
    s0 = idx + m.start(); s1 = idx + m.end()
    t = t[:s0] + 'data-bytes="%d"' % APK_N + t[s1:]
t = t.replace("2026-11-25 更新：桌面改逐像素 alpha，边缘软回来、没有锯齿棱角；挥手换整张抬手立绘，不再切条扭曲",
              "2026-11-25 更新：桌面坐骑改真骑姿——臀落鞍面、人坐在鞍上，不再是站姿悬在马背上")
t = re.sub(r"电脑 [\d.]+ MB", "电脑 %.1f MB" % (EXE_N / 1048576.0), t)
t = re.sub(r"手机 [\d.]+ MB", "手机 %.1f MB" % (APK_N / 1048576.0), t)
io.open(p2, "w", encoding="utf-8").write(t)
print("落地页 145:", 'data-ver="145"' in t, "v1.45" in t, "count v1.45:", t.count("v1.45"),
      "exe字节", str(EXE_N) in t, "apk字节", str(APK_N) in t)
