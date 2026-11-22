# 程序版本：v0.1 | 2026-11-22 | 新建：并行总控，一项一项串着等改成并发跑，每项 60 秒硬超时
# 为什么要有这个：一天一轮里十几个 py 各自冷启动、串行等待，光解释器启动就是十几秒；
# 任何一项没写超时（自检.py 就卡过 7 分钟）整轮就挂在那儿。这里并发 + 硬超时，总时长≈最慢一项。
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor

PY = r"E:\Python313\python.exe"
OUT_DIR = r"F:\Daodao\巡检报告"

JOBS = [
    ("自检", r"F:\Daodao\tools\自检.py", 60),
    ("两端自用体检", r"F:\Daodao\tools\两端自用体检.py", 60),
    ("版本机制", r"F:\Daodao\tools\版本机制.py", 40),
    ("版本奖惩", r"F:\Daodao\tools\版本奖惩.py", 40),
    ("愉悦值检查", r"F:\Daodao\tools\愉悦值检查.py", 40),
    ("纠错体检", r"F:\Daodao\tools\纠错体检.py", 40),
    ("程序版本检查", r"F:\Daodao\tools\程序版本检查.py", 40),
    ("学习复现日历", r"F:\Daodao\tools\学习复现日历.py", 40),
    ("学习归档", r"F:\Daodao\tools\音乐\学习归档\归档.py", 40),
    ("判据检查", r"F:\Daodao\tools\音乐\判据检查\判据检查.py", 40),
    ("触控热区检查", r"F:\Daodao\tools\界面\触控热区检查.py", 30),
    ("前奏钩子检查", r"F:\Daodao\tools\音乐\前奏钩子\前奏钩子检查.py", 40),
]

# 性能类指标不能跟别的检查抢 CPU：13 个脚本并发时帧率会被自己人拉低，
# 实测并发跑 帧调度检查 会假 FAIL（p50 顶到 34ms 以上）。所以它单独跑，其余并发。
PERF_JOBS = [
    ("帧调度检查", r"F:\Daodao\tools\界面\帧调度检查.py", 30),
]


def run_one(name, path, limit):
    t0 = time.time()
    if not os.path.exists(path):
        return dict(name=name, path=path, state="MISSING", sec=0.0, tail="", code=-1)
    try:
        p = subprocess.run([PY, path], capture_output=True, timeout=limit)
        txt = (p.stdout or b"").decode("utf-8", "replace")
        lines = [x for x in txt.strip().splitlines() if x.strip()]
        state = "OK" if p.returncode == 0 else "FAIL"
        code = p.returncode
    except subprocess.TimeoutExpired:
        lines, state, code = [], "TIMEOUT", 124
    return dict(name=name, path=path, state=state, sec=round(time.time() - t0, 1),
                tail="\n".join(lines[-3:]), code=code)


def main():
    t_all = time.time()
    rows = []
    with ThreadPoolExecutor(max_workers=6) as ex:
        futs = [ex.submit(run_one, n, p, s) for n, p, s in JOBS]
        for f in futs:
            rows.append(f.result())
    for n, p, s in PERF_JOBS:
        rows.append(run_one(n, p, s))
    total = round(time.time() - t_all, 1)
    bad = [r for r in rows if r["state"] != "OK"]

    for r in rows:
        print("%-8s %-7s %5.1fs" % (r["name"], r["state"], r["sec"]))
        if r["state"] != "OK" and r["tail"]:
            for ln in r["tail"].splitlines()[-2:]:
                print("    " + ln)
    print("总控|项=%d|过=%d|异常=%d|总耗时=%.1fs" % (len(rows), len(rows) - len(bad), len(bad), total))

    os.makedirs(OUT_DIR, exist_ok=True)
    rep = os.path.join(OUT_DIR, "总控_%s.md" % time.strftime("%Y%m%d_%H%M"))
    with open(rep, "w", encoding="utf-8") as f:
        f.write("# 巡检总控 %s\n\n" % time.strftime("%Y-%m-%d %H:%M:%S"))
        f.write("| 项 | 状态 | 秒 |\n|---|---|---|\n")
        for r in rows:
            f.write("| %s | %s | %.1f |\n" % (r["name"], r["state"], r["sec"]))
        f.write("\n总耗时 %.1fs，异常 %d 项。\n" % (total, len(bad)))
        for r in bad:
            f.write("\n## %s（%s）\n```\n%s\n```\n" % (r["name"], r["state"], r["tail"]))
    print("报告 " + rep)
    sys.exit(0 if not bad else 1)


if __name__ == "__main__":
    main()
