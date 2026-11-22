# -*- coding: utf-8 -*-
"""常驻程序版本检查 + 升版工具

用法：
  python 程序版本检查.py                     # 检查（缺版本头=FAIL，改了没升版=WARN，超 30 天没动=提醒优化）
  python 程序版本检查.py --bump 愉悦值检查.py --note "改了什么"   # 升一版并写进记录

判据：
  P1 每个常驻程序都有「# 程序版本：vX.Y | 日期 | 改动」头
  P2 文件头的版本与 程序版本记录.json 一致
  P3 文件改过的日期不得晚于记录日期（改了不升版 → WARN）
  P4 超过 30 天没动过的程序 → 列入"该轮到优化"（提醒，不 FAIL）
"""
import io, os, sys, json, re, datetime, argparse

ROOT = os.path.dirname(os.path.abspath(__file__))
JSONP = os.path.join(ROOT, '程序版本记录.json')
HDR = re.compile(r'^# 程序版本：v(\d+)\.(\d+) \| (\d{4}-\d{2}-\d{2}) \| (.*)$')


def load():
    return json.load(io.open(JSONP, encoding='utf-8'))


def save(d):
    io.open(JSONP, 'w', encoding='utf-8').write(json.dumps(d, ensure_ascii=False, indent=1))


def read_text(p):
    return io.open(p, encoding='utf-8-sig', errors='replace').read()


def bump(name, note):
    d = load()
    for item in d['程序']:
        if item['名称'] != name:
            continue
        path = item['路径']
        text = read_text(path)
        m = None
        lines = text.split('\n')
        for i, l in enumerate(lines):
            mm = HDR.match(l.strip())
            if mm:
                m, idx = mm, i
                break
        old = 'v%s.%s' % (m.group(1), m.group(2)) if m else 'v0.0'
        major, minor = (int(m.group(1)), int(m.group(2)) + 1) if m else (0, 1)
        newver = 'v%d.%d' % (major, minor)
        newline = '# 程序版本：%s | %s | %s' % (newver, datetime.date.today().isoformat(), note)
        if m:
            lines[idx] = newline
        else:
            lines.insert(0, newline)
        io.open(path, 'w', encoding='utf-8' if path.lower().endswith('.py') else 'utf-8-sig').write('\n'.join(lines))
        item.update({'版本': newver, '日期': datetime.date.today().isoformat(), '改动': note})
        save(d)
        print('BUMP %s：%s -> %s | %s' % (name, old, newver, note))
        return 0
    print('没找到这个程序：', name)
    return 2


def check():
    d = load()
    today = datetime.date.today()
    fail, warn, remind = [], [], []
    for item in d['程序']:
        path = item['路径']
        if not os.path.exists(path):
            fail.append((item['名称'], '文件不存在'))
            continue
        text = read_text(path)
        m = None
        for l in text.split('\n')[:6]:
            mm = HDR.match(l.strip())
            if mm:
                m = mm
                break
        if not m:
            fail.append((item['名称'], '缺版本头'))
            continue
        hver = 'v%s.%s' % (m.group(1), m.group(2))
        if hver != item['版本']:
            fail.append((item['名称'], '头版本 %s ≠ 记录 %s' % (hver, item['版本'])))
        mdate = datetime.date.fromtimestamp(os.path.getmtime(path))
        rec_date = datetime.date.fromisoformat(item['日期'])
        if mdate > rec_date:
            warn.append((item['名称'], '文件改于 %s，记录停在 %s（改了没升版）' % (mdate, rec_date)))
        idle = (today - mdate).days
        if idle >= 30:
            remind.append((item['名称'], '已 %d 天没动，该轮到优化' % idle))

    print('【程序版本检查】共 %d 个常驻程序' % len(d['程序']))
    for n, why in fail:
        print('  FAIL %-16s %s' % (n, why))
    for n, why in warn:
        print('  WARN %-16s %s' % (n, why))
    for n, why in remind:
        print('  REMIND %-14s %s' % (n, why))
    if not (fail or warn or remind):
        print('  全部带版本头、记录同步、近 30 天有改动')
    print('PROGVER|n=%d|缺头或错版=%d|未升版=%d|待优化轮换=%d|%s'
          % (len(d['程序']), len(fail), len(warn), len(remind), 'PASS' if not fail and not warn else 'FAIL'))
    return 0 if not fail and not warn else 1


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--bump')
    ap.add_argument('--note', default='')
    a = ap.parse_args()
    sys.exit(bump(a.bump, a.note) if a.bump else check())
