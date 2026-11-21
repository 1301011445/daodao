# -*- coding: utf-8 -*-
import sys, json
sys.path.insert(0, r'F:\Daodao\tools')
import 问题库 as P

solved = [
 ('Q-060', 'Done/RollDone 改成：重复项（D/W/M）标完成＝滚到下一次（when 用 NextWhen 追到未来、warned 清零、done 仍 0），CheckNotes 里再兜底把历史上被标完成且带重复的行救回来。实测 doneby 打卡 → 2026-11-23 08:00 仍 D、done=0；旧数据 id4/id6 自动恢复。'),
 ('Q-061', 'doneby/delby 不再「第一条命中就 break」，改成在命中项里挑「已完成优先靠后、时间最早」的一条。实测同名两条 交材料(11-22 09:00 / 10:00) → 命中 09:00 那条。'),
 ('Q-062', 'NOTE_RE 增加两种句首：①每天/每日/每周/每星期/每月/明天/后天/大后天/今早/今晚… + 时间点；②早上/晚上/中午/凌晨… + 时间点。实测「每天 早上八点 打卡」「早上八点 打卡」「九点 交材料」都走登记。'),
 ('Q-063', '说「做完了/搞定了/删掉」前先 noteMatchTodo：拿镜像里的待办名与句子互相比对（含「第 N 条」），认不出就当闲聊（或短命令句给一句「没找到这条」）。实测「今天工作完成了，陪我聊会」「这个需求总算搞定了」→ 闲聊。'),
 ('Q-064', 'NOTE_DEL_RE 补上裸「去掉/拿掉/划掉/不要这条」和「别(再|又)?提醒/不用(再)?提醒」。实测「把体检去掉」「别再提醒开会了」→ 删除。'),
 ('Q-065', 'noteAdd/noteBy 用 noteHuman 把人话时间念出来（11月22日9点），重复项还能带上「每天」并说下次时间；add 接口回包追加重复标记。'),
 ('Q-066', '__daoAlarm 响过一次后 1.5s 自动 noteSync，重复提醒的下一次立刻排上手机闹钟。'),
]
for pid, note in solved:
    ok = P.close(pid, note)
    print(pid, ok)
print(P.summary()['open'], '条还开着')
