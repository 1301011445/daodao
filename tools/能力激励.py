# -*- coding: utf-8 -*-
# 程序版本：v0.1 | 2026-11-22 | 基线建档（此前无版本头）
"""各项能力的激励/惩罚（道 自查用，2026-11-18 立）

一句话：每项能力都有分、有证据、有奖惩。分数只按“能重新算一遍的证据”走，
涨了给奖励（愉悦值 +1），跌了记惩罚（愉悦值 -1），跌到 30 以下进“补短板”状态，
连着一周没进展就按停滞扣分。每天只结算一次，多跑不会重复加减。

覆盖 10 项：动作、说话、创作、协调、学习、反馈、改正、反应、思考、反思
（前 7 项跟 `能力台账.txt` 同一个口径，新增协调/反馈/改正三项单独记账）

输出（给 inspect_dao.py 抓）：
  【能力激励】
    动作 50 → 51（+1 奖励）  证据：表情48帧/姿态20/走路16
    ...
    本次合计：愉悦值 +2（上限 ±5/天）
  CAP_STATE=OK|WARN
"""
import json, os, re, sys, time, wave, urllib.request, datetime

ROOT = r'F:\Daodao'
DIR = os.path.join(ROOT, '自我状态')
CAP = os.path.join(DIR, '能力激励.json')
JOY = os.path.join(DIR, '愉悦值.json')
ISSUES = os.path.join(DIR, '问题库.json')
BUNDLE = os.path.join(ROOT, 'src', '桌面分身', '_bundle')

CAPS = ['动作', '说话', '创作', '协调', '学习', '反馈', '改正', '反应', '思考', '反思', '回忆']

MAX_JOY_PER_DAY = 5   # 能力激励一天最多给愉悦值 ±5
LOW_LINE = 30         # 低于这条线进“补短板”
GOOD_LINE = 80        # 高于这条线进“奖励档”


def clamp(v, lo=0, hi=100):
    return max(lo, min(hi, int(v)))


def read_text(p, enc='utf-8-sig'):
    try:
        with open(p, encoding=enc) as f:
            return f.read()
    except Exception:
        return ''


def count(pattern, folder):
    try:
        return sum(1 for f in os.listdir(folder) if re.match(pattern, f))
    except Exception:
        return 0


def count_files(folder, suffix='.wav', name_re=None):
    try:
        fs = [f for f in os.listdir(folder) if f.lower().endswith(suffix)]
        if name_re:
            fs = [f for f in fs if re.search(name_re, f)]
        return len(fs)
    except Exception:
        return 0


def versions_agree():
    pet = read_text(os.path.join(ROOT, 'src', '桌面分身', 'pet.cs'))
    man = read_text(os.path.join(ROOT, 'src', '_apk', 'AndroidManifest.xml'))
    html = read_text(os.path.join(ROOT, 'src', '_apk', 'assets', 'dao.html'))
    a = re.search(r'APP_VER = (\d+)', pet)
    b = re.search(r'versionCode="(\d+)"', man)
    c = re.search(r"HTML_VER = '(\d+)'", html)
    if not (a and b and c):
        return False, '版本号读不全'
    return (a.group(1) == b.group(1) == c.group(1)), 'v%s/v%s/v%s' % (a.group(1), b.group(1), c.group(1))


def reports_info():
    d = os.path.join(ROOT, '巡检报告')
    files = [f for f in os.listdir(d) if f.startswith('巡检_') and f.endswith('.txt')] if os.path.isdir(d) else []
    recent = 0
    has_table = False
    cutoff = datetime.datetime.now() - datetime.timedelta(days=7)
    for f in files:
        t = datetime.datetime.fromtimestamp(os.path.getmtime(os.path.join(d, f)))
        if t > cutoff:
            recent += 1
    if files:
        last = max(files, key=lambda f: os.path.getmtime(os.path.join(d, f)))
        has_table = '【各项程序】' in read_text(os.path.join(d, last))
    return len(files), recent, has_table


def ping_ms():
    try:
        t0 = time.time()
        r = urllib.request.urlopen('http://127.0.0.1:8848/ping', timeout=4)
        r.read()
        return int((time.time() - t0) * 1000)
    except Exception:
        return -1


def _mtime_days(p):
    try:
        return (datetime.datetime.now() - datetime.datetime.fromtimestamp(os.path.getmtime(p))).days
    except Exception:
        return 9999


