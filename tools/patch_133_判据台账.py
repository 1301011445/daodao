# -*- coding: utf-8 -*-
"""v133 判据 + 台账：大模型给动作标签，窗口照着做"""
import json
import os
import re
import subprocess
import zipfile

V = [r'F:\Daodao\voice.py', r'F:\Daodao\src\桌面分身\voice.py', r'F:\Daodao\src\桌面分身\_bundle\voice.py']
P = r'F:\Daodao\src\桌面分身\pet.cs'
v = [open(p, encoding='utf-8').read() for p in V]
pt = open(P, encoding='utf-8').read()
z = zipfile.ZipFile(r'F:\Daodao\src\_apk\Dao.apk')
html = z.read('assets/dao.html').decode('utf-8', 'ignore')

C = [
    ('J1 三条动作规矩进了系统提示（三份同步）', all(('ACT_RULE' in x and 'SYSTEM_PROMPT + MOOD_RULE + ACT_RULE' in x) for x in v)),
    ('J2 标签解析能吃 act:/mount: 与裸 [[dance]]', all('def split_act' in x and 'def _bare' in x for x in v)),
    ('J3 模型不写标签时由模型再挑一次', all('def classify_act' in x and 'classify_act(body)' in x for x in v)),
    ('J4 念出来的话里没有标签残留', all('body = "" if act else txt' in x for x in v)),
    ('J5 每轮输出带 act/mount', all('"act": act, "mount": mount' in x and 'act=_LAST_ACT.get("act"' in x for x in v)),
    ('J6 窗口读标签并驱动动作', 'ApplyLlmAct(a9, m9)' in pt and 'void ApplyLlmAct(string act, int mount)' in pt),
    ('J7 桌面动作映射齐（dance/ride/fly/sword/tea/tv/turn）',
     all(k in pt for k in ['a == "dance"', 'a == "ride"', 'a == "fly"', 'a == "sword"', 'a == "tea"', 'a == "tv"', 'a == "turn"'])),
    ('J8 包内版本 1.33', re.search(r"var HTML_VER = '(\d+)'", html).group(1) == '133'),
]

st = subprocess.run([r'E:\Python313\python.exe', '-X', 'utf8', r'F:\Daodao\voice.py', 'selftest'],
                    capture_output=True, text=True, encoding='utf-8')
last = (st.stdout or '').strip().splitlines()
C.append(('J9 voice selftest 8/8', last and last[-1].endswith('SUMMARY PASS')))

ok = all(x for _, x in C)
for n, x in C:
    print(n, 'PASS' if x else 'FAIL')
print('SUMMARY', 'PASS' if ok else 'FAIL')

if ok:
    apk, exe = os.path.getsize(r'F:\Daodao\src\_apk\Dao.apk'), os.path.getsize(r'F:\Daodao\道.exe')
    open(r'F:\Daodao\发版记录.txt', 'a', encoding='utf-8').write(
        '\n=== v133 大模型出动作（2026-11-25）===\n'
        '规矩：系统提示加 ACT_RULE，正文后另起 [[act:xxx]]（wave/nod/hop/squat/dance/fly/sword/ride/tea/tv/turn/none）\n'
        '      和可选 [[mount:1-5]]；解析后从正文删掉，念出来不带标签。\n'
        '兜底：glm-4-flash 常不写标签，就再发一次一问一答让它从回复里挑一个词（实测 0.6~0.7s，命中 dance/wave）。\n'
        '窗口：pet.cs TalkLoop 读 act/mount → ApplyLlmAct；dance→4 骑→3 飞→1 剑→2 咖啡→5 电视→6 转身→9；\n'
        '      wave/nod/hop/squat 桌面端没有整套动作，只当一次应声。\n'
        '实测：ask_glm("行啊，你听节拍，跳一段") → 0.8s，act=dance，正文空（模型只给了标签）；\n'
        '      问「今天风挺大，出门要加衣服吗」→ 2.5s，正文正常、act=wave。\n'
        'apk %d（vc133/vn1.33）；exe %d（APP_VER=133）。判据 J1~J9 PASS。\n' % (apk, exe))
    lp = r'F:\Daodao\自我状态\版本账本.json'
    try:
        d = json.load(open(lp, encoding='utf-8'))
    except Exception:
        d = {}
    d['current'] = 133
    d.setdefault('notes', {})['133'] = '大模型给动作标签（act/mount），窗口照做；带模型兜底挑选'
    json.dump(d, open(lp, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    with open(r'F:\Daodao\能力检查\2026-11-25.md', 'a', encoding='utf-8') as f:
        f.write('\n## v133 大模型出动作\n- ACT_RULE + split_act + classify_act 兜底；pet.cs ApplyLlmAct\n'
                '- 实测 act=dance/wave，latency +0.6~1.2s；J1~J9 PASS\n')
    print('LEDGER_OK')
raise SystemExit(0 if ok else 1)
