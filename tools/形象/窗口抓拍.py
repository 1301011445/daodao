# -*- coding: utf-8 -*-
"""抓桌面宠物窗口的连续几帧，用来看走路是否连贯、边缘有没有键色毛边。
用法：python 窗口抓拍.py [帧数] [间隔ms] [输出目录]
"""
import ctypes, sys, time, os
from ctypes import wintypes
from PIL import ImageGrab

user32 = ctypes.windll.user32
user32.FindWindowW.restype = wintypes.HWND

def find():
    h = user32.FindWindowW(None, "DaoPetWindow")
    if h:
        return h
    found = []
    def cb(hwnd, lparam):
        buf = ctypes.create_unicode_buffer(256)
        user32.GetWindowTextW(hwnd, buf, 256)
        if "道" in buf.value:
            found.append(hwnd)
        return True
    user32.EnumWindows(ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)(cb), 0)
    return found[0] if found else 0

h = find()
if not h:
    print("没找到窗口"); sys.exit(1)
r = wintypes.RECT()
user32.GetWindowRect(h, ctypes.byref(r))
box = (r.left, r.top, r.right, r.bottom)
print("窗口", box)

n = int(sys.argv[1]) if len(sys.argv) > 1 else 8
gap = int(sys.argv[2]) if len(sys.argv) > 2 else 120
out = sys.argv[3] if len(sys.argv) > 3 else r"F:\Daodao\_diag_look\窗口抓拍"
os.makedirs(out, exist_ok=True)
for i in range(n):
    ImageGrab.grab(bbox=box, all_screens=True).save(os.path.join(out, "w%02d.png" % i))
    time.sleep(gap / 1000.0)
print("存到", out)
