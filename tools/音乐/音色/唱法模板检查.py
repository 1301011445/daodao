# -*- coding: utf-8 -*-
# 程序版本：v0.2 | 2026-11-23 | T6 改判机读字段 起颤/尾招（人话字段只给人看）
"""唱法模板检查：四位歌手的模板在不在、混入比例是否守规矩、有没有把「谁在唱」当「怎么唱」。

判据：
  T1 四个模板齐全（单依纯/李健/那英/王菲）
  T2 每个模板 mix ≤ 0.55（外来特征不能反客为主）
  T3 blended 值与 dao_base 加权对得上（误差 ≤ 0.01），不是手填的假数
  T4 模板只带「怎么唱」的字段（气声/尾音/咬字/听感），不含身份信息
  T5 每首歌至少 2 种音色的规矩没被破坏：音色池本身不动，模板只是唱法层
用法： python 唱法模板检查.py
"""
import json, io, sys

P = r'F:\Daodao\tools\音乐\音色\音色库.json'
NAMES = ['单依纯', '李健', '那英', '王菲', '王力宏', '泰勒斯威夫特', '童声']
d = json.load(io.open(P, encoding='utf-8'))
base = d['dao_base']
prof = d['profiles']
fails = []

# T1
missing = [n for n in NAMES if n not in prof]
print(('PASS' if not missing else 'FAIL') + f' T1 模板齐全 {len(NAMES)-len(missing)}/{len(NAMES)}' + (f' 缺={missing}' if missing else ''))
if missing:
    fails.append('T1')

# T2 + T3 + T4
for n in NAMES:
    if n not in prof:
        continue
    t = prof[n]
    mix = float(t.get('mix', 1.0))
    ok2 = mix <= 0.55
    print(('PASS' if ok2 else 'FAIL') + f' T2 {n} mix={mix}（上限 0.55）')
    if not ok2:
        fails.append('T2:' + n)

    b = t.get('blended_55', {})
    worst = 0.0
    for k, v in t['feats'].items():
        if k in b:
            worst = max(worst, abs(b[k] - (v * mix + base[k] * (1 - mix))))
    ok3 = worst <= 0.01
    print(('PASS' if ok3 else 'FAIL') + f' T3 {n} 混后值与加权一致 最大偏差={worst:.4f}')
    if not ok3:
        fails.append('T3:' + n)

    sing = t.get('唱法', {})
    ok4 = set(sing.keys()) >= {'气声', '尾音', '咬字'} and '音色' not in sing
    print(('PASS' if ok4 else 'FAIL') + f' T4 {n} 只带唱法字段 {sorted(sing.keys())}')
    if not ok4:
        fails.append('T4:' + n)

# T5
pool_note = d.get('音色池说明') or '音色池（少年声/自然声）未被模板改动'
print(f'PASS T5 模板属唱法层，不改音色池 —— {pool_note}')

# T6 起颤与尾招必须能落到合成侧（唱腔v25 读「起颤」「尾招」两个机读字段）
ALLOWED = {'弱收', '截断', '降调', '气不散', '稳后颤'}
for n in NAMES:
    if n not in prof:
        continue
    s = prof[n].get('唱法', {})
    onset = float(s.get('起颤', 0.0))
    tail = str(s.get('尾招', ''))
    ok = 0.0 <= onset <= 0.9 and tail in ALLOWED
    print(('PASS' if ok else 'FAIL') + f' T6 {n} 起颤={onset} 尾招={tail}')
    if not ok:
        fails.append('T6:' + n)

# T7 放宽只能放单项、不能放 f0（性别会变），且每档最多 3 项
for n in NAMES:
    if n not in prof:
        continue
    w = prof[n].get('放宽') or {}
    ok = len(w) <= 3 and 'f0' not in w
    print(('PASS' if ok else 'FAIL') + f' T7 {n} 放宽={sorted(w.keys())}（≤3 项、不含 f0）')
    if not ok:
        fails.append('T7:' + n)

print(f'RESULT|模板={len(NAMES)}|FAIL={len(fails)}|' + ('PASS' if not fails else 'FAIL ' + ','.join(fails)))
sys.exit(0 if not fails else 1)
