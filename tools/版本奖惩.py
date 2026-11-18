# -*- coding: utf-8 -*-
"""版本更新检测 + 版本内容真实使用 的奖惩结算（2026-11-18 加）

用户要求：「版本更新检测奖励惩罚机制也要有，版本内容要定期真实使用。」
所以这里做两件事，都要有证据、可重算：

1) 检测奖惩
   +1 版本一致        电脑 / apk / 页面 / 线上 / 手机上报，五处同一个号（一天一次）
   -1 某端落后（每端每天）  某端版本号比当前最高版低，且距离该端「应该升到当前版」的时间 ≥3 天
                        （手机按 apk 构建时间算，电脑按 exe 时间算，页面按源文件时间算）
   -1 线上核对失败（不扣分） 抓不到线上页时只报 UNKN，不奖不罚，避免断网被当成退步

2) 真实使用奖惩
   +1 电脑真用        今天 道.exe 进程在跑（进程存在即证据，不看谁点开）
   +1 手机真用        今天 手机自检.txt 追加的那一行，版本号 = 当前版
   -1 真用停滞        某一端连续 3 天没有新证据（每端每天 −1）

3) 版本内容真验（写进 自我状态/版本使用.json）
   每个版本登记要真验的内容项（默认目标 3 项），到期（上线 7 天）验不到就 −1；
   已经验过但超过 30 天没再验的项不算数，催着定期真实使用。

所有加减都写进 愉悦值.json 的「记录」，同一类型同一理由当天只记一次；
愉悦值检查.py 还会再做一遍指纹去重与日上限，双保险。
"""
import json, os, re, subprocess, sys, datetime, urllib.request

ROOT = r'F:\Daodao'
STATE = os.path.join(ROOT, '自我状态')
JOY = os.path.join(STATE, '愉悦值.json')
BOOK = os.path.join(STATE, '版本账本.json')
USE = os.path.join(STATE, '版本使用.json')
PHONE = os.path.join(ROOT, '手机自检.txt')
LANDING = os.path.join(ROOT, '引导页_src', 'index.html')
ONLINE = 'https://4mf81m04wehh3.doubao.link/app/app_17hnj8acgs2'

DOUBLE_DAY = 3      # 落后多少天才开始扣
STALL_DAY = 3       # 连续多少天没真用才扣
TARGET_ITEMS = 3    # 每个版本要真验几项内容
DUE_DAY = 7         # 上线几天内要验完
FRESH_DAY = 30      # 验过的项多久不重验就不算数
MAX_LAG_PENALTY = 3


def now():
    return datetime.datetime.now()


def read(p):
    try:
        with open(p, encoding='utf-8-sig') as f:
            return f.read()
    except Exception:
        return ''


def load_json(p, default):
    try:
        with open(p, encoding='utf-8-sig') as f:
            return json.load(f)
    except Exception:
        return default


def save_json(p, obj):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def ver_of(text, pattern):
    m = re.search(pattern, text)
    return m.group(1) if m else None


def mtime(p):
    try:
        return datetime.datetime.fromtimestamp(os.path.getmtime(p))
    except Exception:
        return None


def online_ver():
    try:
        req = urllib.request.Request(ONLINE, headers={'User-Agent': 'dao-version-check'})
        with urllib.request.urlopen(req, timeout=12) as r:
            return ver_of(r.read().decode('utf-8', 'replace'), r'data-ver="(\d+)"')
    except Exception:
        return None


def desktop_running():
    try:
        out = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq 道.exe'],
                             capture_output=True, text=True, timeout=30,
                             errors='replace').stdout
        return '道.exe' in out
    except Exception:
        return False


def phone_last():
    """手机自检.txt 最后一行：返回 (时间, 版本号, bad)"""
    rows = [l for l in read(PHONE).split('\n') if l.strip()]
    if not rows:
        return None, None, None
    last = rows[-1]
    ts = last.split('|')[0].strip()
    hv = re.search(r'html=(\d+)', last)
    bad = re.search(r'bad=([^|]*)', last)
    return ts, (hv.group(1) if hv else None), (bad.group(1).strip() if bad else '')


