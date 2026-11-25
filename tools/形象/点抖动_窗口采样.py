# -*- coding: utf-8 -*-
"""量「点一下道」窗口本身有没有抖：点击前后各 3.2 秒、约 60Hz 读窗口矩形。"""
import ctypes, time, csv, json
from ctypes import wintypes

u = ctypes.windll.user32

class RECT(ctypes.Structure):
    _fields_ = [("L", ctypes.c_long), ("T", ctypes.c_long), ("R", ctypes.c_long), ("B", ctypes.c_long)]

def find_pet():
    hwnds = []
    ENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    def cb(h, l):
        r = RECT()
        u.GetWindowRect(h, ctypes.byref(r))
        w, hh = r.R - r.L, r.B - r.T
        if 200 <= w <= 600 and 120 <= hh <= 400 and u.IsWindowVisible(h):
            buf = ctypes.create_unicode_buffer(256)
            u.GetWindowTextW(h, buf, 256)
            t = buf.value
            if t and ("道" in t or "Doa" in t) or (w, hh) == (380, 205):
                hwnds.append((h, t, w, hh, r.L, r.T))
        return True
    u.EnumWindows(ENUMPROC(cb), 0)
    return hwnds

def sample(hwnd, secs=3.2, tag="x"):
    rows = []
    t0 = time.perf_counter()
    while time.perf_counter() - t0 < secs:
        r = RECT()
        u.GetWindowRect(hwnd, ctypes.byref(r))
        rows.append(dict(t=round(time.perf_counter() - t0, 3), x=r.L, y=r.T,
                         w=r.R - r.L, h=r.B - r.T))
        time.sleep(0.016)
    ys = [r["y"] for r in rows]; xs = [r["x"] for r in rows]; ws = [r["w"] for r in rows]
    dys = [ys[i] - ys[i - 1] for i in range(1, len(ys))]
    flips = sum(1 for i in range(1, len(dys)) if dys[i] * dys[i - 1] < 0)
    print("%s：%d 次采样 y∈[%d,%d] 行程=%dpx 逐次最大Δy=%dpx 换向=%d  x∈[%d,%d]  w∈[%d,%d]"
          % (tag, len(rows), min(ys), max(ys), max(ys) - min(ys), max(abs(d) for d in dys), flips,
             min(xs), max(xs), min(ws), max(ws)))
    return rows, ys, dys, flips

if __name__ == "__main__":
    cand = find_pet()
    print("候选窗口：", cand[:6])
    if not cand:
        raise SystemExit("没找到道的窗口")
    hwnd, title, w, hh, x, y = max(cand, key=lambda c: c[2] * c[3])
    print("用窗口 hwnd=%s 标题=%r 位置=(%d,%d) 尺寸=%dx%d" % (hwnd, title, x, y, w, hh))

    before = sample(hwnd, tag="点击前")
    time.sleep(0.4)
    cx, cy = x + w // 2, y + hh // 2
    print("点击坐标 (%d,%d)" % (cx, cy))
    u.SetCursorPos(cx, cy)
    time.sleep(0.08)
    u.mouse_event(0x0002, 0, 0, 0, 0)
    time.sleep(0.05)
    u.mouse_event(0x0004, 0, 0, 0, 0)
    after = sample(hwnd, tag="点击后")

    res = dict(点击前=dict(rows=before[0], 逐次Δy=before[2], 换向=before[3]),
               点击后=dict(rows=after[0], 逐次Δy=after[2], 换向=after[3]))
    json.dump(res, open(r"F:\Daodao\自我状态\窗口采样.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
