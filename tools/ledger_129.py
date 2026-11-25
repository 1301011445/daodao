# -*- coding: utf-8 -*-
"""v129 台账"""
import json, os

rec = ('2026-11-25 v129 人物配坐骑（每只坐骑单独定高度占比与脚踩比例，骑上人物缩 0.74；'
       '木马重做去底座、飞剑重做成水平；贴边探头冷却 2.5→20 秒）'
       'apk 17,087,029 https://aka.doubaocdn.com/s/D1KIDyBZdU，exe https://aka.doubaocdn.com/s/SQr5MkWbQb，'
       '两页 data-ver=129\r\n')
p = r'F:\Daodao\发版记录.txt'
s = open(p, encoding='utf-8').read()
if 'v129 人物配坐骑' not in s:
    open(p, 'a', encoding='utf-8').write(rec)
print('发版记录 OK')

led = r'F:\Daodao\自我状态\版本账本.json'
d = json.load(open(led, encoding='utf-8'))
d.setdefault('versions', []).append({
    'ver': 129, 'date': '2026-11-25', 'title': '人物配坐骑（按坐骑各自比例）',
    'apk': 17087029, 'apk_link': 'https://aka.doubaocdn.com/s/D1KIDyBZdU',
    'exe_link': 'https://aka.doubaocdn.com/s/SQr5MkWbQb',
})
d['current'] = 129
json.dump(d, open(led, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print('版本账本 current=129')

chk = r'F:\Daodao\能力检查\2026-11-25.md'
s = open(chk, encoding='utf-8').read() if os.path.exists(chk) else '# 2026-11-25\n'
if 'v129' not in s:
    s += ('\n## v129 人物与坐骑相互匹配（2026-11-25）\n'
          '- 需求：人物形象跟坐骑系统要相互匹配应用；形象可再优化；点它乱动还走掉复述一次\n'
          '- 测得的毛病：坐骑统一按「视窗宽 0.98 + 高 0.52 抬升」，导致木马/小鹿比人还小、飞剑几乎贴在脚前、'
          '抬升超过 0.26 视窗高时人物头顶会被切；木马素材带木底座、飞剑素材是斜放的\n'
          '- 素材层：木马重做（无底座、带鞍与缰绳，720×645）、飞剑重做（水平平放，720×236），均透明白像素 0\n'
          '- 代码层：MOUNT_MHW / MOUNT_FR 两张表，五只坐骑各自定「高占视窗比例」与「脚踩高度比例」；'
          '骑上时人物以底边中点为锚缩到 0.74，抬升换算回缩放坐标，头顶不再出画布\n'
          '- 复述的「点它乱动还走掉」再补一刀：贴边探头冷却 2.5 秒 → 20 秒（戳完不会又从边上缩回去）\n'
          '- 判据 M1~M6 PASS；预览 5 版迭代（_配比预览.png → 预览6.png）最终选定参数；'
          'dex date_time=2026-11-25 17:25:20\n')
    open(chk, 'w', encoding='utf-8').write(s)
print('能力检查 OK')
