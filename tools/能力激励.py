# -*- coding: utf-8 -*-
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
import json, os, re, sys, time, urllib.request, datetime

ROOT = r'F:\Daodao'
DIR = os.path.join(ROOT, '自我状态')
CAP = os.path.join(DIR, '能力激励.json')
JOY = os.path.join(DIR, '愉悦值.json')
ISSUES = os.path.join(DIR, '问题库.json')
BUNDLE = os.path.join(ROOT, 'src', '桌面分身', '_bundle')

CAPS = ['动作', '说话', '创作', '协调', '学习', '反馈', '改正', '反应', '思考', '反思']

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


def evidence():
    """每项能力的证据分（0-100）与证据摘要。全部可重算，不写主观感受。"""
    expr = count(r'expr_\d+_\w+\.png$', BUNDLE)
    pose = count(r'pose_\d+_\w+\.png$', BUNDLE)
    walk = count(r'walk8_\d+_\d+\.png$', BUNDLE)
    faces = count(r'face_\d+\.png$', BUNDLE)

    voices = len([l for l in read_text(os.path.join(BUNDLE, 'voices.txt')).splitlines() if l.strip()])
    names = len([l for l in read_text(os.path.join(BUNDLE, 'names.txt')).splitlines() if l.strip()])

    wav = count_files(os.path.join(ROOT, '曲库'), '.wav')
    words = count_files(ROOT, '.md', r'_词\.md$')
    lessons = count_files(ROOT, '.md', r'^乐谱学习_第\d+类')
    archive = os.path.exists(os.path.join(ROOT, '学习归档', '归档清单.json'))

    n_rep, n_recent, has_table = reports_info()
    try:
        solved = sum(1 for i in json.load(open(ISSUES, encoding='utf-8-sig')).get('问题', [])
                     if i.get('状态') == 'solved')
        open_p1 = sum(1 for i in json.load(open(ISSUES, encoding='utf-8-sig')).get('问题', [])
                      if i.get('状态') == 'open' and i.get('严重度') in ('P0', 'P1'))
    except Exception:
        solved, open_p1 = 0, 0

    agree, vtxt = versions_agree()
    ms = ping_ms()

    docs = count_files(DIR, '.md') + count_files(ROOT, '.md', r'^(学习总纲|音乐判据总表|词曲协同规则|音乐制度增补).*\.md$')
    joy = None
    try:
        j = json.load(open(JOY, encoding='utf-8-sig'))
        joy = (j.get('当前愉悦值'), len(j.get('记录', [])))
    except Exception:
        pass

    ev = {}
    ev['动作'] = (clamp((expr + pose + walk) * 0.6), '表情%d帧/姿态%d/走路%d（形象%d个）' % (expr, pose, walk, faces))
    ev['说话'] = (clamp(voices * 4), '音色表%d条/名字%d条' % (voices, names))
    ev['创作'] = (clamp(wav * 15 + words * 15 + (10 if lessons >= 5 else 0)),
                  '曲库%d首/词本%d份/学习%d类' % (wav, words, lessons))
    ev['协调'] = (clamp(40 * (1 if agree else 0) + min(30, n_recent * 10) + (20 if open_p1 == 0 else 0)),
                  '两端%s/近7天报告%d份/P1未修%d' % (vtxt, n_recent, open_p1))
    ev['学习'] = (clamp(lessons * 8 + (20 if archive else 0)),
                  '学习文档%d类/归档清单%s' % (lessons, '在' if archive else '缺'))
    ev['反馈'] = (clamp(min(60, n_rep * 3) + (20 if has_table else 0) + 10),
                  '巡检报告%d份/各项程序表%s' % (n_rep, '有' if has_table else '无'))
    ev['改正'] = (clamp(solved * 12 + 10), '问题库已解决%d项/P1未修%d项' % (solved, open_p1))
    ev['反应'] = (clamp(100 - ms / 5), '自检口 %d ms' % ms) if ms >= 0 else (0, '自检口不通')
    ev['思考'] = (clamp(docs * 15), '制度/总纲类文档%d份' % docs)
    if joy:
        ev['反思'] = (clamp(joy[1] * 2 + 20), '愉悦值台账%d笔（当前%d分）' % (joy[1], joy[0] if isinstance(joy[0], int) else 50))
    else:
        ev['反思'] = (20, '愉悦值台账读不到')
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
            hit = [i for i in its if i.get('来源') == '低能力自救'
                   and n in i.get('标题', '') and i.get('状态') != 'solved']
            if hit:
                continue
            nxt += 1
            its.append({
                'id': 'Q-%03d' % nxt,
                '标题': '能力「%s」只有 %d 分（低于 45），按制度单点补一格' % (n, score),
                '来源': '低能力自救', '严重度': 'P2', '状态': 'open',
                '发现时间': datetime.datetime.now().strftime('%Y-%m-%d %H:%M'),
                '解决时间': '', '解决说明': '', 'scored': False
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
