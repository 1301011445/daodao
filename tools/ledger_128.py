# -*- coding: utf-8 -*-
"""v128 台账"""
import json, os

line = ('2026-11-25 v128 点它别乱跑（走路不再挪窗口=原地迈步；拖动阈值 6→16dp；单击只应声、双击开 App、长按不换形象；'
        '碰过之后 8 秒内不自己走）apk 17,087,029 https://aka.doubaocdn.com/s/ZWSGwOBg5X，'
        'exe https://aka.doubaocdn.com/s/RvIjGAfbfs，两页 data-ver=128\r\n')
p = r'F:\Daodao\发版记录.txt'
s = open(p, encoding='utf-8').read()
if 'v128 点它别乱跑' not in s:
    open(p, 'a', encoding='utf-8').write(line)
print('发版记录 OK')

led = r'F:\Daodao\自我状态\版本账本.json'
d = json.load(open(led, encoding='utf-8'))
d.setdefault('versions', []).append({
    'ver': 128, 'date': '2026-11-25', 'title': '点它别乱跑（走路=原地迈步）',
    'apk': 17087029, 'apk_link': 'https://aka.doubaocdn.com/s/ZWSGwOBg5X',
    'exe_link': 'https://aka.doubaocdn.com/s/RvIjGAfbfs',
})
d['current'] = 128
json.dump(d, open(led, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print('版本账本 current=128')

chk = r'F:\Daodao\能力检查\2026-11-25.md'
s = open(chk, encoding='utf-8').read() if os.path.exists(chk) else '# 2026-11-25\n'
if 'v128' not in s:
    s += ('\n## v128 点它别乱跑（2026-11-25）\n'
          '- 用户反馈：点「道」的时候它乱动还走掉；补充说明「走路不是移动」\n'
          '- 根因 1：walkDrift 真的把悬浮窗按 2dp/拍（≈22dp/秒）横向推，一趟 3~5 秒就是走出小半屏 → 看着像跑掉\n'
          '- 根因 2：ACTION_MOVE 判定只有 6dp，手指抖动被当成拖动，窗口跟手乱窜\n'
          '- 根因 3：ACTION_UP 里「按住 >400ms 未移动」直接 cycleArt() 换形象 → 点慢一点就变脸\n'
          '- 根因 4：点一下直接 openApp()，整只消失，也被当成走掉\n'
          '- 改法：walk 只播八帧+骨盆分腿动画、窗口原地不动；拖动阈值 16dp；按下即收步；碰过后 8 秒不自己走；'
          '单击=站定+应声（点头/挥手/说一句）、双击=开 App、长按不再换形象\n'
          '- 判据 P1~P6 PASS；dex date_time=2026-11-25 17:15:22 证明真重编\n')
    open(chk, 'w', encoding='utf-8').write(s)
print('能力检查 OK')
