# -*- coding: utf-8 -*-
"""愉悦值与问题库的自动检查 / 结算（道 自省用）

做三件事：
1) 台账不存在就按制度初始化（愉悦值 50 起点、空问题库）；
2) 结算：问题库里状态=已解决 但还没加过分的，按严重度把分值记入愉悦值台账（幂等，靠 scored 标记，不重复加分）；
   同一问题超 14 天没动（状态仍是 open/wait），记“停滞”，按制度扣分（每天最多扣 1，单个问题最多扣 5）；
3) 体检：两份 JSON 能不能读、字段齐不齐、愉悦值是否越界、是否有条目缺字段、问题库多久没更新。

输出约定（给 inspect_dao.py 抓取）：
  【愉悦与问题】
    愉悦值：59（+3 今天）  区间 0-100
    问题库：未解决 4 / 待用户 1 / 已解决 3   停滞 0
    ...
  JOY_STATE=OK|WARN
最后一行固定写 JOY_STATE，WARN 表示有需要人看的地方（不阻断巡检，只提醒）。
"""
import json, os, sys, re, datetime

ROOT = r'F:\Daodao'
DIR = os.path.join(ROOT, '自我状态')
JOY = os.path.join(DIR, '愉悦值.json')
ISSUES = os.path.join(DIR, '问题库.json')

# 严重度 → 解决后加的分（制度见 自我状态\愉悦值制度.md）
REWARD = {'P0': 6, 'P1': 4, 'P2': 2, 'P3': 1}
STALE_DAYS = 14

SEED_JOY = {
    "版本": 1,
    "区间": [0, 100],
    "当前愉悦值": 59,
    "说明": "0=很糟，50=中性，100=最好。每次变动都要有理由、有时间和分值，不能凭空加。",
    "记录": [
        {"时间": "2026-11-18 07:20", "类型": "起步", "分值": 50, "理由": "制度建立，从 50 中性起步"},
        {"时间": "2026-11-18 07:34", "类型": "解决问题", "分值": 2, "理由": "解决 P2：exe 站着不动也 30fps 重绘，空闲 CPU 6.6%→2.5% 单核", "关联问题": "Q-001"},
        {"时间": "2026-11-18 07:50", "类型": "解决问题", "分值": 4, "理由": "解决 P1：下载页内嵌包体超 20MiB 上限，改成 CDN 直链，页面 9.4MB→26KB", "关联问题": "Q-002"},
        {"时间": "2026-11-18 07:55", "类型": "解决问题", "分值": 2, "理由": "解决 P2：两端版本停在 54/50 不一致，统一升到 v55", "关联问题": "Q-003"},
        {"时间": "2026-11-18 07:38", "类型": "巡检通过", "分值": 1, "理由": "当日全量巡检 PASS（未解决 0 项、已修复 3 项）"}
    ]
}

SEED_ISSUES = {
    "版本": 1,
    "说明": "没解决的问题先登记在这里，之后分步解决；解决完把状态改成 solved 并填 解决时间，愉悦值检查会自动加分。",
    "问题": [
        {"id": "Q-001", "标题": "exe 站着不动也按 30fps 全量重绘，空闲白烧 CPU", "来源": "用户反馈/自检",
         "严重度": "P2", "状态": "solved", "发现时间": "2026-11-18 07:10", "解决时间": "2026-11-18 07:34",
         "解决说明": "OnTick 按“有没有东西在动”分档，闲置约 10fps；实测空闲 CPU 0.66s/10s → 0.50s/20s", "scored": True},
        {"id": "Q-002", "标题": "下载页要把 v55 包体同步上去，但内嵌 base64 超过单页 20MiB 上限", "来源": "同步任务",
         "严重度": "P1", "状态": "solved", "发现时间": "2026-11-17 22:10", "解决时间": "2026-11-18 07:50",
         "解决说明": "页面只留壳，下载按钮走 CDN 直链，JS 加空块兜底；发布 finished", "scored": True},
        {"id": "Q-003", "标题": "电脑端 54 / 网页 50 / 手机 50 三处版本不一致", "来源": "巡检",
         "严重度": "P2", "状态": "solved", "发现时间": "2026-11-17 22:00", "解决时间": "2026-11-18 07:55",
         "解决说明": "APP_VER/HTML_VER/versionCode 统一 55，apk 重打包并校验 MD5", "scored": True},
        {"id": "Q-004", "标题": "形象在桌面上看不见（UpdateLayeredWindow 返回 err=87）", "来源": "用户反馈（旧账第 8 项）",
         "严重度": "P1", "状态": "open", "发现时间": "2026-11-15 22:30", "解决时间": "",
         "解决说明": "", "scored": False},
        {"id": "Q-005", "标题": "DiagTrack 与 HKLM 下 Conexant 三件套自启未关（要一次管理员提权）", "来源": "开机慢排查",
         "严重度": "P1", "状态": "wait", "发现时间": "2026-11-18 07:05", "解决时间": "",
         "解决说明": "脚本已备好：tools\\开机瘦身_管理员.ps1", "scored": False},
        {"id": "Q-006", "标题": "豆包 16 个进程占 2.5GB 内存（登录后可用只剩 2.6GB）", "来源": "开机慢排查",
         "严重度": "P2", "状态": "wait", "发现时间": "2026-11-18 07:05", "解决时间": "",
         "解决说明": "可选：改手动启动；等用户拍板", "scored": False},
        {"id": "Q-007", "标题": "手机端 v55 未在真机安装验证（巡检里最后上报仍是 v50）", "来源": "巡检",
         "严重度": "P2", "状态": "wait", "发现时间": "2026-11-18 07:38", "解决时间": "",
         "解决说明": "等真机装一次", "scored": False},
        {"id": "Q-008", "标题": "下载页改走直链后，未在手机浏览器/微信里实测一次", "来源": "本轮改动",
         "严重度": "P3", "状态": "open", "发现时间": "2026-11-18 07:50", "解决时间": "",
         "解决说明": "", "scored": False}
    ]
}


