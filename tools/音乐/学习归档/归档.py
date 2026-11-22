# -*- coding: utf-8 -*-
# 程序版本：v0.1 | 2026-11-22 | 基线建档（此前无版本头）
"""学习归档：把散在各文件夹的「第 N 类」学习文档、脚本、判据收成一份索引，
并自检缺口（来源少于 2 条、没有脚本、没写"没做的"）。每天定时跑一次。
"""
import json, os, re, sys, time

def _find_root(start):
    """从脚本所在目录往上找项目根：认「道.exe」或任意 乐谱学习_第N类*.md。
    云主机时代的 ROOT=上一级目录；同步到电脑后脚本落在 tools\音乐\学习归档\，
    照旧取上一级会指到 tools\音乐 而扫不到文档，所以改成向上探测。"""
    d = start
    for _ in range(5):
        if os.path.exists(os.path.join(d, '道.exe')):
            return d
        try:
            if any(f.startswith('乐谱学习_第') and f.endswith('.md') for f in os.listdir(d)):
                return d
        except OSError:
            pass
        d = os.path.dirname(d)
    return os.path.dirname(os.path.dirname(start))

ROOT = _find_root(os.path.dirname(os.path.abspath(__file__)))   # 项目根
OUT = os.path.join(ROOT, '学习归档')
os.makedirs(OUT, exist_ok=True)

DOC_PAT = re.compile(r'乐谱学习_第(\d+)类.*\.md$')
URL_PAT = re.compile(r'https?://[^\s)>\]]+')

def scan():
    items = []
    for dirpath, _, files in os.walk(ROOT):
        if '学习归档' in dirpath or 'out' in dirpath.split(os.sep):
            continue
        for f in files:
            m = DOC_PAT.match(f)
            if not m:
                continue
            p = os.path.join(dirpath, f)
            txt = open(p, encoding='utf-8').read()
            title = (txt.splitlines()[0] if txt.splitlines() else f).lstrip('# ').strip()
            date = ''
            dm = re.search(r'学习日期：([0-9-]+)', txt)
            if dm:
                date = dm.group(1)
            urls = sorted(set(URL_PAT.findall(txt)))
            rules = 0
            for line in txt.splitlines():
                if line.startswith('|') and '---' not in line and '| 类 |' not in line:
                    rules += 1
            has_gap = ('没做的' in txt) or ('还没做' in txt)
            scripts = [x for x in os.listdir(dirpath) if x.endswith('.py')]
            size = os.path.getsize(p)
            stamp = time.strftime('%Y-%m-%d %H:%M', time.localtime(os.path.getmtime(p)))
            items.append(dict(id=int(m.group(1)), title=title, path=p, date=date,
                              sources=len(urls), urls=urls, rules=rules,
                              has_gap=has_gap, scripts=scripts,
                              bytes=size, mtime=stamp))
    return sorted(items, key=lambda x: x['id'])

def main():
    items = scan()
    problems = []
    for it in items:
        if it['sources'] < 2:
            problems.append('第%d类 来源只有 %d 条（要 ≥2）' % (it['id'], it['sources']))
        if not it['has_gap']:
            problems.append('第%d类 没写「没做的」段落（不写就等于假装做完）' % it['id'])
        if it['rules'] == 0:
            problems.append('第%d类 没有判据表（学完不能只剩感想）' % it['id'])
        if not it['scripts']:
            problems.append('第%d类 所在目录没有脚本（只抄笔记不算学过）' % it['id'])
    json.dump(dict(generated=time.strftime('%Y-%m-%d %H:%M:%S'), count=len(items),
                   items=items, problems=problems),
              open(os.path.join(OUT, '归档清单.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)

    md = ['# 乐谱学习总纲（自动生成，勿手改）', '',
          '> 生成时间：%s　共生 %d 类' % (time.strftime('%Y-%m-%d %H:%M'), len(items)), '',
          '| 类 | 标题 | 日期 | 来源数 | 判据条数 | 脚本 | 文档 |',
          '|---|---|---|---|---|---|---|']
    for it in items:
        md.append('| %d | %s | %s | %d | %d | %s | %s |'
                  % (it['id'], it['title'][:40], it['date'], it['sources'], it['rules'],
                     ('、'.join(it['scripts'])[:50] or '—'), os.path.basename(it['path'])))
    md += ['', '## 自检缺口（%d 处）' % len(problems)]
    md += ['- ' + p for p in problems] or ['- 无']
    md += ['', '## 来源清单（按类）']
    for it in items:
        md.append('**第 %d 类**' % it['id'])
        md += ['- ' + u for u in it['urls']]
    open(os.path.join(OUT, '学习总纲.md'), 'w', encoding='utf-8').write('\n'.join(md) + '\n')

    print('归档 %d 类，缺口 %d 处' % (len(items), len(problems)))
    for it in items:
        print('  第%-2d类 %-28s 来源%d 判据%d 脚本%d' % (it['id'], it['title'][:28], it['sources'],
                                                   it['rules'], len(it['scripts'])))
    for p in problems:
        print('  ! ' + p)

if __name__ == '__main__':
    main()
