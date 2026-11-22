# -*- coding: utf-8 -*-
import json, io, time, subprocess, os

jp = r"F:\Daodao\tools\程序版本记录.json"
d = json.load(open(jp, encoding="utf-8"))
progs = d["程序"]
name = "帧调度检查.py"
path = r"F:\Daodao\tools\界面\帧调度检查.py"
if not any(p["名称"] == name for p in progs):
    mt = time.strftime("%Y-%m-%d", time.localtime(os.path.getmtime(path)))
    progs.append({
        "名称": name, "路径": path, "版本": "v0.1", "日期": "2026-11-22",
        "用途": "桌面端帧调度体检（p50/p95/max/重绘耗时/稳定性 7 条）",
        "改动": "新建：读 /diag，阈值按 30fps 档定，3 次采样防 flaky",
        "文件修改日": mt, "已插版本头": True,
    })
    json.dump(d, open(jp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("ADDED", len(progs))
else:
    print("EXISTS", len(progs))
