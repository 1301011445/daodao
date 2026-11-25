# -*- coding: utf-8 -*-
"""v137 台账收尾（2026-11-26 手机悬浮窗轮）"""
import io, json, os, sys
sys.path.insert(0, r"F:\Daodao\tools")
import importlib
qk = importlib.import_module("问题库")
R=r"F:\Daodao"; now="2026-11-26 00:05"
def app(p,t):
    with io.open(p,"a",encoding="utf-8") as f: f.write(t)

app(os.path.join(R,"发版记录.txt"), """
=== v137 手机悬浮窗补齐（2026-11-26 00:05）===
修/加：① petH 从屏高 7.5%/上限 66dp/下限 52dp → 15%/150dp/100dp，1080×2400 上约 360px 高、180px 宽，眉眼已可辨。
② App 里「换形象」原来只换 App 内那只（dao.html 里 setArt 调用 0 处），现在 btnSwap 会调 DaoNative.setArt(species)，DaoOverlay 新增静态 setArt + 静态服务引用，桌面悬浮窗立刻跟着换；没起窗时写进偏好，下次起来直接是它。
③ 悬浮窗会走会飞：走路时整窗每拍最多 0.42dp（≈12.6dp/秒，3~5 秒走 40~60dp，不会横穿屏幕）；骑祥云/飞剑/纸鹤（mount 1/3/5）叠 ±9dp 上下飘；走完把 x0/y0 存回偏好。
④ 桌面端顺带修「说话时还在叠心情浮动、两层正弦打架像发抖」：moodTicks 只在 !speaking 时生效、幅度 1.4→1.0。
判据：tools\\网页更新检查.py 新增 W0~W5（W0 距上次检查 ≤26h，W1/W2 线上 data-ver 与账本 current 一致，W3 线上短链与账本一致，W4 清单页正文「当前版本号」不能留旧数字，W5 本地两页 ≤3 天改过），不过就记扣分到 自我状态\\网页扣分.json。首次跑真抓到两处：清单页正文还写「当前版本号：135」、没有历史检查记录，扣 4 分；发版后复跑全 PASS。
出包：exe 13707776（APP_VER=137，BUILD_OK proc=1 res=214）；apk 29065505（vc137/vn1.37、HTML_VER=137，包内 DaoNative.setArt/ isAirMount / driftAccX 均在 dex，旧包 Dao.v136.apk）。
发页：清单页/落地页 data-ver 137、短链 WOTOC311ae / vvpEr6hTIJ，线上抽查 data-ver=137、正文 137。
""")

app(os.path.join(R,"待优化.txt"), """115|走路八帧素材重烘（Q-161 的落地）：先 7 号少年、4 号恐龙少女，提示词写死「两腿分开一前一后、抬起脚离地」|P1|待改|tools\\形象\\形象评审.py 复测脚簇≥2、步幅≥6px
116|悬浮窗尺寸要按真机复核：15% 屏高在小屏（720×1280）上可能压到底栏|P2|待改|装 1.37 后在 720p/1080p 各量一次窗口高度占比
""")

app(os.path.join(R,"学习台账.txt"), """
[2026-11-26 00:05] 悬浮窗补齐轮（第14类「骨骼与动作」/第1类 帧调度的应用）：把「App 选择 → 悬浮窗」的同步链路补上（DaoNative.setArt → DaoOverlay.setArt → PetView.setArt 三段），把「会走会飞」拆成「速度上限 + 腾空竖向漂浮」两条可判据，并新增网页更新检查 W0~W5 六条判据（含漏检扣分）。
""")
app(os.path.join(R,"同步日志.txt"), "[2026-11-26 00:05] v137：悬浮窗 15% 屏高（原 7.5%）、App 换形象同步到悬浮窗、走路 12.6dp/秒 + 云/剑/鹤上下飘、桌面端修说话发抖；网页检查 W0~W5 首跑抓 2 处旧文案扣 4 分，发版后全 PASS；双端 137 + 两页 137。\n")

q=qk.register("悬浮窗尺寸偏小（7.5% 屏高/66dp 顶，看不清眉眼）",
             来源="用户反馈", 严重度="P1",
             说明="v137 已改 15%/150dp/100dp；真机 720p 还要复核，见待优化 116。",
             key="ui:overlay-size")
print("Q", q)

# 账本
p=os.path.join(R,"自我状态","版本账本.json")
d=json.load(io.open(p,encoding="utf-8"))
d["current"]=137
d.setdefault("notes",{})["137"]="悬浮窗 15% 屏高、App 换形象同步到悬浮窗、走路 12.6dp/秒+腾空漂浮、桌面端修说话发抖；新增网页更新检查 W0~W5"
d.setdefault("versions",[]).append({"ver":137,"date":"2026-11-26","title":"手机悬浮窗放大+形象坐骑同步+会走会飞+网页更新检查",
  "apk":29065505,"apk_link":"https://aka.doubaocdn.com/s/vvpEr6hTIJ",
  "exe":13707776,"exe_link":"https://aka.doubaocdn.com/s/WOTOC311ae",
  "pages":["app_17hpue26uuw","app_17jdxkgf27q"]})
d["检测"].update({"时间":now,"电脑":"137","apk":"137","页面":"137","线上":"137"})
io.open(p,"w",encoding="utf-8").write(json.dumps(d,ensure_ascii=False,indent=2))

p2=os.path.join(R,"自我状态","版本使用.json")
u=json.load(io.open(p2,encoding="utf-8"))
u.setdefault("版本",{})["137"]={"立项":"2026-11-26","目标":3,"项":[
 {"项":"两端 v137 包与版本号","验证":"2026-11-26","证据":"BUILD_OK exe 13707776 APP_VER=137；apk 29065505 vc137/vn1.37 HTML_VER=137，dex 含 setArt/isAirMount/driftAccX"},
 {"项":"网页更新检查真跑","验证":"2026-11-26","证据":"tools\\网页更新检查.py 首跑 4/6（抓到旧文案 135、漏检）扣 4 分；改账本与发页后复跑 6/6"},
 {"项":"两页线上 137","验证":"2026-11-26","证据":"release 7712063216179858364 / 7712063135939857397 finished；线上 data-ver=137、正文 137、短链 WOTOC311ae/vvpEr6hTIJ"}]}
io.open(p2,"w",encoding="utf-8").write(json.dumps(u,ensure_ascii=False,indent=2))
print("ledger ok")
