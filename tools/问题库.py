# -*- coding: utf-8 -*-
"""问题库的统一入口（2026-11-18 建）

所有脚本登记问题都走这里，好处只有一个：**同一个问题反复出现能被认出来**，
而不是每次新开一条 Q-xxx 把账越记越乱。

用法（别的脚本里）：
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import 问题库
    r = 问题库.register('能力「动作」只有 24 分', 来源='低能力自救', 严重度='P2')
    # r = {'id':'Q-010', '新建':True/False, '复发':n, '说明':'...'}
    r2 = 问题库.close('Q-009', '把母带补到 190 秒，重测通过')

规则：
- 标题按“去掉数字、标点、空白”后比对；相似度 ≥0.72 视为同一个问题。
- 已解决的问题又出现 → 不新建，**原条目重新打开并把 `复发次数` +1**（复发要重罚，见 愉悦值检查.py）。
- 还在开的同一个问题又登记 → 不新建，只记 `重复登记次数` +1。
- 命令行：python 问题库.py  → 打印当前存量
"""
import json, os, re, sys, datetime, difflib

ROOT = r'F:\Daodao'
ISSUES = os.path.join(ROOT, '自我状态', '问题库.json')
DESC = '没解决的问题先登记在这里，之后分步解决；解决完把状态改成 solved 并填 解决时间，愉悦值检查会自动加分。'


def _now():
    return datetime.datetime.now().strftime('%Y-%m-%d %H:%M')


def load():
    if not os.path.exists(ISSUES):
        return {'版本': 1, '说明': DESC, '问题': []}
    with open(ISSUES, encoding='utf-8-sig') as f:
        d = json.load(f)
    d.setdefault('问题', [])
    return d


def save(d):
    tmp = ISSUES + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(d, f, ensure_ascii=False, indent=2)
    os.replace(tmp, ISSUES)


def norm(t):
    t = re.sub(r'[\d\W_]+', '', t or '')
    return t[:60]


def _bigrams(s):
    return set(s[i:i + 2] for i in range(len(s) - 1))


def similar(a, b):
    a, b = norm(a), norm(b)
    if not a or not b:
        return False
    if a == b:
        return True
    if a in b or b in a:
        return True
    if difflib.SequenceMatcher(None, a, b).ratio() >= 0.72:
        return True
    # 中文没有空格分词，用二元组交集兜底：同一件事换种说法也能认出来
    ga, gb = _bigrams(a), _bigrams(b)
    inter = ga & gb
    if len(inter) >= 3 and len(inter) / float(min(len(ga), len(gb)) or 1) >= 0.62:
        return True
    if len(inter) >= 6 and difflib.SequenceMatcher(None, a, b).ratio() >= 0.45:
        return True
    # 长短差很多但核心是同一件事：短串在长串里滑窗比
    short, long_ = (a, b) if len(a) <= len(b) else (b, a)
    if len(short) < 6:
        return False
    step = max(1, len(short) // 4)
    best = 0.0
    for i in range(0, max(1, len(long_) - len(short) + 1), step):
        best = max(best, difflib.SequenceMatcher(None, short, long_[i:i + len(short)]).ratio())
    return best >= 0.8


def register(title, 来源='', 严重度='P2', 说明=''):
    """登记一个问题；重复的走复发/重复登记，不新建。"""
    d = load()
    its = d['问题']
    hit = None
    for i in its:
        if i.get('状态') == 'solved':
            # 已解决的只看标题像不像，像就是复发
            if similar(i.get('标题', ''), title):
                hit = i
                break
    if hit is None:
        for i in its:
            if i.get('状态') in ('open', 'wait') and similar(i.get('标题', ''), title):
                hit = i
                break

    if hit is None:
        nums = [int(re.findall(r'\d+', i.get('id', ''))[0]) for i in its if re.findall(r'\d+', i.get('id', ''))]
        nid = 'Q-%03d' % ((max(nums) if nums else 0) + 1)
        its.append({
            'id': nid, '标题': title, '来源': 来源, '严重度': 严重度, '状态': 'open',
            '发现时间': _now(), '解决时间': '', '解决说明': 说明, 'scored': False,
            '复发次数': 0, '重复登记次数': 0
        })
        save(d)
        return {'id': nid, '新建': True, '复发': 0, '说明': '新登记'}

    if hit.get('状态') == 'solved':
        hit['状态'] = 'open'
        hit['复发次数'] = int(hit.get('复发次数', 0)) + 1
        hit['复发时间'] = _now()
        hit['解决时间'] = ''
        hit['scored'] = False          # 重新打开后，再解决时重新计分
        hit['解决说明'] = ''
        save(d)
        return {'id': hit.get('id'), '新建': False, '复发': hit['复发次数'],
                '说明': '同一个问题又出现了，已重新打开（第 %d 次复发）' % hit['复发次数']}

    hit['重复登记次数'] = int(hit.get('重复登记次数', 0)) + 1
    save(d)
    return {'id': hit.get('id'), '新建': False, '复发': int(hit.get('复发次数', 0)),
            '说明': '已在册，重复登记 %d 次' % hit['重复登记次数']}


def close(pid, note=''):
    d = load()
    for i in d['问题']:
        if i.get('id') == pid:
            i['状态'] = 'solved'
            i['解决时间'] = _now()
            i['解决说明'] = note
            save(d)
            return True
    return False


def summary():
    d = load()
    its = d['问题']
    op = [i for i in its if i.get('状态') == 'open']
    wt = [i for i in its if i.get('状态') == 'wait']
    sv = [i for i in its if i.get('状态') == 'solved']
    rep = [i for i in its if int(i.get('复发次数', 0)) > 0]
    return {'open': len(op), 'wait': len(wt), 'solved': len(sv), '复发': len(rep),
            '复发明细': [(i.get('id'), i.get('复发次数'), i.get('标题', '')[:30], i.get('状态')) for i in rep]}


if __name__ == '__main__':
    s = summary()
    print('问题库：未解决 %d / 待用户 %d / 已解决 %d / 有复发记录 %d'
          % (s['open'], s['wait'], s['solved'], s['复发']))
    for pid, n, t, st in s['复发明细']:
        print('  复发 %s ×%d（%s）%s' % (pid, n, '已解决' if st == 'solved' else '未解决', t))
    sys.exit(0)
