# -*- coding: utf-8 -*-
import os, datetime

stamp = '【2026-11-17 v48】'
msg = ('形象统一为人形：0 橘猫少年 / 1 白兔少女 / 2 狐狸少女 / 3 熊猫少女，'
       '6 蓝发少女 / 7 黑发少年 / 8 银发剑客 / 11 机械少年 全部改为成人比例手办质感；'
       'names.txt 与 voices.txt 补齐 14 项；'
       '新增两端自检：手机 App 打开即自检并上报（/selfcheck），电脑端接收存 手机自检.txt；'
       '新增每日 08:47 自动巡检（计划任务 DaoAutoInspect），报告落 巡检报告\\，'
       '问题自动入 待改进.md、修好的自动划掉。')

for fn in (r'F:\Daodao\同步日志.txt',):
    p = fn
    raw = open(p, 'rb').read() if os.path.exists(p) else b''
    bom = raw.startswith(b'\xef\xbb\xbf')
    txt = raw.decode('utf-8-sig') if raw else ''
    if not txt.endswith('\n'):
        txt += '\n'
    txt += stamp + msg + '\n'
    open(p, 'wb').write((b'\xef\xbb\xbf' if bom or not raw else b'') + txt.encode('utf-8'))
    print('已记录', p, len(txt.encode('utf-8')), '字节')

# 待优化：新开一节待办
p2 = r'F:\Daodao\待优化.txt'
raw = open(p2, 'rb').read() if os.path.exists(p2) else b''
bom2 = raw.startswith(b'\xef\xbb\xbf')
t2 = raw.decode('utf-8-sig') if raw else ''
if not t2.endswith('\n'):
    t2 += '\n'
t2 += ('\n【巡检待改 2026-11-17】\n'
       '1. 4 小恐龙 / 5 小企鹅 / 9 魔法师 / 10 古风少女 还是老 Q 版，需重做人形\n'
       '2. 6/7/8/11 的 pose 动作帧仍是老画风，换动作会跳回旧脸，需按新形象重生成\n'
       '3. 表情帧 expr_* 只有 0-11 且是老脸，12/13 无表情帧\n')
open(p2, 'wb').write((b'\xef\xbb\xbf' if bom2 or not raw else b'') + t2.encode('utf-8'))
print('已记录待优化', len(t2.encode('utf-8')), '字节')
