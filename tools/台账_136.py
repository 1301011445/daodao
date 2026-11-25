# -*- coding: utf-8 -*-
"""v136 台账收尾（2026-11-25 形象补齐轮）"""
import io, json, os, sys, datetime
sys.path.insert(0, r"F:\Daodao\tools")
import importlib
qk = importlib.import_module("问题库")
R = r"F:\Daodao"
now = "2026-11-25 18:58"

def app(path, text):
    with io.open(path, "a", encoding="utf-8") as f:
        f.write(text)

app(os.path.join(R,"发版记录.txt"), """
=== v136 形象补齐（2026-11-25 18:58）===
修：① 道.exe --dump 被单实例锁挡掉，桌面上有它在跑就一张评审图都出不来 —— dump 提前到锁前面（出图 0→89 张）。
② 走路「点它就自己走掉」的根因：PaintAll 里 tripX += 3.2，每重绘一帧就往前蹭一步，点一下/冒气泡都会挪，高刷屏还更快。已删，位移只由 tick 改窗口坐标。
③ 近走 3px/跳≈187px/s（每秒跑过 1.3 个自己）→ 1px/跳≈62px/s；速度改用真实 dt，不再假设 30 跳/秒。
④ 步频改成按素材步幅反算（步幅 21px、一个循环两步），滑步率 1.00；⑤ 摆动 6.5px(4.5%身高) → 2.6px(1.8%)；⑥ 朝向一律取 walkDirX，不再用会翻面的 tripDir。
⑦ 巡走节拍 200 跳(3.2s) → 1800 跳(29s)，目标从「整屏随便挑」限制到当前位置 ±260px。
判据：tools\\形象\\走路判据.py B1~B7 全 PASS（滑步率 1.00、巡走阈值 1800）；tools\\形象\\形象评审.py：A1 9/16、A3 残留 0、渲染摆幅 1.4~1.9% 全 PASS、A8 步态 5/14（9 只八帧不迈腿，已登记）。
出包：exe 13707776（APP_VER=136，BUILD_OK proc=1 res=214）；apk 29065505（vc136/vn1.36、HTML_VER=136，旧包 Dao.v135.apk）。
发页：清单页/落地页 data-ver 136，短链换 Cnf1l8Ior4 / DtYKgapMJM，线上抽查两页均回 136。
""")

app(os.path.join(R,"待优化.txt"), """112|走路八帧里 9 只不迈腿（脚簇=1、步幅<6px）：重烘八帧，提示词必须写「两腿分开、一前一后、抬起的那只脚离地」|P1|待改|tools\\形象\\形象评审.py 量化名单；先重烘 7 号黑发少年与 4 号恐龙少女
113|立绘头身比 7 张超出 6.5–8.0（7 号 10.24、8 号 10.33、11 号 9.58）|P2|待改|重生成立绘时在提示词里锁 7.5 头身，并用 tools\\形象\\形象评审.py 复测
114|形象评审 A2（25% 缩略五官可辨）还没有阈值|P3|待改|先量 14 张立绘缩略后的梯度能量分布，再定阈值
""")

app(os.path.join(R,"学习台账.txt"), """
[2026-11-25 18:58] 形象补齐轮（非新类别，第14类「骨骼与动作」的应用）：把「走路像不像走」量化成 7 条判据并真跑；发现并修掉 6 处代码缺陷（dump 被锁、tripX 逐帧累加、速度超身材、步频拍脑袋、摆幅过大、朝向用错变量）。判据脚本 tools\\形象\\走路判据.py、tools\\形象\\形象评审.py。
""")
app(os.path.join(R,"今日所学.txt"), "2026-11-25 形象：步态量化（脚簇/步幅/滑步率）+ 绘制层与位移层分离；判据 B1~B7 全 PASS。\n")
app(os.path.join(R,"同步日志.txt"), "[2026-11-25 18:58] v136 形象补齐：dump 修复、tripX 逐帧累加删除、近走 62px/s、步频按步幅反算、巡走 29s/±260px；走路判据 7/7 PASS；形象评审 A1 9/16 A3 0 残留 A8 5/14；双端 136 + 两页 136 上线。\n")

q1 = qk.register("走路八帧里 9 只不迈腿（脚簇=1、步幅<6px），看着像原地滑",
                 来源="形象评审", 严重度="P1",
                 说明="sp0/1/3/4/5/6/7/10/12/13 的 walk8 素材两脚从没分开；评审脚本 tools\\形象\\形象评审.py 可复跑量化。第一步：只重烘 7 号与 4 号，提示词写死「两腿分开、一前一后、抬起的脚离地」，烘完用同一脚本复测脚簇≥2、步幅≥6px。",
                 key="art:walk8")
q2 = qk.register("立绘头身比超出 6.5–8.0（7 号 10.24 / 8 号 10.33 / 11 号 9.58）",
                 来源="形象评审", 严重度="P2",
                 说明="A1 硬门不过；修法=重生成时锁 7.5 头身，再用 tools\\形象\\形象评审.py 复测。当前只登记不动素材，避免一改就换脸。",
                 key="art:headratio")
print("Q:", q1, q2)

# 版本账本
p = os.path.join(R,"自我状态","版本账本.json")
d = json.load(io.open(p, encoding="utf-8"))
d["current"] = 136
d.setdefault("notes", {})["136"] = "修 dump 被单实例锁挡、走路 tripX 逐帧累加、速度超身材、步频拍脑袋、摆幅 4.5%→1.8%、朝向用错变量、巡走 3.2s→29s"
d.setdefault("versions", []).append({"ver":136,"date":"2026-11-25","title":"形象补齐：走路不再乱走/滑步",
    "apk":29065505,"apk_link":"https://aka.doubaocdn.com/s/DtYKgapMJM",
    "exe":13707776,"exe_link":"https://aka.doubaocdn.com/s/Cnf1l8Ior4",
    "pages":["app_17hpue26uuw","app_17jdxkgf27q"]})
d.setdefault("检测", {})["时间"] = now
d["检测"].update({"电脑":"136","apk":"136","页面":"136","线上":"136"})
io.open(p,"w",encoding="utf-8").write(json.dumps(d, ensure_ascii=False, indent=2))

# 版本使用
p2 = os.path.join(R,"自我状态","版本使用.json")
u = json.load(io.open(p2, encoding="utf-8"))
u.setdefault("版本", {})["136"] = {"立项":"2026-11-25","目标":3,"项":[
 {"项":"两端 v136 包与版本号","验证":"2026-11-25","证据":"BUILD_OK exe 13707776 APP_VER=136；apk 29065505 vc136/vn1.36 HTML_VER=136"},
 {"项":"走路判据真跑","验证":"2026-11-25","证据":"tools\\形象\\走路判据.py SUMMARY|7/7|bad=0（滑步率 1.00）"},
 {"项":"清单页/落地页线上 136","验证":"2026-11-25","证据":"release 7712060398006406149 / 7712060449521650630 均 finished；线上两页 data-ver=136，短链 Cnf1l8Ior4/DtYKgapMJM"}]}
io.open(p2,"w",encoding="utf-8").write(json.dumps(u, ensure_ascii=False, indent=2))
print("ledger ok")