def now_str():
    return datetime.datetime.now().strftime('%Y-%m-%d %H:%M')


def load_or_seed(path, seed):
    if not os.path.exists(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(seed, f, ensure_ascii=False, indent=2)
        return json.loads(json.dumps(seed)), True
    with open(path, encoding='utf-8-sig') as f:
        return json.load(f), False


def save(path, obj):
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def _lib():
    """把 tools\\问题库.py 当模块用（同目录），统一登记/去重/复发计数"""
    import importlib.util
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), '问题库.py')
    spec = importlib.util.spec_from_file_location('problem_lib', p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _issue_register(title, 来源='', 严重度='P2', 说明='', key=''):
    try:
        return _lib().register(title, 来源=来源, 严重度=严重度, 说明=说明, key=key)
    except Exception:
        # 兜底：老办法直接塞一条，保证不丢
        return {'id': 'Q-???', '新建': True, '复发': 0, '说明': '问题库.py 调不动，按新条登记'}


def _issue_load():
    try:
        return _lib().load().get('问题', [])
    except Exception:
        return []


def parse_time(s):
    for fmt in ('%Y-%m-%d %H:%M', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d'):
        try:
            return datetime.datetime.strptime(s, fmt)
        except Exception:
            pass
    return None


def main():
    out = ['【愉悦与问题】']
    warn = []

    joy, joy_new = load_or_seed(JOY, SEED_JOY)
    iss, iss_new = load_or_seed(ISSUES, SEED_ISSUES)
    if joy_new:
        out.append('  愉悦值台账刚建好：%s' % JOY)
    if iss_new:
        out.append('  问题库刚建好：%s' % ISSUES)

    score_before = joy.get('当前愉悦值')
    today = datetime.date.today().isoformat()
    added_today = 0

    # ---------- 结算：已解决的问题自动加分（幂等） ----------
    items = iss.get('问题', [])
    for it in items:
        if it.get('状态') == 'solved' and not it.get('scored'):
            d = REWARD.get(it.get('严重度', 'P3'), 1)
            joy.setdefault('记录', []).append({
                '时间': now_str(), '类型': '解决问题', '分值': d,
                '理由': '解决 %s：%s' % (it.get('严重度', 'P3'), it.get('标题', '')),
                '关联问题': it.get('id', '')
            })
            it['scored'] = True
            if not it.get('解决时间'):
                it['解决时间'] = now_str()
            out.append('  结算：%s %s 已解决，+%d' % (it.get('id', ''), it.get('标题', '')[:28], d))

    # ---------- 复发：同一个问题又出现 → 越复发扣得越狠（1 次 -1、2 次 -3、3 次 -5、之后每次 -6 封顶） ----------
    for it in items:
        n = int(it.get('复发次数', 0))
        paid = int(it.get('复发扣分', 0))
        if n > paid:
            for k in range(paid + 1, n + 1):
                d = min(6, 1 + 2 * (k - 1))
                joy.setdefault('记录', []).append({
                    '时间': now_str(), '类型': '问题复发', '分值': -d,
                    '理由': '%s 第 %d 次复发：%s' % (it.get('id', ''), k, it.get('标题', '')[:28]),
                    '关联问题': it.get('id', '')
                })
                out.append('  复发扣分：%s 第 %d 次复发，-%d' % (it.get('id', ''), k, d))
            it['复发扣分'] = n
            it['最近复发'] = it.get('复发时间', '') or now_str()

    # ---------- 停滞：open/wait 超过 STALE_DAYS 天没动 → 按制度扣分（单个问题最多 -5） ----------
    stale = []
    for it in items:
        if it.get('状态') not in ('open', 'wait'):
            continue
        t = parse_time(it.get('发现时间', ''))
        if not t:
            warn.append('问题 %s 的发现时间看不懂：%r' % (it.get('id', ''), it.get('发现时间', '')))
            continue
        days = (datetime.datetime.now() - t).days
        it['停滞天数'] = days
        if days > STALE_DAYS:
            stale.append((it, days))

    for it, days in stale:
        paid = it.get('停滞扣分', 0)
        want = min(5, days - STALE_DAYS)
        if paid < want:
            d = want - paid
            joy.setdefault('记录', []).append({
                '时间': now_str(), '类型': '停滞', '分值': -d,
                '理由': '%s 已 %d 天没动：%s' % (it.get('id', ''), days, it.get('标题', '')[:28]),
                '关联问题': it.get('id', '')
            })
            it['停滞扣分'] = want
            out.append('  停滞扣分：%s 放着 %d 天没动，-%d' % (it.get('id', ''), days, d))

    # ---------- 防重复刷分：同一件事只加一次；同类加分按制度有日上限（2026-11-18 加） ----------
    # 目的是让分数反映真实的进步，而不是靠反复跑脚本、反复登记同一件事把分堆上去。
    CAP_DAY = {'用户赞许': 9, '作品点赞': 5, '学到好东西': 3, '巡检通过': 1, '能力激励': 5, '版本一致': 1, '电脑真用': 1, '手机真用': 1}
    seen_fp = {}
    kept = {}
    dropped = 0
    capped = 0
    drop_val = 0
    for r in joy.get('记录', []):
        try:
            d = int(r.get('分值', 0))
        except Exception:
            d = 0
        if d <= 0 or not str(r.get('时间', '')).startswith(today):
            continue
        fp = '%s|%s' % (r.get('类型', ''), r.get('关联问题') or str(r.get('理由', ''))[:24])
        if fp in seen_fp:
            r['分值'] = 0
            r['重复跳过'] = True
            dropped += 1
            drop_val += d
            continue
        seen_fp[fp] = True
        cap = CAP_DAY.get(r.get('类型', ''))
        if cap is not None:
            used = kept.get(r.get('类型', ''), 0)
            if used + d > cap:
                allow = max(0, cap - used)
                r['分值'] = allow
                r['超上限裁剪'] = True
                capped += 1
                drop_val += d - allow
                d = allow
            kept[r.get('类型', '')] = used + d
    if dropped or capped:
        out.append('  防刷分：同事件跳过 %d 条、超日上限裁剪 %d 条，共拦下 %d 分' % (dropped, capped, drop_val))
    if dropped:
        warn.append('今天有 %d 条重复加分被拦下（同一件事只加一次，别刷）' % dropped)

    # ---------- 体检 ----------
    total = sum(int(r.get('分值', 0)) for r in joy.get('记录', []))
    lo, hi = joy.get('区间', [0, 100])
    if total < lo or total > hi:
        warn.append('愉悦值算出来是 %d，跑到区间 %s 外面了，台账可能被手改过' % (total, joy.get('区间')))
    joy['当前愉悦值'] = max(lo, min(hi, total))

    for r in joy.get('记录', []):
        if '时间' not in r or '分值' not in r or '理由' not in r:
            warn.append('愉悦值台账有一条缺字段：%r' % (r,))

    n_open = sum(1 for i in items if i.get('状态') == 'open')
    n_wait = sum(1 for i in items if i.get('状态') == 'wait')
    n_done = sum(1 for i in items if i.get('状态') == 'solved')
    n_other = len(items) - n_open - n_wait - n_done
    if n_other:
        warn.append('问题库里有 %d 条状态不是 open/wait/solved，结算会漏掉' % n_other)

    for it in items:
        for k in ('id', '标题', '严重度', '状态'):
            if not it.get(k):
                warn.append('问题库有一条缺 %s：%r' % (k, it.get('标题', '?')))

    ids = [i.get('id') for i in items]
    dup = set(x for x in ids if ids.count(x) > 1)
    if dup:
        warn.append('问题库有重复 id：%s' % '、'.join(sorted(dup)))

    # 问题库多久没更新（超过 30 天没新增/没改，说明这台“记事本”在吃灰）
    newest = None
    for it in items:
        for k in ('解决时间', '发现时间'):
            t = parse_time(it.get(k, ''))
            if t and (newest is None or t > newest):
                newest = t
    if newest:
        idle = (datetime.datetime.now() - newest).days
        if idle > 30:
            warn.append('问题库已经 %d 天没有更新过（最后一次 %s）' % (idle, newest.strftime('%Y-%m-%d')))

    # ---------- 低愉悦处置：跌到 LOW 以下就自动立一个自救项，回到 RECOVER 以上自动关掉 ----------
    LOW, RECOVER = 45, 50
    rescue = [i for i in items if i.get('来源') == '低愉悦自救' and i.get('状态') != 'solved']
    if joy['当前愉悦值'] < LOW:
        if not rescue:
            r = _issue_register('愉悦值跌到 %d（<%d），按制度先补短板、先修 P1' % (joy['当前愉悦值'], LOW),
                                来源='低愉悦自救', 严重度='P1', key='joy:low')
            items = _issue_load()
            out.append('  低愉悦处置：愉悦值 %d 低于 %d，已登记自救项 %s（%s；分数回到 %d 自动关闭）'
                       % (joy['当前愉悦值'], LOW, r['id'], r['说明'], RECOVER))
        else:
            out.append('  低愉悦处置：愉悦值 %d 仍低于 %d，自救项 %s 在进行中'
                       % (joy['当前愉悦值'], LOW, '、'.join(i.get('id', '') for i in rescue)))
    elif rescue and joy['当前愉悦值'] >= RECOVER:
        for i in rescue:
            i['状态'] = 'solved'
            i['解决时间'] = now_str()
            i['解决说明'] = '愉悦值回到 %d（≥%d），自救项自动关闭' % (joy['当前愉悦值'], RECOVER)
        out.append('  低愉悦处置：愉悦值回到 %d，自救项 %s 已自动关闭（+%d 记账在下一轮结算）'
                   % (joy['当前愉悦值'], '、'.join(i.get('id', '') for i in rescue),
                      sum(REWARD.get(i.get('严重度', 'P3'), 1) for i in rescue)))

    # 今日变动：起步那 50 分是基线，不算今天涨的
    for r in joy.get('记录', []):
        if r.get('时间', '').startswith(today) and r.get('类型') != '起步':
            added_today += int(r.get('分值', 0))

    out.append('  愉悦值：%d（区间 %d-%d）%s' % (joy['当前愉悦值'],
             lo, hi, ('今日净变动 %+d' % added_today) if added_today else '今日无变动'))
    out.append('  问题库：未解决 %d / 待用户 %d / 已解决 %d%s' % (n_open, n_wait, n_done,
             ('，停滞 %d' % len(stale)) if stale else ''))
    for it in sorted(items, key=lambda x: (x.get('状态') != 'open', x.get('id', ''))):
        if it.get('状态') in ('open', 'wait'):
            tag = '待用户' if it.get('状态') == 'wait' else '未解决'
            rep = int(it.get('复发次数', 0))
            if rep:
                tag += '·已复发 %d 次' % rep
            out.append('    · [%s] %s %s（%s）' % (it.get('严重度'), it.get('id'), it.get('标题', '')[:34], tag))

    # 复发的东西不能拖：每次都要在报告里点名字提醒，复发次数越多越靠前
    rep_open = [i for i in items if int(i.get('复发次数', 0)) > 0 and i.get('状态') != 'solved']
    if rep_open:
        rep_open.sort(key=lambda x: -int(x.get('复发次数', 0)))
        for i in rep_open:
            out.append('  提醒：%s「%s」已复发 %d 次，今天就处理，别再放着'
                       % (i.get('id', ''), i.get('标题', '')[:28], int(i.get('复发次数', 0))))
            warn.append('%s 复发 %d 次未处理' % (i.get('id', ''), int(i.get('复发次数', 0))))
    # 今日已经加的分列出来，方便核对有没有乱加
    wins = [r for r in joy.get('记录', []) if r.get('时间', '').startswith(today)
            and int(r.get('分值', 0)) > 0 and r.get('类型') != '起步']
    if wins:
        out.append('  今日加分：' + '；'.join('%s(+%d)' % (r.get('理由', '')[:22], int(r.get('分值', 0))) for r in wins))

    if warn:
        for w in warn:
            out.append('  ! ' + w)

    save(JOY, joy)
    save(ISSUES, iss)

    out.append('  JOY_STATE=' + ('WARN' if warn else 'OK'))
    print('\n'.join(out))
    return 0


if __name__ == '__main__':
    sys.exit(main())
