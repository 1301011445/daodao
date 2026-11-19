# -*- coding: utf-8 -*-
"""回忆台账（2026-11-19 立）：道每次"被问上次/以前"，把命中与否记下来，
分数只由 tools\\能力激励.py 按这份台账算，不手工改分。

用法：
  python 回忆.py ask "上次那首歌多少秒" "命中" "曲库\\母带.wav" "母带 90 秒，不合 170-200 口径"
  python 回忆.py ask "她喜欢什么题材" "部分" "memory" "只记得故乡，语气偏好说不清"
  python 回忆.py stat
结果取值：命中 / 部分 / 未命中
去重：同一问句 + 同一来源，24 小时内只记一条（防重复刷分）
"""
import datetime
import json
import os
import sys

ROOT = r'F:\Daodao'
BOOK = os.path.join(ROOT, '自我状态', '回忆台账.json')


def load():
    if os.path.exists(BOOK):
        with open(BOOK, encoding='utf-8-sig') as f:
            return json.load(f)
    return {'版本': 1,
            '说明': '回忆能力的证据台账：每次被问"上次/以前"记一条，分数只由能力激励.py 算',
            '记录': []}


def save(obj):
    tmp = BOOK + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    os.replace(tmp, BOOK)


def ask(q, result, src, detail=''):
    obj = load()
    now = datetime.datetime.now()
    for r in obj.get('记录', []):
        if r.get('问句') == q and r.get('来源') == src:
            try:
                if (now - datetime.datetime.strptime(r.get('时间', ''), '%Y-%m-%d %H:%M')).total_seconds() < 86400:
                    print('SKIP|同一问句+来源 24 小时内已记，不重复计分')
                    return
            except Exception:
                pass
    obj['记录'].append({'时间': now.strftime('%Y-%m-%d %H:%M'),
                        '日期': now.date().isoformat(),
                        '问句': q, '结果': result, '来源': src, '明细': detail})
    save(obj)
    print('OK|记下 1 条｜结果=%s｜来源=%s' % (result, src))


def stat():
    obj = load()
    recs = obj.get('记录', [])
    today = datetime.date.today()
    h7 = 0
    for r in recs:
        try:
            if r.get('结果') == '命中' and (today - datetime.date.fromisoformat(r.get('日期', ''))).days <= 7:
                h7 += 1
        except Exception:
            pass
    hit = len([r for r in recs if r.get('结果') == '命中'])
    print('RECALL|总%d|命中%d|近7天命中%d|未命中%d' % (
        len(recs), hit, h7, len([r for r in recs if r.get('结果') == '未命中'])))


if __name__ == '__main__':
    if not sys.argv[1:]:
        stat()
    elif sys.argv[1] == 'stat':
        stat()
    elif sys.argv[1] == 'ask':
        ask(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5] if len(sys.argv) > 5 else '')
    else:
        print('用法：回忆.py ask "问句" 命中|部分|未命中 "来源" "明细"  /  回忆.py stat')
