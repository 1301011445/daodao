# -*- coding: utf-8 -*-
import sys, os
sys.path.insert(0, r'F:\Daodao\tools')
import 问题库 as P

items = [
    ('重复提醒（每天/每周/每月）被语音标成做完后永久不再响，记事本里成死条目',
     '两端联调', 'P1', 'doneby/done 直接把 done 置 1，CheckNotes 见 done=1 就跳过；重复项应该滚到下一次。',
     'note_repeat_done'),
    ('doneby/delby 按关键字命中第一条，同名待办会改错条',
     '两端联调', 'P2', '循环 break 在第一条命中就停，按文件行序而不是离得最近的一条。',
     'note_doneby_hit'),
    ('语音说「每天/每周/每月…」开头的话不登记，被判成闲聊',
     '两端联调', 'P1', 'NOTE_RE 用 ^ 锚死触发词，句首是时间/重复词就不认；实测「每天 早上八点 打卡」→ 闲聊。',
     'voice_route_norepeat'),
    ('含「完成了/搞定了」的闲聊被当成记事本操作，会误改数据',
     '两端联调', 'P1', 'NOTE_DONE_RE 只看关键词不看对象；实测「今天工作完成了，陪我聊会」「这个需求总算搞定了」都进了 doneby。',
     'voice_route_false_done'),
    ('「把体检去掉」「别再提醒开会了」这类说法不认，落进闲聊',
     '两端联调', 'P2', 'NOTE_DEL_RE 只认「去掉这条」「不用提醒了」，中间夹「再」或裸「去掉」都不匹配。',
     'voice_route_del'),
    ('手机端登记成功后念的是「2026-11-22 09:00」这种机器日期',
     '两端联调', 'P2', 'noteAdd 直接念接口回的原始 when 串，没转成「M月d日H点m分」。',
     'note_add_speak'),
    ('手机本地闹钟响过之后不重排重复提醒的下一次',
     '两端联调', 'P2', '__daoAlarm 只念不同步，重复项的下一次要等页面下次刷新才排上。',
     'phone_alarm_repeat'),
]
for t, s, sev, note, key in items:
    r = P.register(t, 来源=s, 严重度=sev, 说明=note, key=key)
    print(r)
