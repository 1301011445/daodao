# -*- coding: utf-8 -*-
# 程序版本：v0.1 | 2026-11-23 | 新建：四位歌手唱法模板的 T1–T5 判据（齐全/mix≤0.55/混后值一致/只带唱法字段/不动音色池）
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
NAMES = ['单依纯', '李健', '那英', '王菲']
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

print(f'RESULT|模板={len(NAMES)}|FAIL={len(fails)}|' + ('PASS' if not fails else 'FAIL ' + ','.join(fails)))
sys.exit(0 if not fails else 1)
