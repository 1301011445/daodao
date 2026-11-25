# -*- coding: utf-8 -*-
"""真机按钮链路验证：点「换形象」两次，每次截 App + 最后截桌面悬浮窗。"""
import subprocess, time, os
from PIL import Image, ImageDraw, ImageFont

ADB = r"E:\AndroidTools\sdk\platform-tools\adb.exe"
D = r"F:\Daodao\_diag_look\真机"


def sh(*a):
    return subprocess.run([ADB, "shell"] + list(a), capture_output=True, text=True,
                          encoding="utf-8", errors="ignore").stdout


def shot(name):
    with open(os.path.join(D, name), "wb") as f:
        subprocess.run([ADB, "exec-out", "screencap", "-p"], stdout=f)


def who():
    sh("uiautomator", "dump", "/sdcard/w.xml")
    x = sh("cat", "/sdcard/w.xml")
    import re
    m = re.search(r'text="([^"]+)" resource-id="whoName"', x)
    return m.group(1) if m else "?"


def tap_swap():
    # 输入条会盖住按钮行，先把焦点移开，再点按钮行（真机 1080x2400 上 y≈2118）
    sh("input", "keyevent", "4")
    time.sleep(0.6)
    sh("input", "tap", "117", "2118")
    time.sleep(2.5)


sh("am", "start", "-n", "com.daodao.pet/.Launcher0")
time.sleep(4)
n0 = who()
shot("20_0.jpg".replace(".jpg", ".png") if False else "20_before.png")
tap_swap()
n1 = who()
shot("21_after1.png")
tap_swap()
n2 = who()
shot("22_after2.png")
sh("am", "start", "-a", "android.intent.action.MAIN", "-c", "android.intent.category.HOME")
time.sleep(4)
shot("23_home.png")
print("序列：", n0, "→", n1, "→", n2)

# 拼图（App 两次 + 桌面悬浮窗）
f = ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", 15)
A = Image.open(os.path.join(D, "20_before.png")).convert("RGB")
B = Image.open(os.path.join(D, "22_after2.png")).convert("RGB")
C = Image.open(os.path.join(D, "23_home.png")).convert("RGB")
W, H = 300, 667
out = Image.new("RGB", (W * 3 + 50, H + 56), (22, 22, 26))
out.paste(A.resize((W, H), Image.LANCZOS), (8, 48))
out.paste(B.resize((W, H), Image.LANCZOS), (W + 22, 48))
out.paste(C.resize((W, H), Image.LANCZOS), (W * 2 + 36, 48))
d = ImageDraw.Draw(out)
d.text((8, 14), "① 起点 App：%s" % n0, fill=(236, 236, 242), font=f)
d.text((W + 22, 14), "② 点两下换形象：%s" % n2, fill=(236, 236, 242), font=f)
d.text((W * 2 + 36, 14), "③ 桌面悬浮窗也是 %s" % n2, fill=(120, 255, 180), font=f)
out.save(os.path.join(D, "换形象_按钮链路_真机验证.png"))
print("拼图 OK")
