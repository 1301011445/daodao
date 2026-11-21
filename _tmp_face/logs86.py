# -*- coding: utf-8 -*-
import io, datetime
now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

fb = """
[%s] v0.86 修复"手机端人物消失"
- 根因：dao.html 的 redraw() 里剑客跳舞分支写成 var swayX，var 提升到整个函数作用域，
  把外层 swayX 遮蔽成 undefined；除剑客跳舞这一支，其它形象走到
  ctx.translate(CX + dx + walkX + swayX, footY + hopY + bob) 时 x=NaN，
  整条变换矩阵失效，人物整幅不绘制（界面/按钮/帧率都正常，所以肉眼像"人没了"）。
- 改法：局部变量改名 dSway；translate/rotate/scale 前加 isFinite 兜底，坏值时退回站姿位置并 console.warn。
- 验证：本机浏览器实跑 file:// dao.html。修前画布不透明像素只在左上角一条 456x45、人物 0 像素；
  修后 黑发少年 完整绘制、58fps。自检 27/27 通过。
- 打包：apk versionCode=86 / versionName=0.86，apksigner 验签通过，包内 assets/dao.html MD5 与源码一致。
- 发版：apk https://aka.doubaocdn.com/s/3lPW2VauvA  exe https://aka.doubaocdn.com/s/5Do7LRrMAe
  清单页 app_17hpue26uuw / 落地页 app_17jdxkgf27q 两次都 status=finished，线上 data-ver=86。
  落地页首次发布缺 9 张 assets 图（云主机没有本地素材），已补齐后重发，file_count=11。
- 顺带修：check_and_feed.ps1 版本比较把 "0.86" 用 -split'.'[0] 取成 "0"，误报"两端版本不一致"；
  改为去掉前导 "0." 再比，复跑结论=正常、退出码 0。
""" % now

sj = """
[%s] 体检轮（v0.86）
- 第零步：13 个 Dao 计划任务 WakeToRun 全为 True，无需改设置。
- 第一步 daily_sync：随身版网页已更新、apk 内页面已是最新、功能体检齐全。
- 第二步 体检：进程 1 个、/ping=OK|道|86|192.168.2.115|8848、无待装更新、话术 74 行 / 知识 90 行 / 记忆 15 行。
- 第18条 双端真跑：自检 27/27 通过；手机端只验了包（HTML_VER=86、桥接 26 方法、曲库 3 首、无废 wav、JS 语法 0 错），没有实机点。
- 第23条 巡检：结论=正常（详见 反馈.txt 最后一行）。
- 本轮遗留（写进待优化，不假装解决）：
  1) 语音首字延迟：电脑端 TTS 0.02s 正常，手机端真机首字延迟仍无实测数字。
  2) 录音链路（边说边传切片 ASR）补丁还没落到 DaoBridge.java。
  3) 人物消失只在浏览器验过，真机需用户装 v86 后再看一眼。
""" % now

neng = """
## 2026-11-21 10:2x 体检轮补充（十项能力打分 + 应用对照表）

| 能力 | 分数 | 依据（真跑数字） |
|---|---|---|
| 版本能力 | 95 | 五处/线上全 86；账本 检测一致=True |
| 检查能力 | 88 | 自检 27/27；巡检误报已修，复跑结论=正常、exit 0 |
| 解决问题能力 | 85 | Q-058 P0 当天定位→改→验→结案，未超 7 天 |
| 渲染能力 | 82 | 修前 bbox 仅 456x45、修后人物完整且 58fps |
| 形象能力 | 78 | 人物正常渲染；dao.html 里 face()/tear() 已删（贴图表情=0） |
| 动作能力 | 72 | walk8.png 899,704 字节在包内；口型层仍空，未测偏移 |
| 纠错能力 | 72 | 本轮回登记 1 条并当天结案；复发 2 条（Q-007/Q-032）待跟 |
| 语音能力 | 62 | 电脑 TTS 10,368 字节 0.01s；手机端首字延迟无真机数字 |
| 创作能力 | 60 | 体检轮未推进写曲；沿用上一轮 |
| 学习能力 | 55 | 体检轮按排班不推进新类别（学习排在傍晚更新轮） |

未解决 18 条（open）+ 2 条（wait）；本轮新增登记 1 条（Q-058，已 solved）。

### 应用对照表（本轮）

| 经验 | 应用方式 | 改动位置 | 验证结果 | 生效 |
|---|---|---|---|---|
| var 提升会遮蔽同名外层变量，NA→NaN 会让整条变换失效 | 改代码 | dao.html redraw() 跳舞分支（局部改名 dSway） | 修前人物 0 像素 → 修后完整绘制 58fps | 2026-11-21 已生效 |
| 坐标/缩放这类关键参数要挡非法值 | 改代码 | dao.html translate/rotate/scale 前的 isFinite 兜底 | 坏值时退回站姿并 console.warn | 2026-11-21 已生效 |
| 版本号比较要先归一（"0.86" ≠ "0"） | 改检查流程 | tools/check_and_feed.ps1 第 94 行 | 复跑 结论=正常、exit 0 | 2026-11-21 已生效 |

下一轮先改：手机端语音首字延迟（真机取样）+ 录音分块上传落地。
"""

for path, txt in ((r"F:\Daodao\发版记录.txt", fb), (r"F:\Daodao\同步日志.txt", sj),
                  (r"F:\Daodao\能力检查\2026-11-21.md", neng)):
    io.open(path, "a", encoding="utf-8").write(txt)
    print("追加", path)

exp = ("%s | 主题：手机端人物消失是变量提升遮蔽 | 学到：var 在函数内提升会遮蔽外层同名变量，"
       "被遮蔽的位移量参与 translate 会得到 NaN，变换矩阵失效后整幅不绘制且不报错 | "
       "来源：MDN var hoisting / canvas transform NaN 行为 | "
       "改动：F:\\Daodao\\src\\_apk\\assets\\dao.html redraw() 局部变量 dSway + isFinite 兜底，v0.86 | "
       "效果：修前画布仅 456x45 像素、修后人物完整 58fps，自检 27/27 | "
       "标签：#渲染 #动作 #打包 #检查 | 状态：已用 | 提交：待提交\n") % now
io.open(r"F:\Daodao\经验库.md", "a", encoding="utf-8").write(exp)
print("经验库已追加")
