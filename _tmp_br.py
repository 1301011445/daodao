# -*- coding: utf-8 -*-
import io, json

# 1) 程序版本记录：登记呼吸节律检查
jp = r"F:\Daodao\tools\程序版本记录.json"
d = json.load(open(jp, encoding="utf-8"))
name = "呼吸节律检查.py"
if not any(p["名称"] == name for p in d["程序"]):
    d["程序"].append({
        "名称": name, "路径": r"F:\Daodao\tools\神态\呼吸节律检查.py", "版本": "v0.1",
        "日期": "2026-11-22", "用途": "待机呼吸判据（周期抖动/吸气占比/波形连续/静态断言 6 条）",
        "改动": "新建：复算 BrWave 波形 + 源码断言",
        "文件修改日": "2026-11-22", "已插版本头": True,
    })
    json.dump(d, open(jp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("PROG", len(d["程序"]))

# 2) 学习台账
with io.open(r"F:\Daodao\学习台账.txt", "a", encoding="utf-8") as f:
    f.write("""
2026-11-22 19:35 | 第17条 GitHub 学习（二）：待机呼吸不是等周期正弦 | 来源：pixiv/three-vrm（待机呼吸按周期随机+幅度缓变）、kirklasalle/SkyrimTrueGaze（呼吸/眨眼当生理节律参数）、GitHub topics/idle-animation（同类对照）| 做法：pet.cs 呼吸改相位推进（周期 3.6~5.2s 每口气重取、吸气占 38%、幅度 ±5%、两段半余弦在接缝处连续）| 真跑：tools\\神态\\呼吸节律检查.py 6/6 PASS（中位 4.40s、跨度 1.60s、吸气 0.38、接缝误差 3.4e-9/1.3e-7、单步 0.099）| 未上传：按用户要求暂停，exe 本地编译 9,938,432 B、ping 112、paint_err 无、进程 1
""")

# 3) 经验库
with io.open(r"F:\Daodao\经验库.md", "a", encoding="utf-8") as f:
    f.write("""
2026-11-22 | 主题：从 GitHub 待机动画学「呼吸要有周期抖动和吸呼不对称」 | 学到：真人静息呼吸 12-18 次/分（周期 3.3-5.0s），吸气短于呼气约 4:6，每口气幅度小幅浮动；等周期纯正弦在肉眼上是"晃"不是"呼吸" | 来源：github.com/pixiv/three-vrm、github.com/kirklasalle/SkyrimTrueGaze、github.com/topics/idle-animation | 改动：pet.cs 新增 brT/brPeriod/brPh/brAmpJit 与 BrStep/BrWave/BrValue，PaintAll 的 breathe 改读 BrValue()；OnTick 每帧 BrStep(dt) | 效果：判据 6/6 PASS（中位 4.40s/跨度 1.60s/吸气 0.38/接缝 3.4e-9/单步 0.099）；BUILD_OK 9,938,432 B、ping 112、paint_err 无 | 标签：#神态 #动作 | 状态：已用（本地验证，未发布）
""")

# 4) 今日所学
with io.open(r"F:\Daodao\今日所学.txt", "a", encoding="utf-8") as f:
    f.write("""
7. GitHub 侧（第二课）：待机呼吸要"周期随机 + 吸气短呼气长 + 幅度浮动"，纯正弦看着是晃不是喘。
   落地：周期 3.6~5.2s、吸气 38%、接缝误差 3.4e-9，判据 6/6 PASS。
8. 排队待用的开源思路：jayzuccarelli/saccade 的 adaptive cadence（节奏由情境决定）→ 手机浮窗探头频率；
   SkyrimTrueGaze 的 micro-saccadic drift → 位图眼睛动不了，记为"不适用"，别硬搬。
""")

# 5) 待优化：两条排队项（标明来源，宁可不做也不硬搬）
with io.open(r"F:\Daodao\待优化.txt", "a", encoding="utf-8") as f:
    f.write("""101|手机浮窗探头频率改自适应节奏（安静时 8-20s 一探，有动静时 2-4s）：抄 jayzuccarelli/saccade 的 adaptive cadence|P2|待修|2026-11-22 登记
102|桌面端再加一层"呼吸相位耦合"：眨眼更容易落在呼气末（SkyrimTrueGaze 的 blink-breath coupling），本轮只做了眨眼分布，没做耦合|P2|待修|2026-11-22 登记
""")

# 6) 同步日志
with io.open(r"F:\Daodao\同步日志.txt", "a", encoding="utf-8") as f:
    f.write("2026-11-22 19:35 GitHub 学习二：呼吸改 3.6~5.2s 抖动 + 吸气 38% 半余弦波形，判据 6/6 PASS；exe 9,938,432 B 本地编译，按用户要求未上传\n")
print("TEXT_OK")
