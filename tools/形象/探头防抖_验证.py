# -*- coding: utf-8 -*-
"""验证探头（petMode=1）防抖：光标放上去、移开、再放上去，各看 3 秒，窗口应当各只动一次。"""
import ctypes, time, json
from ctypes import wintypes

u = ctypes.windll.user32

class RECT(ctypes.Structure):
    _fields_ = [("L", ctypes.c_long), ("T", ctypes.c_long), ("R", ctypes.c_long), ("B", ctypes.c_long)]

def find_pet():
    found = []
    ENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    def cb(h, l):
        r = RECT(); u.GetWindowRect(h, ctypes.byref(r))
        w, hh = r.R - r.L, r.B - r.T
        if 300 <= w <= 600 and 150 <= hh <= 400 and u.IsWindowVisible(h):
            buf = ctypes.create_unicode_buffer(256); u.GetWindowTextW(h, buf, 256)
            if buf.value == "DaoPetWindow":
                found.append((h, r.L, r.T, w, hh))
        return True
    u.EnumWindows(ENUMPROC(cb), 0)
    return found

def phase(hwnd, tag, secs=3.0, move_to=None):
    if move_to:
        u.SetCursorPos(*move_to)
    t0 = time.perf_counter(); xs = []
    while time.perf_counter() - t0 < secs:
        r = RECT(); u.GetWindowRect(hwnd, ctypes.byref(r)); xs.append(r.L)
        time.sleep(0.02)
    ch = [(round((i) * 0.02, 2), xs[i]) for i in range(1, len(xs)) if xs[i] != xs[i - 1]]
    print("%s：x∈[%d,%d] 变动 %d 次 %s" % (tag, min(xs), max(xs), len(ch), ch[:8]))
    return dict(xs=xs, changes=len(ch))

if __name__ == "__main__":
    c = find_pet()
    print("窗口：", c)
    if not c: raise SystemExit("没找到道")
    hwnd, x, y, w, h = c[0]
    inside = (x + max(8, w // 8), y + h // 2)     # 露出那条身上的位置
    away = (max(0, x - 300), y + h // 2)
    res = {}
    res["A_光标放上去"] = phase(hwnd, "A 光标放到露出的身上", 3.0, move_to=inside)
    res["B_光标移开"] = phase(hwnd, "B 光标移开 300px", 3.0, move_to=away)
    res["C_再放上去"] = phase(hwnd, "C 再放回身上", 3.0, move_to=inside)
    res["D_点击"] = phase(hwnd, "D 停在身上 3s（应不再动）", 3.0, move_to=inside)
    json.dump(res, open(r"F:\Daodao\自我状态\探头防抖.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
