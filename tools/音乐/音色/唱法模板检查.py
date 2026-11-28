# -*- coding: utf-8 -*-
# 程序版本：v0.3 | 2026-11-28 | 跟着 11-24 的决定改口径：旧参考歌手全退役，判「道自己的三声型」
"""唱法模板检查（v2 口径）：2026-11-24 用户判定旧参考歌手融合档不喜欢，全部退役进 legacy；
音色库改成道自己的三声型（少年声 / 自然声 / 低语声），每首歌至少用 2 种。
判据跟着改，不是把门槛放低——旧判据查「歌手模板齐全」，现在查「三声型齐全、比例规矩、身份不回流」。

判据：
  T1 三个声型齐全（少年声 / 自然声 / 低语声）
  T2 每档 feats.mix ≤ 0.55（融合比例不能反客为主）
  T3 每档 feats 字段齐全（f0/range_semi/vib_rate/vib_depth/breath/centroid/tilt/dyn/mix）
  T4 音色池里不出现歌手身份（旧歌手名只能留在 legacy，不许回流 profiles）
  T5 「每首歌至少用 2 种音色」这条规矩写在库里
  T6 三声型音高有序：低语 < 自然 < 少年（清亮偏高），差 ≥ 10Hz，免得三档听着是一档
  T7 legacy 只作历史：legacy 里的名字一个都不在 profiles
用法： python 唱法模板检查.py
"""
import json, io, sys

P = r'F:\Daodao\tools\音乐\音色\音色库.json'
VOICES = ['少年声', '自然声', '低语声']
FIELDS = {'f0', 'range_semi', 'vib_rate', 'vib_depth', 'breath', 'centroid', 'tilt', 'dyn', 'mix'}

d = json.load(io.open(P, encoding='utf-8'))
prof = d.get('profiles', {})
legacy = d.get('legacy', {})
fails = []

missing = [n for n in VOICES if n not in prof]
print(('PASS' if not missing else 'FAIL') + ' T1 三声型齐全 %d/%d' % (len(VOICES) - len(missing), len(VOICES))
      + (' 缺=%s' % missing if missing else ''))
if missing:
    fails.append('T1')

for n in VOICES:
    if n not in prof:
        continue
    f = prof[n].get('feats', {})
    mix = float(f.get('mix', 1.0))
    ok2 = mix <= 0.55
    print(('PASS' if ok2 else 'FAIL') + ' T2 %s mix=%.2f（上限 0.55）' % (n, mix))
    if not ok2:
        fails.append('T2:' + n)

    lack = sorted(FIELDS - set(f.keys()))
    ok3 = not lack
    print(('PASS' if ok3 else 'FAIL') + ' T3 %s feats 齐全 %s' % (n, '缺=%s' % lack if lack else len(FIELDS)))
    if not ok3:
        fails.append('T3:' + n)

bad_id = [n for n in prof if n in legacy]
print(('PASS' if not bad_id else 'FAIL') + ' T4 音色池不带歌手身份 %s' % (bad_id or '0 个'))
if bad_id:
    fails.append('T4')

note = (d.get('说明') or '') + ' ' + str(d.get('音色池说明') or '')
ok5 = '至少' in note and '2' in note
print(('PASS' if ok5 else 'FAIL') + ' T5 「每首至少 2 种音色」写进库 %s' % ('有' if ok5 else '没写'))
if not ok5:
    fails.append('T5')

if all(n in prof for n in VOICES):
    f0 = {n: float(prof[n]['feats']['f0']) for n in VOICES}
    ok6 = f0['低语声'] + 10 <= f0['自然声'] and f0['自然声'] + 10 <= f0['少年声']
    print(('PASS' if ok6 else 'FAIL') + ' T6 音高有序 低语%.0f < 自然%.0f < 少年%.0f（每档差≥10Hz）'
          % (f0['低语声'], f0['自然声'], f0['少年声']))
    if not ok6:
        fails.append('T6')

leak = [n for n in legacy if n in prof]
print(('PASS' if not leak else 'FAIL') + ' T7 legacy 只作历史（%d 个旧档）回流 %s' % (len(legacy), leak or '0 个'))
if leak:
    fails.append('T7')

print('RESULT|音色=%d|FAIL=%d|' % (len(VOICES), len(fails)) + ('PASS' if not fails else 'FAIL ' + ','.join(fails)))
sys.exit(0 if not fails else 1)