def master_seconds():
    """曲库最长母带时长（秒）；读不出来记 0"""
    d = os.path.join(ROOT, '曲库')
    best = 0.0
    try:
        for f in os.listdir(d):
            if not f.lower().endswith('.wav'):
                continue
            try:
                with wave.open(os.path.join(d, f), 'rb') as w:
                    best = max(best, w.getnframes() / float(w.getframerate() or 1))
            except Exception:
                pass
    except Exception:
        pass
    return round(best, 1)


def corpus_lines():
    """台词语料条数。以前只扫素材包 _bundle 里那 3 行占位记录，
    而程序运行时真正读写的是根目录的「我说的话.txt」（道自己攒的台词），
    于是「说话」这一项一直按 3/60 算分，白白少 20 多分。改成根目录优先。"""
    for base in (ROOT, BUNDLE):
        for name in ('我说的话.txt', '语料.txt', '台词.txt'):
            p = os.path.join(base, name)
            if os.path.exists(p):
                n = len([l for l in read_text(p).splitlines() if l.strip()])
                if n:
                    return n
    return 0


def report_days(days=14):
    """近 N 天里有几天真跑过巡检（不是跑了几份）"""
    d = os.path.join(ROOT, '巡检报告')
    if not os.path.isdir(d):
        return 0
    ds = set()
    for f in os.listdir(d):
        if not (f.startswith('巡检_') and f.endswith('.txt')):
            continue
        t = datetime.datetime.fromtimestamp(os.path.getmtime(os.path.join(d, f)))
        if (datetime.datetime.now() - t).days <= days:
            ds.add(t.strftime('%Y-%m-%d'))
    return len(ds)


def fresh_study(days=7):
    try:
        for f in os.listdir(ROOT):
            if re.match(r'^乐谱学习_第\d+类', f):
                if _mtime_days(os.path.join(ROOT, f)) <= days:
                    return True
    except Exception:
        pass
    return False


def issue_stats():
    """问题库的体检：解决数、P1、停滞、复发率、根因说明率"""
    st = {'solved': 0, 'p1': 0, 'stale': 0, 'total': 0, 'recur': 0, 'root_ratio': 0.0}
    try:
        its = json.load(open(ISSUES, encoding='utf-8-sig')).get('问题', [])
    except Exception:
        return st
    st['total'] = len(its)
    good = 0
    for i in its:
        stt = i.get('状态')
        if stt == 'solved':
            st['solved'] += 1
            note = i.get('解决说明', '') or ''
            if any(w in note for w in ('根因', '因为', '原因是', '为什么', '漏了', '误')):
                good += 1
        elif stt == 'open' and i.get('严重度') in ('P0', 'P1'):
            st['p1'] += 1
        if stt in ('open', 'wait'):
            try:
                days = (datetime.datetime.now() - datetime.datetime.strptime(i.get('发现时间', '')[:16], '%Y-%m-%d %H:%M')).days
                if days > 14:
                    st['stale'] += 1
            except Exception:
                pass
        st['recur'] += int(i.get('复发次数', 0))
    st['root_ratio'] = (good / float(st['solved'])) if st['solved'] else 0.0
    return st


def joy_stats():
    try:
        j = json.load(open(JOY, encoding='utf-8-sig'))
    except Exception:
        return {'n': 0, 'fresh': False, 'detail_ratio': 0.0, 'score': 50}
    recs = j.get('记录', [])
    fresh = any((datetime.datetime.now() - datetime.datetime.strptime(r.get('时间', '')[:16], '%Y-%m-%d %H:%M')).days <= 7
                for r in recs if r.get('时间'))
    detailed = sum(1 for r in recs if re.search(r'\d', r.get('理由', '') or ''))
    return {'n': len(recs), 'fresh': fresh,
            'detail_ratio': (detailed / float(len(recs))) if recs else 0.0,
            'score': int(j.get('当前愉悦值', 50))}
def lesson_classes():
    """乐谱学习类数（2026-11-19 修）：以前只数根目录，文档落在 tools\\音乐、tools\\表情第10类 里就被漏掉（7 vs 实际9）。
    改成全盘递归 + 按类号去重：同一类只算一次，避免一个类多份文件重复加分。"""
    pat = re.compile(r'乐谱学习_第(\d+)类')
    seen = set()
    for dirpath, _, files in os.walk(ROOT):
        for f in files:
            m = pat.search(f)
            if m and f.endswith('.md'):
                seen.add(int(m.group(1)))
    return len(seen)


