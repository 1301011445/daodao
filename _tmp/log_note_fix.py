# -*- coding: utf-8 -*-
import io, sys, importlib

sys.path.insert(0, r'F:\Daodao\tools')
qb = importlib.import_module('问题库')

qb.register('记事本到点把待办自动标成「完成」，待办区变空',
            来源='手机截屏（2026-11-22 13:20）', 严重度='P1',
            说明='CheckNotes 在 dt<=now 时把非重复项 f[2] 置 1（当完成处理），用户没做的事也进「已完成」，记事本待办区显示「还没有登记的事」。改为到点只播报一次（f[3]=2），不再自动完成',
            key='note:auto-done')
qb.close('Q-086', note='pet.cs CheckNotes 改：非重复项到点只播报不标完成；f[3] 改三态（0 未预告/1 已预告/2 已播报）；待办过期由手机端显示「已过点，还没划掉」。已重编 exe 并实测：交材料恢复待办后 25 秒未被再标完成，/note?op=today 回「今天有1件：9点 交材料」',
          复现='1) 记事本加一条已过点的待办；2) 等 20 秒；3) GET /note?op=list 应仍为 done=0，且 /note?op=today 应把它念出来')

qb.register('build_exe.ps1 换包失败：Move-Item -Force 不覆盖已存在 exe',
            来源='2026-11-22 13:22 手动构建', 严重度='P2',
            说明='csc 编译成功并产出 _build_tmp.exe，但 Move-Item -Force 到已存在的 道.exe 报「当文件已存在时，无法创建该文件」，脚本中断，exe 仍是旧版；改成 Copy-Item -Force 覆盖 + 删临时件，并顺手清自愈冷却',
            key='build:move')
qb.close('Q-087', note='build_exe.ps1 v0.2：换包改 Copy-Item -Force；真跑一次回 BUILD_OK size=9851392 proc=1 res=113',
          复现='powershell -File F:\\Daodao\\tools\\build_exe.ps1 应在已存在 道.exe 的情况下仍回 BUILD_OK，且 道.exe 修改时间更新')

# 能力检查
with io.open(r'F:\Daodao\能力检查\2026-11-22.md', 'a', encoding='utf-8') as f:
    f.write('''
### 13:25 追加（记事本待办消失的真因 + 构建换包失败）

- 用户截屏：手机记事本待办区空，只有「已完成 开会；交材料」。查数据：`F:\\Daodao\\记事本.txt` 两条都是 done=1。
- 真因（Q-086）：`pet.cs` CheckNotes 里非重复项到点就 `f[2]="1"`（当完成），所以 09:00 的「交材料」被自己的提醒划掉了——待办区自然空。
- 修法：到点只播报、不标完成；`f[3]` 由二态改三态（0 未预告 / 1 已预告 / 2 已播报），已播报的不再重复吵，条目一直挂在待办里，过期由手机端显示「已过点，还没划掉」。
- 重编 exe（9,851,392B）→ 新进程 2072；实测：把「交材料」改回 done=0 后等 25 秒，仍是 done=0，`/note?op=today` 回「今天有1件：9点 交材料」。
- 附带查出构建脚本 bug（Q-087）：编译成功但 `Move-Item -Force` 不覆盖已存在 exe，报「当文件已存在时，无法创建该文件」，等于白编。改 `Copy-Item -Force` 覆盖并清自愈冷却，真跑回 `BUILD_OK size=9851392 proc=1 res=113`。
- 版本：exe 仍为 v0.107（本轮只修行为、未发版）；待 0.108 发版时把这条一起带上。
''')

with io.open(r'F:\Daodao\经验库.md', 'a', encoding='utf-8') as f:
    f.write('2026-11-22 | 主题：提醒不会被自己划掉 | 学到：到点自动置「完成」的提醒 = 待办消失的元凶；播报要留痕但不改完成态 | 来源：用户截屏 + 记事本.txt 实数据 | 改动：pet.cs CheckNotes 改三态 f[3]，build_exe.ps1 换包改 Copy-Item | 效果：/note?op=today 恢复念「9点 交材料」，构建回 BUILD_OK | 标签：#记事本 #构建 #Bug | 状态：已用 | 提交：未提交（pet.cs、build_exe.ps1 待随源码提交）\n')
    f.write('2026-11-22 | 主题：PowerShell 换文件 | 学到：Move-Item -Force 到已存在目标并不覆盖，会报「当文件已存在时，无法创建该文件」；要覆盖用 Copy-Item -Force 再删源 | 来源：build_exe.ps1 实测 | 改动：build_exe.ps1 v0.2 | 效果：真跑 BUILD_OK | 标签：#PowerShell #构建 | 状态：已用 | 提交：未提交\n')

with io.open(r'F:\Daodao\同步日志.txt', 'a', encoding='utf-8') as f:
    f.write('2026-11-22 13:25  修 Q-086 记事本到点自动完成（pet.cs→三态 f[3]，重编 exe 9851392B，进程 2072）；修 Q-087 build_exe.ps1 换包 Move-Item 不覆盖（改 Copy-Item，BUILD_OK）；记事本 交材料 恢复待办\n')

with io.open(r'F:\Daodao\待优化.txt', 'a', encoding='utf-8') as f:
    f.write('19|记事本「到点自动标完成」已修但只在本地 exe（线上包仍是旧行为）|中|待发版|0.108 发版时把 pet.cs 这处改动带上；否则新装的机器仍会把没做的待办塞进已完成\n')
print('Q-086/Q-087 已登记并关闭，日志已追加')
