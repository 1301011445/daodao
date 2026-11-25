# -*- coding: utf-8 -*-
"""v140：两页换成新短链与字节数，角标/正文/更新说明一起改。"""
import io, os, re

R = r"F:\Daodao"
EXE = "https://aka.doubaocdn.com/s/vOZ4r4KyTr"
APK = "https://aka.doubaocdn.com/s/7RaBG2Sd9f"
EXE_N = os.path.getsize(os.path.join(R, "道.exe"))
APK_N = os.path.getsize(os.path.join(R, "道.apk"))
print("字节：exe", EXE_N, "apk", APK_N)

# 清单页
p1 = r"C:\Users\LDY\Doubao\chats\2026-11-11\new-chat\vermanifest\index.html"
t = io.open(p1, encoding="utf-8").read()
t = t.replace('data-ver="139"', 'data-ver="140"')
t = t.replace("https://aka.doubaocdn.com/s/VD9RhyLfuC", EXE)
t = t.replace("https://aka.doubaocdn.com/s/SNZC9azVZP", APK)
t = re.sub(r"<p>当前版本号：139（电脑 [\d,]+ 字节，手机 [\d,]+ 字节）</p>",
           "<p>当前版本号：140（电脑 {:,} 字节，手机 {:,} 字节）</p>".format(EXE_N, APK_N), t)
t = t.replace("本次更新：6 号蓝发少女、7 号黑发少年的八帧走路换成真迈步的一套（脚前后错开约一个脚长，鞋底同一水平线）；",
              "本次更新：生活动作只留「骑坐骑」，看电视、喝茶、跳舞、转身、飞、御剑、滑板、轮滑连同它们的场景（客厅/花丛/云海/海边）一起下线；"
              "顺手修了鼠标停在贴边探头的道身上时窗口来回抽的问题（改成按光标位置判定 + 200/450ms 防抖）。")
io.open(p1, "w", encoding="utf-8").write(t)
print("清单页 140:", 'data-ver="140"' in t, "当前版本号：140" in t, EXE in t, APK in t)

# 落地页
p2 = r"C:\Users\LDY\Doubao\chats\2026-11-11\new-chat\道落地页\道_落地页_v069.html"
t = io.open(p2, encoding="utf-8").read()
t = t.replace('data-ver="139"', 'data-ver="140"')
t = t.replace("https://aka.doubaocdn.com/s/VD9RhyLfuC", EXE)
t = t.replace("https://aka.doubaocdn.com/s/SNZC9azVZP", APK)
t = t.replace("v1.39", "v1.40")
t = re.sub(r'data-bytes="\d+"', 'data-bytes="%d"' % EXE_N, t, count=1)
# 第二处 data-bytes 是手机
idx = t.find('data-bytes="%d"' % EXE_N) + len('data-bytes="%d"' % EXE_N)
m = re.search(r'data-bytes="\d+"', t[idx:])
if m:
    s0 = idx + m.start(); s1 = idx + m.end()
    t = t[:s0] + 'data-bytes="%d"' % APK_N + t[s1:]
t = t.replace("2026-11-26 更新：6/7 号八帧走路换成真迈步，形象评审 A8 转 PASS",
              "2026-11-25 更新：生活动作只留骑坐骑，其他场景全部下线；贴边探头不再来回抽")
t = re.sub(r"电脑 [\d.]+ MB", "电脑 %.1f MB" % (EXE_N / 1048576.0), t)
t = re.sub(r"手机 [\d.]+ MB", "手机 %.1f MB" % (APK_N / 1048576.0), t)
io.open(p2, "w", encoding="utf-8").write(t)
print("落地页 140:", 'data-ver="140"' in t, "v1.40" in t, "count v1.40:", t.count("v1.40"),
      "exe字节", str(EXE_N) in t, "apk字节", str(APK_N) in t)
