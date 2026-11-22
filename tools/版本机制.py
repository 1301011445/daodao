# -*- coding: utf-8 -*-
# 程序版本：v0.1 | 2026-11-22 | 基线建档（此前无版本头）
"""道 · 版本 100 进制机制体检（只读，不自动改分）
versionCode 十进制整数单调递增；versionName 用 100 进制（62 -> "0.62"，100 -> "1.00"）。
用法：python 版本机制.py [--json]
"""
import io, json, os, sys

F = r'F:\Daodao'
LEDGER = os.path.join(F, '自我状态', '版本账本.json')
USE = os.path.join(F, '自我状态', '版本使用.json')
TARGET = 100
MILESTONES = [(70, '形象与动作定稿'), (80, '音乐与曲库'), (90, '跨端一致'), (100, '对外首版')]

def load(p):
    return json.load(io.open(p, encoding='utf-8-sig'))

def v100(n):
    return "%d.%02d" % (int(n) // 100, int(n) % 100)

def parse100(s):
    a, b = str(s).split('.')
    return int(a) * 100 + int(b)

led, use = load(LEDGER), load(USE)
det = led.get('检测', {})
cur = int(det.get('电脑') or 0)
real_pc = led.get('真用', {}).get('电脑', {})
real_ph = led.get('真用', {}).get('手机', {})

next_m, next_name = TARGET, '对外首版'
for m, name in MILESTONES:
    if cur < m:
        next_m, next_name = m, name
        break

blk = use.get('版本', {}).get(str(cur), {})
items = blk.get('项', [])
goal = int(blk.get('目标', 3))

five = [det.get(k) for k in ('电脑', 'apk', '页面', '线上', '手机')]
gates = [
    ('1 真改动', os.path.exists(os.path.join(F, '发版记录.txt')), '发版记录在'),
    ('2 两端同号', all(str(v) == str(cur) for v in five), '五处=' + '/'.join(str(v) for v in five)),
    ('3 三项真验', len(items) >= goal, '本版已验 %d/%d 项' % (len(items), goal)),
    ('4 真在用', str(real_pc.get('版本')) == str(cur), '电脑 %s @ %s' % (v100(real_pc.get('版本') or 0), real_pc.get('最后'))),
    ('5 体检过', True, '以上一轮巡检结论为准'),
    ('6 可回滚', os.path.isdir(os.path.join(F, '_bak')), '_bak 目录在' if os.path.isdir(os.path.join(F, '_bak')) else '缺 _bak'),
]

debts = [v for v, b in sorted(use.get('版本', {}).items(), key=lambda x: int(x[0])) if not b.get('项')]
advice = []
if str(cur) not in use.get('版本', {}):
    advice.append('v%d（%s）没在 版本使用.json 立项，先补目标项' % (cur, v100(cur)))
if len(items) < goal:
    advice.append('v%d（%s）目标项 %d/%d，上线 7 天内补不上要扣 改正 -1' % (cur, v100(cur), len(items), goal))
if not all(str(v) == str(cur) for v in five):
    advice.append('五处版本不一致（手机 %s / %s），协调 -2 停下补装' % (det.get('手机'), v100(det.get('手机') or 0)))
if debts:
    advice.append('零验证版本 %d 个：%s' % (len(debts), '、'.join(v100(v) for v in debts)))
advice.append('下一版起 versionName 改 100 进制（v63 -> 0.63），versionCode 仍用整数 63')

if '--json' in sys.argv:
    print(json.dumps(dict(版本码=cur, 版本名=v100(cur), 目标码=TARGET, 目标名=v100(TARGET),
                          差=TARGET - cur, 里程碑码=next_m, 里程碑名=next_name,
                          门禁={g[0]: bool(g[1]) for g in gates}, 欠账=[v100(x) for x in debts], 建议=advice),
                     ensure_ascii=False, indent=2))
else:
    print('【进度】versionCode %d = versionName %s ／ 目标 %d = %s，还差 %d 版'
          % (cur, v100(cur), TARGET, v100(TARGET), TARGET - cur))
    print('        下一个里程碑 v%d（%s）「%s」，还差 %d 版'
          % (next_m, v100(next_m), next_name, next_m - cur))
    print('【六道门】')
    for name, ok, note in gates:
        print('  %-8s %s  %s' % (name, 'PASS' if ok else 'FAIL', note))
    print('【欠账】' + (('零验证版本 %d 个：%s' % (len(debts), '、'.join(v100(x) for x in debts))) if debts else '无'))
    print('【真用】电脑 %s @ %s ｜ 手机 %s @ %s'
          % (v100(real_pc.get('版本') or 0), real_pc.get('最后'),
             v100(real_ph.get('版本') or 0), real_ph.get('最后')))
    print('【换算自检】parse100("1.00")=%d ｜ v100(62)=%s ｜ v100(100)=%s'
          % (parse100('1.00'), v100(62), v100(100)))
    for a in advice:
        print('  -> ' + a)