def evidence():
    """能力指标 v3（2026-11-18）：每项拆成 2-3 个子项，各按"证据量/覆盖率/新鲜度"打分，全部可重算。
    权重是有意设得比现状高的：能拿满分说明真的做到位了，不是拿数量凑分。"""
    expr = count(r'expr_\d+_\w+\.png$', BUNDLE)
    pose = count(r'pose_\d+_\w+\.png$', BUNDLE)
    walk = count(r'walk8_\d+_\d+\.png$', BUNDLE)
    faces = count(r'face_\d+\.png$', BUNDLE)
    frames = expr + pose + walk

    voices = len([l for l in read_text(os.path.join(BUNDLE, 'voices.txt')).splitlines() if l.strip()])
    names = len([l for l in read_text(os.path.join(BUNDLE, 'names.txt')).splitlines() if l.strip()])
    corpus = corpus_lines()

    wav = count_files(os.path.join(ROOT, '曲库'), '.wav')
    msec = master_seconds()
    qualified = wav if 170 <= msec <= 200 else 0        # 合格的成品：170-200 秒
    words = count_files(ROOT, '.md', r'_词\.md$')
    lessons = lesson_classes()
    archive = os.path.exists(os.path.join(ROOT, '学习归档', '归档清单.json'))

    n_rep, n_recent, has_table = reports_info()
    days14 = report_days(14)
    iss = issue_stats()
    agree, vtxt = versions_agree()
    ms = ping_ms()
    js = joy_stats()
    opt_fresh = _mtime_days(os.path.join(DIR, '每周优化清单.md')) <= 7
    docs = count_files(DIR, '.md') + count_files(ROOT, '.md', r'^(学习总纲|音乐判据总表|词曲协同规则|音乐制度增补).*\.md$')

    def pct(x):
        return max(0.0, min(1.0, x))

    ev = {}

    # 动作：帧量 45（目标 134 帧）/ 单形象帧数覆盖 30 / 四类素材齐全 25
    cover = pct((frames / float(faces)) / 6.0) if faces else 0
    complete = 25 if (expr and pose and walk and faces) else 0
    ev['动作'] = (clamp(45 * pct(frames / 134.0) + 30 * cover + complete),
                  '帧量%d/134(45)·覆盖%.0f%%(30)·齐全%d(25)' % (frames, cover * 100, complete))

    # 说话：音色 50（目标 20 条）/ 名字对齐 25 / 台词语料 25（目标 60 行）
    ev['说话'] = (clamp(50 * pct(voices / 20.0) + 25 * (pct(names / float(voices)) if voices else 0) + 25 * pct(corpus / 60.0)),
                  '音色%d/20(50)·名字%d/音色%d(25)·语料%d行/60(25)' % (voices, names, voices, corpus))

    # 创作：合格成品 45（170-200 秒，目标 3 首）/ 半成品 20（有母带但时长不合口径，1 首即满）/ 词本 20（目标 2 份）/ 词曲配对 15（词本对着曲子，1 对即满）
    # 注意：乐理不再算进创作，避免和「学习」一鱼两吃（同一个文件不许给两项能力加分）
    semi = 1 if (wav and not (170 <= msec <= 200)) else 0
    pair = min(words, wav)
    ev['创作'] = (clamp(45 * pct(qualified / 3.0) + 20 * semi + 20 * pct(words / 2.0) + 15 * pct(pair / 1.0)),
                  '合格成品%d首/3(45，母带%.1f秒)·半成品%d(20)·词本%d/2(20)·词曲配对%d(15)' % (qualified, msec, semi, words, pair))

    # 协调：三端版本一致 40 / 近 7 天报告 30 / P1 清零 30
    ev['协调'] = (clamp(40 * (1 if agree else 0) + 30 * pct(n_recent / 3.0) + 30 * (1 if iss['p1'] == 0 else 0)),
                  '版本%s(40)·近7天报告%d/3(30)·P1未修%d(30)' % (vtxt, n_recent, iss['p1']))

    # 学习：类数 40（目标 10 类）/ 归档 20 / 近 7 天有新学 40
    ev['学习'] = (clamp(40 * pct(lessons / 10.0) + 20 * (1 if archive else 0) + 40 * (1 if fresh_study() else 0)),
                  '类数%d/10(40)·归档%s(20)·近7天新学%s(40)' % (lessons, '在' if archive else '缺', '有' if fresh_study() else '无'))

    # 反馈：覆盖天数 50（近 14 天至少 10 天跑过）/ 各项程序表 20 / 问题库新鲜 30
    issue_fresh = _mtime_days(ISSUES) <= 7
    ev['反馈'] = (clamp(50 * pct(days14 / 10.0) + 20 * (1 if has_table else 0) + 30 * (1 if issue_fresh else 0)),
                  '近14天跑过%d/10天(50)·程序表%s(20)·问题库近7天更新%s(30)' % (days14, '有' if has_table else '无', '有' if issue_fresh else '无'))

    # 改正：解决数 45（目标 8 项）/ 复发率 30 / 无停滞 25
    recur_ratio = (iss['recur'] / float(iss['total'])) if iss['total'] else 0
    ev['改正'] = (clamp(45 * pct(iss['solved'] / 8.0) + 30 * (1 - pct(recur_ratio)) + 25 * (1 if iss['stale'] == 0 else 0)),
                  '已解决%d/8(45)·复发率%.0f%%(30)·停滞%d项(25)' % (iss['solved'], recur_ratio * 100, iss['stale']))

    # 反应：接口响应 50（≤50ms 满分，200ms 归零）/ 字段完整 25 / 稳定（近 7 天有报告即算）25
    resp = pct((200 - ms) / 150.0) if ms > 0 else 0
    ev['反应'] = (clamp(50 * resp + 25 * (1 if ms > 0 else 0) + 25 * (1 if n_recent > 0 else 0)),
                  '响应%dms(50)·通%s(25)·近7天在线%s(25)' % (ms, '是' if ms > 0 else '否', '是' if n_recent > 0 else '否'))

    # 思考：制度文档 45（目标 10 份）/ 每周清单新鲜 25 / 解决说明带根因 30
    ev['思考'] = (clamp(45 * pct(docs / 10.0) + 25 * (1 if opt_fresh else 0) + 30 * iss['root_ratio']),
                  '制度%d/10份(45)·优化清单新鲜%s(25)·根因说明%.0f%%(30)' % (docs, '是' if opt_fresh else '否', iss['root_ratio'] * 100))

    # 反思：台账笔数 45（目标 30 笔）/ 近 7 天在记 25 / 记录带数据 30
    ev['反思'] = (clamp(45 * pct(js['n'] / 30.0) + 25 * (1 if js['fresh'] else 0) + 30 * js['detail_ratio']),
                  '台账%d/30笔(45)·近7天记账%s(25)·带数据%.0f%%(30)' % (js['n'], '是' if js['fresh'] else '否', js['detail_ratio'] * 100))

    # 回忆（2026-11-19 加）：可复查索引 40（问题库/愉悦值/版本账本/归档清单 各 10，30 天内更新算在账）
    #                   命中台账 35（近 7 天"命中"≥5 条满分）/ 沉淀条目 25（问题+学习类+版本记录，目标 30 条）
    _books = [os.path.join(DIR, '问题库.json'), JOY,
              os.path.join(DIR, '版本账本.json'),
              os.path.join(ROOT, '学习归档', '归档清单.json')]
    idx = sum(10 for p in _books if os.path.exists(p) and _mtime_days(p) <= 30)
    hits7, n_rec = 0, 0
    try:
        with open(os.path.join(DIR, '回忆台账.json'), encoding='utf-8-sig') as f:
            _rj = json.load(f)
        _recs = _rj.get('记录', [])
        n_rec = len(_recs)
        for _r in _recs:
            try:
                if _r.get('结果') == '命中' and (datetime.date.today() -
                                                 datetime.date.fromisoformat(str(_r.get('日期', '')))).days <= 7:
                    hits7 += 1
            except Exception:
                pass
    except Exception:
        pass
    sunk = iss['total'] + lessons
    try:
        with open(os.path.join(DIR, '版本账本.json'), encoding='utf-8-sig') as f:
            sunk += len(json.load(f).get('记录', []))
    except Exception:
        pass
    ev['回忆'] = (clamp(idx + 35 * pct(hits7 / 5.0) + 25 * pct(sunk / 30.0)),
                  '索引%d/4份(40)·近7天命中%d/5(35)·沉淀%d条/30(25)' % (idx // 10, hits7, sunk))

    return ev


def load_caps():
    if os.path.exists(CAP):
        return json.load(open(CAP, encoding='utf-8-sig'))
    # 头一回：前 7 项沿用 能力台账.txt 的分，协调/反馈/改正 用证据分
    base = 49
    txt = read_text(os.path.join(ROOT, '能力台账.txt')).splitlines()
    try:
        base = int(float(txt[0].split()[0])) if txt else 49
    except Exception:
        base = 49
    obj = {'版本': 1, '说明': '每项能力的分 + 证据 + 奖惩记录；每天只结算一次，不手工改分',
           '能力': {n: {'分': base, '证据': '', '上次更新': '', '奖励': 0, '惩罚': 0} for n in CAPS[:7]},
           '记录': []}
    for n in CAPS[7:]:
        obj['能力'][n] = {'分': base, '证据': '', '上次更新': '', '奖励': 0, '惩罚': 0}
    return obj


def main():
    out = ['【能力激励】']
    warn = []
    ev = evidence()
    obj = load_caps()
    today = datetime.date.today().isoformat()
    caps = obj.setdefault('能力', {})
    for n in CAPS:
        caps.setdefault(n, {'分': 49, '证据': '', '上次更新': '', '奖励': 0, '惩罚': 0})

    last = obj.get('最后结算日', '')
    already = (last == today)

    total_joy = 0
    rows = []
    for n in CAPS:
        cur = int(caps[n].get('分', 49))
        target, why = ev[n]
        gap = target - cur
        if already:
            delta, tag = 0, '今日已结算'
        elif gap >= 5:
            delta = min(3, max(1, gap // 5))
            tag = '奖励'
            caps[n]['奖励'] = caps[n].get('奖励', 0) + 1
        elif gap <= -5:
            # 掉分不天天扣：同一项 7 天内最多罚一次，避免“越查越低”的假崩
            last_pen = caps[n].get('上次惩罚', '')
            try:
                ok_pen = not last_pen or (datetime.date.today() - datetime.date.fromisoformat(last_pen)).days >= 7
            except Exception:
                ok_pen = True
            if ok_pen:
                delta, tag = -1, '惩罚'
                caps[n]['惩罚'] = caps[n].get('惩罚', 0) + 1
                caps[n]['上次惩罚'] = today
            else:
                delta, tag = 0, '惩罚冷却中'
        else:
            delta, tag = 0, '平稳'
        new = clamp(cur + delta)
        caps[n]['分'] = new
        caps[n]['证据'] = why
        if not already:
            # 连续不达标计数：掉分或证据分远远低于当前分，都算一次不达标
            if delta < 0 or gap <= -5:
                caps[n]['连续不达标'] = int(caps[n].get('连续不达标', 0)) + 1
            else:
                caps[n]['连续不达标'] = 0
        if not already:
            caps[n]['上次更新'] = today
            obj.setdefault('记录', []).append({'时间': datetime.datetime.now().strftime('%Y-%m-%d %H:%M'),
                                               '能力': n, '变化': delta, '分值': new, '理由': '%s｜证据：%s' % (tag, why)})
        total_joy += 1 if delta > 0 else (-1 if delta < 0 else 0)

        state = '平稳'
        if new < LOW_LINE:
            state = '补短板'
            warn.append('%s 只有 %d 分（低于 %d），今天必须做一件能验证的小事' % (n, new, LOW_LINE))
        elif new >= GOOD_LINE:
            state = '奖励档'
        rows.append((n, cur, new, delta, tag, why, state))

    # 愉悦值：一天最多 ±MAX_JOY_PER_DAY，只写一条汇总，不让分数乱抖
    joy_delta = max(-MAX_JOY_PER_DAY, min(MAX_JOY_PER_DAY, total_joy))
    if not already and joy_delta != 0:
        try:
            j = json.load(open(JOY, encoding='utf-8-sig'))
            j.setdefault('记录', []).append({
                '时间': datetime.datetime.now().strftime('%Y-%m-%d %H:%M'),
                '类型': '能力激励', '分值': joy_delta,
                '理由': '能力分变动合计（%s）' % '、'.join('%s%+d' % (r[0], r[3]) for r in rows if r[3] != 0)[:60]
            })
            tot = sum(int(r.get('分值', 0)) for r in j.get('记录', []))
            lo, hi = j.get('区间', [0, 100])
            j['当前愉悦值'] = clamp(tot, lo, hi)
            tmp = JOY + '.tmp'
            with open(tmp, 'w', encoding='utf-8') as f:
                json.dump(j, f, ensure_ascii=False, indent=2)
            os.replace(tmp, JOY)
        except Exception as e:
            warn.append('愉悦值写不进去：%s' % e)

    if not already:
        obj['最后结算日'] = today

    # ---------- 低能力自救（2026-11-18 补）：分数太低就自动登记，补上来自动关 ----------
    try:
        low_now = [(n, int(caps[n]['分'])) for n in CAPS
                   if int(caps[n]['分']) < 30
                   or (int(caps[n]['分']) < 45 and int(caps[n].get('连续不达标', 0)) >= 3)]
        its = []
        if os.path.exists(ISSUES):
            its = json.load(open(ISSUES, encoding='utf-8-sig')).get('问题', [])
        nums = [int(re.findall(r'\d+', i.get('id', ''))[0]) for i in its if re.findall(r'\d+', i.get('id', ''))]
        nxt = max(nums) if nums else 0
        for n, score in low_now:
            # 同一个能力用同一个键：分数反复低，沿用原条并累计复发，不新开条
            hit = [i for i in its if i.get('键') == 'ability:%s' % n]
            if hit:
                old = hit[0]
                if old.get('状态') == 'solved':
                    old['状态'] = 'open'
                    old['复发次数'] = int(old.get('复发次数', 0)) + 1
                    old['复发时间'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
                    old['解决时间'] = ''
                    old['scored'] = False
                    out.append('  低能力自救：%s 又掉回 %d 分，%s 重新打开（第 %d 次复发，按复发档扣分）'
                               % (n, score, old.get('id'), old['复发次数']))
                else:
                    out.append('  低能力自救：%s 仍是 %d 分，%s 在册不重复开条' % (n, score, old.get('id')))
                continue
            nxt += 1
            its.append({
                'id': 'Q-%03d' % nxt,
                '标题': '能力「%s」只有 %d 分（低于 45），按制度单点补一格' % (n, score),
                '来源': '低能力自救', '严重度': 'P2', '状态': 'open',
                '发现时间': datetime.datetime.now().strftime('%Y-%m-%d %H:%M'),
                '解决时间': '', '解决说明': '', 'scored': False,
                '键': 'ability:%s' % n, '复发次数': 0, '重复登记次数': 0
            })
            out.append('  低能力自救：已登记 %s（%d 分，%s）' % (n, score, 'Q-%03d' % nxt))
        for i in [x for x in its if x.get('来源') == '低能力自救' and x.get('状态') != 'solved']:
            name = next((n for n in CAPS if n in i.get('标题', '')), None)
            if name and int(caps[name]['分']) >= 50:
                i['状态'] = 'solved'
                i['解决时间'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
                i['解决说明'] = '「%s」回到 %d 分（≥50），自救项自动关闭' % (name, int(caps[name]['分']))
                out.append('  低能力自救：%s 已回到 %d 分，%s 自动关闭' % (name, int(caps[name]['分']), i.get('id')))
        if os.path.exists(ISSUES):
            tmp_i = ISSUES + '.tmp'
            d_i = json.load(open(ISSUES, encoding='utf-8-sig'))
            d_i['问题'] = its
            with open(tmp_i, 'w', encoding='utf-8') as f:
                json.dump(d_i, f, ensure_ascii=False, indent=2)
            os.replace(tmp_i, ISSUES)
    except Exception as e:
        warn.append('低能力自救登记失败：%s' % e)

    tmp = CAP + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    os.replace(tmp, CAP)

    for n, cur, new, delta, tag, why, state in rows:
        arrow = ('%d → %d（%+d %s）' % (cur, new, delta, tag)) if delta else ('%d（%s）' % (new, tag))
        out.append('  %-4s %-22s %-5s 证据：%s' % (n, arrow, state, why))
    if already:
        out.append('  本次未结算（今天已经结过一次，防止重复加减）')
    else:
        out.append('  本次结算：愉悦值 %+d（上限 ±%d/天）' % (joy_delta, MAX_JOY_PER_DAY))
    low = [(n, caps[n]['分']) for n in CAPS if caps[n]['分'] < LOW_LINE]
    if low:
        out.append('  最该补的：' + '、'.join('%s(%d)' % x for x in sorted(low, key=lambda x: x[1])))
    for w in warn:
        out.append('  ! ' + w)
    out.append('  CAP_STATE=' + ('WARN' if warn else 'OK'))
    print('\n'.join(out))
    return 0


if __name__ == '__main__':
    sys.exit(main())
