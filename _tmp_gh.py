# -*- coding: utf-8 -*-
import io, json, os, time

# 1) 程序版本记录登记
jp = r"F:\Daodao\tools\程序版本记录.json"
d = json.load(open(jp, encoding="utf-8"))
name = "眨眼节律检查.py"
if not any(p["名称"] == name for p in d["程序"]):
    d["程序"].append({
        "名称": name, "路径": r"F:\Daodao\tools\神态\眨眼节律检查.py", "版本": "v0.1",
        "日期": "2026-11-22", "用途": "眨眼间隔分布判据（对数正态/双眨/源码断言 6 条）",
        "改动": "新建：复算 pet.cs 同款分布 + 静态断言",
        "文件修改日": "2026-11-22", "已插版本头": True,
    })
    json.dump(d, open(jp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("PROG_ADDED", len(d["程序"]))

# 2) 学习台账
with io.open(r"F:\Daodao\学习台账.txt", "a", encoding="utf-8") as f:
    f.write("""
2026-11-22 19:20 | 第17条 GitHub 学习（不上传）：真人眨眼间隔是对数正态而非均匀分布 | 来源：GitHub kirklasalle/SkyrimTrueGaze（NPC 眼动/眨眼生物力学建模）、jayzuccarelli/saccade（adaptive cadence：节奏由情境决定）、GitHub topics/saccade（同类实现对照）| 做法：pet.cs 眨眼间隔改对数正态（Irwin–Hall 4 均匀→正态→exp，中位 3.2s，0.6~18s 截断），双眨 25% 保留 | 真跑：tools\\神态\\眨眼节律检查.py 6/6 PASS（中位 3.21s、p10 1.56s、p90 6.51s、双眨 25.3%、源码断言 log=1 old=0）| 未上传：按用户要求本轮只学不改远端，exe 本地已编译，线上仍是今日 112
""")

# 3) 经验库
with io.open(r"F:\Daodao\经验库.md", "a", encoding="utf-8") as f:
    f.write("""
2026-11-22 | 主题：从 GitHub 的 NPC 眼动建模学「眨眼节律不该是节拍器」 | 学到：真人眨眼间隔服从对数正态（多数 3-4 秒，长尾十几秒），开源 NPC gaze 项目把它当生物力学参数建；均匀随机分布肉眼上就是机械滴答 | 来源：github.com/kirklasalle/SkyrimTrueGaze、github.com/jayzuccarelli/saccade、github.com/topics/saccade | 改动：pet.cs OnTick 眨眼分支（对数正态 + 0.6/18s 截断 + 双眨 25%）；新增 tools\\神态\\眨眼节律检查.py | 效果：判据 6/6 PASS（中位 3.21s/p10 1.56/p90 6.51/双眨 25.3/旧均匀分布已移除）；编译 BUILD_OK、ping 112 正常 | 标签：#神态 #动作 | 状态：已用（本地验证，未发布）
""")

# 4) 今日所学追加
with io.open(r"F:\Daodao\今日所学.txt", "a", encoding="utf-8") as f:
    f.write("""
5. GitHub 侧（只学不上传）：真人眨眼间隔是对数正态而不是均匀分布，开源 NPC 眼动项目（SkyrimTrueGaze 一类）把它当可调生物力学参数；
   均匀随机在肉眼上就是节拍器。落地后中位 3.21s、p90 6.51s、双眨 25.3%，判据 6/6 PASS。
6. jayzuccarelli/saccade 的 adaptive cadence 值得抄：节奏不该由代码写死，该由"情境有多安静"决定——这条留给手机端浮窗的探头频率。
""")

# 5) 发版记录
with io.open(r"F:\Daodao\发版记录.txt", "a", encoding="utf-8") as f:
    f.write("""
2026-11-22 19:20 | 未发版（用户要求先不上传）| 本地 exe 已编译（眨眼节律改对数正态），APP_VER 仍 112、体积 9,937,920 B 与线上同号但内容不同 | 下一轮发布时统一升 113 并重打 apk，避免同号不同物
""")

# 6) 同步日志
with io.open(r"F:\Daodao\同步日志.txt", "a", encoding="utf-8") as f:
    f.write("2026-11-22 19:20 GitHub 学习落地：眨眼间隔改对数正态（中位 3.21s/双眨 25.3%），判据 6/6 PASS；按用户要求未上传，线上仍 112\n")
print("TEXT_OK")
