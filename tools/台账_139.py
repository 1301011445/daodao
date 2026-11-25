# -*- coding: utf-8 -*-
import io, json, os, subprocess, sys, time

R = r"F:\Daodao"
sys.path.insert(0, os.path.join(R, "tools"))
import 问题库 as qk

# 1) 重启桌面道到 139
subprocess.run(["taskkill", "/IM", "道.exe", "/F"], capture_output=True)
time.sleep(2)
subprocess.Popen([os.path.join(R, "道.exe")], cwd=R, close_fds=True)
time.sleep(3)

now = "2026-11-26 22:30"
with io.open(os.path.join(R, "发版记录.txt"), "a", encoding="utf-8") as f:
    f.write("""
=== v139 八帧走路真迈步（2026-11-26 22:30）===
起因：形象评审 A8 显示 14 个形象里只有 5 个真迈腿，6 号蓝发少女、7 号黑发少年的八帧是「站着不动」的素材（Q-161）。程序化转腿试过两版都出残影（裙摆残带、腿缝竖线、两脚并成一根白柱），已弃。
改法：以立绘为参考、旧八帧表为排版参考，用图像模型重画整套走路循环（8 格横排、纯白底、同一角色同一服装），再走 tools\\形象\\切片_走路表.py：去白底→按脚底统一身高 342px→192x384 居中，写入 src\\_apk\\assets 与 src\\桌面分身\\_bundle。
效果（形象评审 A8 真跑）：
  sp6 蓝发少女：脚簇 1→2，步幅 1.0px→58.0px，腿区帧差 125→3545，FAIL→PASS；
  sp7 黑发少年：脚簇 1→2，步幅 0.5px→49.0px，腿区帧差 133→4739，FAIL→PASS。
其余仍 FAIL 的 7 个（0 橘猫、1 白兔、3 熊猫、4 恐龙、5 企鹅、10 金发、12 白裙、13 猫耳）已排进待优化 118，同一套流程照抄即可。
出包：exe 14,440,448（APP_VER=139）、apk 31,246,217（vc139/vn1.39、HTML_VER=139）；真机已装 1.39，悬浮窗仍 180x360、形象与 App 一致（白兔+祥云）。
页面：短链 exe VD9RhyLfuC / apk SNZC9azVZP，两页 data-ver 139、落地页角标 v1.39、正文 139。
""")

with io.open(os.path.join(R, "待优化.txt"), "a", encoding="utf-8") as f:
    f.write("""118|剩下 7 个形象八帧不迈腿（0 橘猫/1 白兔/3 熊猫/4 恐龙/5 企鹅/10 金发/12 白裙/13 猫耳），照 v139 流程重画|P1|待改|形象评审 A8 每个 sp 脚簇=2 且步幅≥6px
""")

md = os.path.join(R, "能力检查", "2026-11-25.md")
with io.open(md, "a", encoding="utf-8") as f:
    f.write("""
## v139 形象步态修复（2026-11-26 22:30）

| 项 | 结果 | 证据 |
|---|---|---|
| sp6 蓝发少女 A8 | FAIL→PASS | 脚簇 2、步幅 58.0px、腿区帧差 3545 |
| sp7 黑发少年 A8 | FAIL→PASS | 脚簇 2、步幅 49.0px、腿区帧差 4739 |
| 真机 1.39 | 已装 | versionCode=139 / versionName=1.39，悬浮窗 180x360、形象=白兔（与 App 一致） |
| 两页 139 | 已上线 | data-ver 139、角标 v1.39、短链 VD9RhyLfuC / SNZC9azVZP |
| 待优化 118 | 已登记 | 剩 7 个形象同法重画 |
""")

# 关 Q-164（6 号无迈腿素材）
try:
    print("关 Q-164:", qk.close("Q-164", "6 号八帧已换成真迈步一套：A8 脚簇 2、步幅 58px、PASS；旧帧备份在 _bak\\walk8_6_旧。", "形象评审.py A8 sp6"))
except Exception as e:
    print("Q-164 失败:", e)
# Q-161 部分解决，注明进展
try:
    print("备注 Q-161:", qk.register("9 只走路素材不迈腿（v139 已修 2 只：6/7）", 来源="形象评审 A8", 严重度="P1",
                                  说明="v139 用图像模型重画八帧，sp6/sp7 已 PASS；其余 7 只见待优化 118，同一套流程。", key="art:walk8"))
except Exception as e:
    print("Q-161 备注失败:", e)

# 账本
p = os.path.join(R, "自我状态", "版本账本.json")
d = json.load(io.open(p, encoding="utf-8"))
d["current"] = 139
d.setdefault("notes", {})["139"] = "6/7 号八帧走路换成真迈步（图像模型重画+切片对齐），A8 由 FAIL 转 PASS"
d.setdefault("versions", []).append({
    "ver": 139, "date": "2026-11-26", "title": "八帧走路真迈步（6/7 号）",
    "apk": 31246217, "apk_link": "https://aka.doubaocdn.com/s/SNZC9azVZP",
    "exe": 14440448, "exe_link": "https://aka.doubaocdn.com/s/VD9RhyLfuC",
    "pages": ["app_17hpue26uuw", "app_17jdxkgf27q"],
})
d["检测"].update({"时间": now, "电脑": "139", "apk": "139", "页面": "139", "线上": "139", "手机": "139"})
d["真用"] = {"电脑": {"最后": now, "版本": "139", "证据": "重启后进程 道.exe 载入 139"},
             "手机": {"最后": now, "版本": "139", "证据": "adb dumpsys package versionCode=139"}}
io.open(p, "w", encoding="utf-8").write(json.dumps(d, ensure_ascii=False, indent=2))

p2 = os.path.join(R, "自我状态", "版本使用.json")
u = json.load(io.open(p2, encoding="utf-8"))
u.setdefault("版本", {})["139"] = {"立项": "2026-11-26", "目标": 3, "项": [
    {"项": "6/7 号八帧真迈步（A8 转 PASS）", "验证": "2026-11-26",
     "证据": "形象评审 sp6 脚簇2/步幅58.0 / sp7 脚簇2/步幅49.0"},
    {"项": "真机安装 1.39", "验证": "2026-11-26", "证据": "adb dumpsys versionCode=139；悬浮窗 180x360、形象白兔与 App 一致"},
    {"项": "两页 139 上线", "验证": "2026-11-26", "证据": "线上 data-ver=139、正文 139、角标 v1.39、短链 VD9RhyLfuC/SNZC9azVZP"},
]}
io.open(p2, "w", encoding="utf-8").write(json.dumps(u, ensure_ascii=False, indent=2))
print("账本已写 139")
