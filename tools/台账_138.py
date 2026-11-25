# -*- coding: utf-8 -*-
import io, json, os

R = r"F:\Daodao"
now = "2026-11-26 21:40"


def app(p, t):
    with io.open(os.path.join(R, p), "a", encoding="utf-8") as f:
        f.write(t)


app("发版记录.txt", """
=== v138 手机悬浮窗真机对齐（2026-11-26 21:40）===
起因：手机 USB 连上电脑，adb 终于能用。装 1.37 真跑一遍，看到「App 显示白兔少女、悬浮窗还是蓝发少女」——换形象只在点按钮时同步，开机不推。
改：dao.html / 道-随身版.html 在「定下今天是谁」之后立刻调 DaoNative.setArt(species)，开机就把当前形象推给悬浮窗；坐骑本来在 init 就推，不动。五处版本升 138。
真机实测（红米 23049RAD8C、Android 15、1080x2400、440dpi）：
  - dumpsys window 读到悬浮窗 ty=APPLICATION_OVERLAY、(x,y)(180x360)，360px = 15% 屏高，和设计一致；
  - 连续 7 次采样坐标：x 857→831，y 498/504/525/486/468，窗口真的在挪，骑祥云时上下飘 25px 级别；
  - adb 装包成功，versionCode=138 / versionName=1.38，App 左上角显示 v1.38。
限制：这台 MIUI 默认禁止 adb 注入输入事件（INJECT_EVENTS 被拒），「点换形象看悬浮窗跟着变」这一步没能在设备上自动点，等用户打开「USB 调试（安全设置）」后补验。
exe 13707776（APP_VER=138）、apk 29065505（vc138/vn1.38、HTML_VER=138、包内 setArt 4 处含开机同步）；短链 exe FE7Q2fZVoU / apk QnewAqhfga；两页 data-ver 138、落地页角标 v1.38、正文 138。
""")

app("学习台账.txt", """
[2026-11-26 21:40] 真机联调轮：第一次用 adb 在真机上读出悬浮窗的真实窗口参数（ty=APPLICATION_OVERLAY + mAttrs 的 (x,y)(w x h)），把「看起来大不大」「会不会动」从猜改成可采样的数；也第一次撞上 MIUI 的 INJECT_EVENTS 拦截，学到「能装包能截图，但不一定能点」。
""")

app("同步日志.txt", "[2026-11-26 21:40] v138：真机装 1.37 发现 App 与悬浮窗形象不一致 → 加开机 setArt 同步；真机实测 180x360px、走动和漂浮坐标可测；双端 138 + 两页 138。\n")

p = os.path.join(R, "自我状态", "版本账本.json")
d = json.load(io.open(p, encoding="utf-8"))
d["current"] = 138
d.setdefault("notes", {})["138"] = "开机把当前形象推给手机悬浮窗（修 App 与悬浮窗不一致）；真机实测悬浮窗 180x360px、走动+漂浮可测"
d.setdefault("versions", []).append({
    "ver": 138, "date": "2026-11-26", "title": "悬浮窗与 App 形象真机对齐",
    "apk": 29065505, "apk_link": "https://aka.doubaocdn.com/s/QnewAqhfga",
    "exe": 13707776, "exe_link": "https://aka.doubaocdn.com/s/FE7Q2fZVoU",
    "pages": ["app_17hpue26uuw", "app_17jdxkgf27q"],
})
d["检测"].update({"时间": now, "电脑": "138", "apk": "138", "页面": "138", "线上": "138"})
io.open(p, "w", encoding="utf-8").write(json.dumps(d, ensure_ascii=False, indent=2))

p2 = os.path.join(R, "自我状态", "版本使用.json")
u = json.load(io.open(p2, encoding="utf-8"))
u.setdefault("版本", {})["138"] = {"立项": "2026-11-26", "目标": 3, "项": [
    {"项": "真机安装并读到悬浮窗窗口参数", "验证": "2026-11-26",
     "证据": "adb dumpsys window：ty=APPLICATION_OVERLAY (180x360)px；7 次采样 x857→831、y468~525"},
    {"项": "真机包版本与页面版本", "验证": "2026-11-26",
     "证据": "dumpsys package versionCode=138/versionName=1.38；App 左上角 v1.38；两页 data-ver=138"},
    {"项": "开机形象同步进包", "验证": "2026-11-26",
     "证据": "zipfile 读 assets/dao.html：HTML_VER=138、v138 同步注释在、DaoNative.setArt 4 处"},
]}
io.open(p2, "w", encoding="utf-8").write(json.dumps(u, ensure_ascii=False, indent=2))
print("账本与台账已写")
