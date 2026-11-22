# -*- coding: utf-8 -*-
"""唤醒判据：喊名字的识别、常驻进程只起一次、能量门限与应声流程都能验。

跑法：python tools\\语音\\唤醒检查.py
前提：道.exe 已在跑（本机 127.0.0.1:8848）。
"""
import json
import os
import subprocess
import sys
import time
import urllib.parse
import urllib.request

BASE = "http://127.0.0.1:8848"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "唤醒检查_结果.json")
rows = []


def get(path, timeout=8):
    with urllib.request.urlopen(BASE + path, timeout=timeout) as r:
        return r.read().decode("utf-8", "ignore").strip()


def wake_procs():
    """返回当前在跑的 voice.py wake 进程数（常驻只该有 1 个）。"""
    try:
        ps = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
             "Where-Object { $_.CommandLine -like '*voice.py*wake*' } | "
             "Select-Object -ExpandProperty ProcessId"],
            capture_output=True, text=True, timeout=30)
        ids = [x.strip() for x in ps.stdout.splitlines() if x.strip().isdigit()]
        return ids
    except Exception:
        return []


def check(name, ok, detail):
    rows.append({"项": name, "结果": "PASS" if ok else "FAIL", "细节": detail})
    print(("PASS " if ok else "FAIL ") + name + "  " + detail)


def main():
    # 1. 该应的说法
    for t in ["道", "道道你在吗", "喂道", "hey dao"]:
        v = get("/wakechk?t=" + urllib.parse.quote(t))
        check("应声：" + t, v == "YES", v)

    # 2. 不该应的说法（话里带"道"但不是喊人）
    for t in ["知道了", "这道题怎么做", "味道不错", "道理很简单", "频道切一下"]:
        v = get("/wakechk?t=" + urllib.parse.quote(t))
        check("不误应：" + t, v == "NO", v)

    # 3. 应声流程能走通
    v = get("/wakefeed?t=" + urllib.parse.quote("道"))
    check("喂一句能触发应声", v == "HIT", v)

    # 4. 常驻进程：20 秒内 PID 不变、且只有 1 个
    a = wake_procs()
    time.sleep(20)
    b = wake_procs()
    check("常驻进程只起一个", len(b) == 1, "count=%d ids=%s" % (len(b), b))
    check("常驻进程不重启", a == b and len(a) == 1, "before=%s after=%s" % (a, b))

    # 5. 能量门限参数在位（代码级，恒定 120 判据见源码）
    try:
        src = open(r"F:\Daodao\src\桌面分身\pet.cs", "r", encoding="utf-8", errors="ignore").read()
        ok = "rms < 120" in src and "voice.py\" wake" not in src and '" wake"' in src
        check("能量门限在位", ok, "rms<120 与 wake 常驻参数都在")
    except Exception as e:
        check("能量门限在位", False, repr(e))

    n = len(rows)
    bad = [r for r in rows if r["结果"] != "PASS"]
    okall = len(bad) == 0
    print("SELFTEST|n=%d|pass=%d|fail=%d|%s" % (n, n - len(bad), len(bad), "PASS" if okall else "FAIL"))
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({"时间": time.strftime("%Y-%m-%d %H:%M:%S"), "项": rows,
                   "汇总": {"n": n, "fail": len(bad)}}, f, ensure_ascii=False, indent=1)
    return 0 if okall else 1


if __name__ == "__main__":
    sys.exit(main())