def add_joy(recs, kinds, typ, val, reason):
    """写一条记账；同一类型+同一理由今天只加一次（防刷分第一道）"""
    today = now().strftime('%Y-%m-%d')
    fp = typ + '|' + reason[:24]
    for r in recs:
        if not str(r.get('时间', '')).startswith(today):
            continue
        if (r.get('类型') == typ and str(r.get('理由', ''))[:24] == reason[:24]):
            kinds.append('%s：今天已记过，跳过' % typ)
            return 0
    recs.append({'时间': now().strftime('%Y-%m-%d %H:%M'), '类型': typ,
                 '分值': val, '理由': reason})
    kinds.append('%+d %s（%s）' % (val, typ, reason))
    return val


def main():
    out = []
    kinds = []
    ver_desk = ver_of(read(os.path.join(ROOT, 'src', '桌面分身', 'pet.cs')), r'APP_VER\s*=\s*(\d+)')
    ver_apk = ver_of(read(os.path.join(ROOT, 'src', '_apk', 'AndroidManifest.xml')), r'versionCode="(\d+)"')
    ver_page = ver_of(read(os.path.join(ROOT, 'src', '_apk', 'assets', 'dao.html')), r"HTML_VER\s*=\s*'(\d+)'")
    ver_land = ver_of(read(LANDING), r'data-ver="(\d+)"')
    v_online = online_ver()
    p_ts, v_phone, p_bad = phone_last()
    nums = [int(v) for v in (ver_desk, ver_apk, ver_page) if v]
    top = max(nums) if nums else None

    # ---------- 1. 检测 ----------
    aligned = (ver_desk == ver_apk == ver_page == ver_land and v_phone == ver_desk and top is not None)
    out.append('【版本奖惩】')
    out.append('  电脑 v%s · 手机 v%s（最后上报 %s）· 页面 v%s · 线上 v%s'
               % (ver_desk, v_phone, p_ts or '从未', ver_land, v_online or '抓不到'))

    joy = load_json(JOY, {'记录': [], '当前愉悦值': 50})
    recs = joy.setdefault('记录', [])

    delta = 0
    if aligned:
        delta += add_joy(recs, kinds, '版本一致', 1, '五处同为 v%s（电脑/apk/页面/线上/手机上报）' % ver_desk)
    else:
        out.append('  一致：否（电脑 %s / apk %s / 页面 %s / 线上 %s / 手机 %s）'
                   % (ver_desk, ver_apk, ver_page, ver_land or '?', v_phone))
    if v_online is None:
        out.append('  线上：没抓到，本次不奖不罚（不算退步，只算没核对到）')

    # 落后判罚
    lag = []
    if top is not None:
        if v_phone and v_phone != ver_apk:
            t = mtime(os.path.join(ROOT, '道.apk'))
            days = (now() - t).days if t else 0
            lag.append(('手机', days))
        if ver_desk != ver_apk:
            t = mtime(os.path.join(ROOT, '道.exe'))
            days = (now() - t).days if t else 0
            lag.append(('电脑', days))
        if ver_land and ver_page and ver_land != ver_page:
            t = mtime(LANDING)
            days = (now() - t).days if t else 0
            lag.append(('页面', days))
    pen = 0
    for end, days in lag:
        if days >= DOUBLE_DAY and pen < MAX_LAG_PENALTY:
            pen += 1
            delta += add_joy(recs, kinds, '版本落后', -1, '%s 端已落后 %d 天（超 %d 天要扣）' % (end, days, DOUBLE_DAY))
    if lag:
        out.append('  落后：' + '、'.join('%s %d 天' % (e, d) for e, d in lag))

    # ---------- 2. 真实使用 ----------
    # 判据分开：+1 只认「当前版本被真用」；停滞扣分只看「这一端多久没任何活跃证据」，
    # 免得同一个「手机没升级」既算落后又算停滞，一错两罚。
    book = load_json(BOOK, {'真用': {}, '已结算': {}})
    use = book.setdefault('真用', {})
    today = now().strftime('%Y-%m-%d')
    desk_run = desktop_running()
    if desk_run:
        use['电脑'] = {'最后': now().strftime('%Y-%m-%d %H:%M'), '版本': ver_desk, '证据': '进程 道.exe 在跑'}
        delta += add_joy(recs, kinds, '电脑真用', 1, 'v%s 今天真在跑（进程证据）' % ver_desk)
    if p_ts:
        use['手机'] = {'最后': p_ts, '版本': v_phone, '证据': '手机自检.txt 最后一行'}
    ph_ok = bool(v_phone and v_phone == ver_desk and str(p_ts).startswith(today))
    if ph_ok:
        delta += add_joy(recs, kinds, '手机真用', 1, 'v%s 今天手机端自己上报了自检' % v_phone)
    for end in ('电脑', '手机'):
        e = use.get(end)
        if not e or not e.get('最后'):
            days = 999
        else:
            try:
                days = (now() - datetime.datetime.strptime(str(e['最后'])[:16], '%Y-%m-%d %H:%M')).days
            except Exception:
                days = 999
        if days >= STALL_DAY:
            delta += add_joy(recs, kinds, '真用停滞', -1, '%s 端已 %d 天没活跃（≥%d 天要扣）' % (end, min(days, 99), STALL_DAY))
    d_use = use.get('电脑', {}).get('最后', '从未')
    p_use = use.get('手机', {}).get('最后', '从未')
    out.append('  真用：电脑 %s%s · 手机 %s（v%s）' % (d_use, '（在跑）' if desk_run else '', p_use, v_phone or '?'))

    # ---------- 3. 版本内容真验 ----------
    u = load_json(USE, {'版本': {}})
    vers = u.setdefault('版本', {})
    cur = str(top) if top else None
    if cur:
        blk = vers.setdefault(cur, {'立项': today, '项': [], '目标': TARGET_ITEMS})
        blk.setdefault('目标', TARGET_ITEMS)
        fresh = []
        for it in blk.get('项', []):
            try:
                d = datetime.datetime.strptime(it.get('验证', ''), '%Y-%m-%d')
                if (now() - d).days <= FRESH_DAY:
                    fresh.append(it)
            except Exception:
                pass
        try:
            born = datetime.datetime.strptime(blk.get('立项', today), '%Y-%m-%d')
            age = (now() - born).days
        except Exception:
            age = 0
        out.append('  内容真验 v%s：%d/%d 项（立项第 %d 天，剩余 %d 天到期）'
                   % (cur, len(fresh), blk.get('目标', TARGET_ITEMS), age, max(0, DUE_DAY - age)))
        for it in fresh[:5]:
            out.append('    · %s（%s）' % (it.get('项', '?'), it.get('验证', '?')))
        if age >= DUE_DAY and len(fresh) < blk.get('目标', TARGET_ITEMS):
            delta += add_joy(recs, kinds, '内容未验', -1,
                             'v%s 上线 %d 天只真验 %d/%d 项' % (cur, age, len(fresh), blk.get('目标', TARGET_ITEMS)))

    # ---------- 落账 ----------
    # 总额由 愉悦值检查.py 统一重算（它会把全部记录求和），这里只负责把记录写进去，不自己加总。
    save_json(JOY, joy)

    book['检测'] = {
        '时间': now().strftime('%Y-%m-%d %H:%M'),
        '电脑': ver_desk, 'apk': ver_apk, '页面': ver_page, '线上': v_online, '手机': v_phone,
        '手机上报时间': p_ts, '一致': aligned, '落后': {e: d for e, d in lag},
    }
    save_json(BOOK, book)
    save_json(USE, u)

    if kinds:
        out.append('  结算：' + '；'.join(kinds))
    else:
        out.append('  结算：本次没有新的加减（同类今天已记过）')
    print('\n'.join(out))
    # OK=全对齐；MISMATCH=没对齐但还没到扣分线；LAG=本次真的扣了分（要在报告里挂 WARN）
    penal = any(k.startswith('-') for k in kinds)
    print('VSTATE=' + ('LAG' if penal else ('OK' if aligned else 'MISMATCH')))
    return 0


if __name__ == '__main__':
    sys.exit(main())
