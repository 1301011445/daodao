# -*- coding: utf-8 -*-
"""「道」两端自动巡检：版本、名单、图片、包内、进程、发布一致性。
用法：python inspect_dao.py
输出：F:\\Daodao\\巡检报告\\巡检_YYYYMMDD_HHMM.txt，末行 PASS / FAIL
"""
import os, re, sys, struct, subprocess, datetime, socket, urllib.request, json

ROOT = r'F:\Daodao'
SRC = os.path.join(ROOT, 'src')
BUNDLE = os.path.join(SRC, '桌面分身', '_bundle')
PETCS = os.path.join(SRC, '桌面分身', 'pet.cs')
APKDIR = os.path.join(SRC, '_apk')
DAOHTML = os.path.join(APKDIR, 'assets', 'dao.html')
MANIFEST = os.path.join(APKDIR, 'AndroidManifest.xml')
EXE = os.path.join(ROOT, '道.exe')
APK = os.path.join(ROOT, '道.apk')
SEVENZ = r'E:\Tools\7-Zip\7z.exe'
AAPT2 = r'E:\AndroidTools\sdk\build-tools\34.0.0\aapt2.exe'

CC = []   # (level, text)
def rec(level, text, detail=''):
    CC.append((level, text, detail))

def read(p, enc='utf-8-sig'):
    with open(p, 'r', encoding=enc, errors='replace') as f:
        return f.read()

def png_info(p):
    """返回 (宽, 高, colorType)；colorType 6 = RGBA"""
    with open(p, 'rb') as f:
        head = f.read(33)
    if head[:8] != b'\x89PNG\r\n\x1a\n':
        return None
    w, h = struct.unpack('>II', head[16:24])
    return (w, h, head[25])

MUSIC = os.path.join(ROOT, 'tools', '音乐')
PY = sys.executable

def _run_py(script_dir, script, timeout=120):
    """跑一个音乐工具脚本，回 (returncode, 输出文本)"""
    try:
        r = subprocess.run([PY, script], cwd=os.path.join(MUSIC, script_dir),
                           capture_output=True, timeout=timeout)
        out = (r.stdout or b'').decode('utf-8', 'replace') + (r.stderr or b'').decode('utf-8', 'replace')
        return r.returncode, out
    except Exception as e:
        return -1, 'EXC %s' % e

def music_check(lines, problems):
    """音乐这一摊的自动巡检：学习归档自检 + 词曲判据 + 两端曲库一致性。
    只报事实，不改东西；发现问题进 problems，留给巡检报告与待改进.md。"""
    lines.append('【音乐自检】')
    if not os.path.isdir(MUSIC):
        lines.append('  tools\\音乐 不存在，音乐巡检跳过')
        problems.append('WARN 音乐工具目录缺失（tools\\音乐）')
        lines.append('')
        return

    # 1) 学习归档自检：类别数 / 缺口数
    code, out = _run_py('学习归档', '归档.py')
    m = re.search(r'归档\s*(\d+)\s*类，缺口\s*(\d+)\s*处', out)
    if m:
        n_cls, n_gap = int(m.group(1)), int(m.group(2))
        lines.append('  学习归档：%d 类，缺口 %d 处' % (n_cls, n_gap))
        for g in re.findall(r'^\s*!\s*(.+)$', out, re.M):
            lines.append('    ! ' + g.strip())
            problems.append('WARN 学习归档缺口：' + g.strip())
    else:
        lines.append('  学习归档：跑不起来（%s）' % (out.strip().splitlines()[-1] if out.strip() else code))
        problems.append('WARN 学习归档脚本跑不起来')

    # 2) 词曲判据 L1-L4
    code, out = _run_py('判据检查', '判据检查.py')
    m2 = re.search(r'汇总：(.*)', out)
    if m2:
        summary = m2.group(1).strip()
        lines.append('  词曲判据：' + summary)
        if '不过' in summary or '×' in summary:
            problems.append('WARN 词曲判据没全过：' + summary)
    elif code == 0:
        lines.append('  词曲判据：跑通了但没看到汇总行')
    else:
        lines.append('  词曲判据：跑不起来（exit=%d）' % code)
        problems.append('WARN 判据检查脚本跑不起来')

    # 3) 两端曲库一致性（电脑 _bundle\\music 与 手机 assets\\music 文件名必须同一套）
    pc_mus = os.path.join(BUNDLE, 'music')
    ph_mus = os.path.join(APKDIR, 'assets', 'music')

    def _names(d):
        """只比 wav（手机端只带 wav；json/mid 是谱源，电脑端独有，不该算不同步）。
        名字规整：手机端为了打进 assets 用了 ASCII 名（demo_01.wav），电脑端是中文全名
        （demo_01_五声主题.wav），所以去掉中文与空段后比前缀，同曲不同名不算缺。"""
        try:
            raw = [f for f in os.listdir(d) if f.lower().endswith('.wav')]
        except OSError:
            return set()
        out = set()
        for f in raw:
            stem = os.path.splitext(f)[0]
            ascii_part = re.match(r'^[A-Za-z0-9_\-]+', stem).group(0) if re.match(r'^[A-Za-z0-9_\-]+', stem) else stem
            out.add(ascii_part.rstrip('_'))
        return out
    a, b = _names(pc_mus), _names(ph_mus)
    if a or b:
        lines.append('  曲库：电脑 %d 个 / 手机 %d 个' % (len(a), len(b)))
        only_a = sorted(a - b)
        only_b = sorted(b - a)
        if only_a:
            lines.append('    只在电脑端：' + '、'.join(only_a[:6]))
            problems.append('WARN 曲库不同步（只在电脑端：%s）' % '、'.join(only_a[:6]))
        if only_b:
            lines.append('    只在手机端：' + '、'.join(only_b[:6]))
            problems.append('WARN 曲库不同步（只在手机端：%s）' % '、'.join(only_b[:6]))
    else:
        lines.append('  曲库：两端都没有音乐文件')
        problems.append('WARN 曲库为空，两端播歌功能等于没素材')

    # 4) 未发布作品仓（只保存不发布的曲子必须有词/谱/母带三件齐全）
    lib = os.path.join(ROOT, '曲库')
    if os.path.isdir(lib):
        wavs = [f for f in os.listdir(lib) if f.lower().endswith('.wav')]
        words = [f for f in os.listdir(ROOT) if f.endswith('_词.md')]
        lines.append('  未发布仓：曲库 %d 首母带，词本 %d 份' % (len(wavs), len(words)))
    lines.append('')

def joy_check(lines, problems):
    """愉悦值与问题库（2026-11-18 新加的一节）。
    跑 tools\\愉悦值检查.py：结算已解决问题该加的分、算停滞、体检两份 JSON。
    只报事实，不判 FAIL；WARN 会落到问题区，留给人看。"""
    lines.append('【愉悦与问题】')
    script = os.path.join(ROOT, 'tools', '愉悦值检查.py')
    if not os.path.exists(script):
        lines.append('  tools\\愉悦值检查.py 不在，本节跳过')
        problems.append('WARN 愉悦值检查脚本缺失')
        lines.append('')
        return
    try:
        r = subprocess.run([PY, script], capture_output=True, timeout=120)
        out = (r.stdout or b'').decode('utf-8', 'replace') + (r.stderr or b'').decode('utf-8', 'replace')
    except Exception as e:
        lines.append('  跑不起来：%s' % e)
        problems.append('WARN 愉悦值检查跑不起来')
        lines.append('')
        return
    for l in out.splitlines():
        s = l.strip()
        if not s or s.startswith('【愉悦与问题】') or s.startswith('JOY_STATE='):
            continue
        lines.append(l)
    if 'JOY_STATE=WARN' in out:
        for l in out.splitlines():
            s = l.strip()
            if s.startswith('!'):
                problems.append('WARN 愉悦值/问题库：' + s.lstrip('!').strip())
    lines.append('')

def main():
    ts = datetime.datetime.now()
    checks = {}
    problems = []

    # ---------- 1. 电脑端素材 ----------
    faces = sorted([f for f in os.listdir(BUNDLE) if re.match(r'face_\d+\.png$', f)],
                   key=lambda x: int(re.findall(r'\d+', x)[0]))
    n_faces = len(faces)
    checks['电脑端形象张数'] = n_faces
    idx = [int(re.findall(r'\d+', f)[0]) for f in faces]
    if idx != list(range(n_faces)):
        problems.append('脸图编号不连续：%s' % idx)
    bad_png = []
    for f in faces:
        info = png_info(os.path.join(BUNDLE, f))
        if info is None:
            bad_png.append(f + '(非PNG)')
        else:
            w, h, ct = info
            if h < 400:
                bad_png.append('%s(高度%d偏小)' % (f, h))
    if bad_png:
        problems.append('脸图异常：' + '，'.join(bad_png))

    names = [l.strip() for l in read(os.path.join(BUNDLE, 'names.txt')).split('\n') if l.strip()]
    voices_p = os.path.join(BUNDLE, 'voices.txt')
    voices = [l for l in read(voices_p).split('\n') if l.strip()] if os.path.exists(voices_p) else []
    checks['names 条数'] = len(names)
    checks['voices 条数'] = len(voices)
    if len(names) < n_faces:
        problems.append('names.txt 只有 %d 条，少于形象数 %d' % (len(names), n_faces))
    if len(voices) < n_faces:
        problems.append('WARN 音色表 %d 条，少于形象数 %d（这些形象无配音）' % (len(voices), n_faces))

    expr = len([f for f in os.listdir(BUNDLE) if re.match(r'expr_\d+_\w+\.png$', f)])
    pose = len([f for f in os.listdir(BUNDLE) if re.match(r'pose_\d+_\w+\.png$', f)])
    checks['表情帧张数'] = expr
    checks['动作帧张数'] = pose

    # ---------- 2. 版本号三处 ----------
    cs = read(PETCS)
    m = re.search(r'public const int APP_VER = (\d+);', cs)
    app_ver = int(m.group(1)) if m else None
    man = read(MANIFEST)
    m2 = re.search(r'versionCode="(\d+)"', man)
    ver_code = int(m2.group(1)) if m2 else None
    checks['APP_VER(pet.cs)'] = app_ver
    checks['versionCode(manifest)'] = ver_code

    html = read(DAOHTML)
    m3 = re.search(r"var HTML_VER = '(\d+)';", html)
    html_ver = int(m3.group(1)) if m3 else None
    checks['HTML_VER(源页面)'] = html_ver

    # ---------- 3. 手机端页面结构 ----------
    def arr(name):
        i = html.find('var %s = [' % name)
        if i < 0:
            return None
        j = html.find(']', i)
        return re.findall(r"[^,\[\]]+", html[i + len('var %s = [' % name):j])

    faces_seg = html[html.index('var FACES = ['):html.index('];', html.index('var FACES = [') + 1)]
    n_faces_html = faces_seg.count('data:image')
    checks['页面 FACES 张数'] = n_faces_html
    ks = arr('_ks')
    kinds = arr('_kinds')
    who = arr('WHO')
    checks['_ks 项数'] = len(ks) if ks else 0
    checks['WHO 项数'] = len(who) if who else 0
    for nm, v in (('_ks', ks), ('_kinds', kinds), ('WHO', who), ('FY', arr('FY')), ('FW', arr('FW'))):
        if not v:
            problems.append('页面缺少数组 %s' % nm)
        elif len(v) != n_faces:
            problems.append('页面 %s 项数 %d ≠ 形象数 %d' % (nm, len(v), n_faces))

    if n_faces_html != n_faces:
        problems.append('页面内嵌 %d 张图，_bundle 有 %d 张，两端不同步' % (n_faces_html, n_faces))

    # ---------- 4. 版本一致性 ----------
    if app_ver is None or ver_code is None or html_ver is None:
        problems.append('版本号读取失败：APP_VER=%s versionCode=%s HTML_VER=%s' % (app_ver, ver_code, html_ver))
    elif len({app_ver, ver_code, html_ver}) > 1:
        problems.append('三处版本号不一致：pet.cs=%s manifest=%s 页面=%s' % (app_ver, ver_code, html_ver))

    # ---------- 5. 产物与包内 ----------
    for p, label in ((EXE, '道.exe'), (APK, '道.apk')):
        if not os.path.exists(p):
            problems.append('%s 不存在' % label)
        else:
            checks[label + ' 字节'] = os.path.getsize(p)

    if os.path.exists(EXE) and app_ver is not None:
        pass
    if os.path.exists(APK):
        try:
            out = subprocess.run([AAPT2, 'dump', 'badging', APK], capture_output=True, text=True, timeout=60, errors='replace').stdout
            pk = re.search(r"versionCode='(\d+)'", out)
            if pk and int(pk.group(1)) != (app_ver or -1):
                problems.append('apk 版本 %s 与 APP_VER %s 不一致' % (pk.group(1), app_ver))
            checks['apk versionCode'] = int(pk.group(1)) if pk else None
        except Exception as e:
            problems.append('aapt2 读取失败：%s' % e)

        tmp = os.path.join(ROOT, '_tmp_face', 'apkcheck_auto')
        os.makedirs(tmp, exist_ok=True)
        try:
            subprocess.run([SEVENZ, 'e', APK, '-o' + tmp, r'assets\dao.html', '-y'],
                           capture_output=True, timeout=120)
            inner = os.path.join(tmp, 'dao.html')
            if os.path.exists(inner):
                ih = read(inner)
                iv = re.search(r"var HTML_VER = '(\d+)';", ih)
                ifr = ih[ih.index('var FACES = ['):ih.index('];', ih.index('var FACES = [')) + 1]
                checks['包内 HTML_VER'] = int(iv.group(1)) if iv else None
                checks['包内 FACES 张数'] = ifr.count('data:image')
                if iv and html_ver is not None and int(iv.group(1)) != html_ver:
                    problems.append('包内页面版本 %s ≠ 源页面 %s，改动没打进 apk' % (iv.group(1), html_ver))
                if ifr.count('data:image') != n_faces:
                    problems.append('包内脸图 %d 张 ≠ %d 张' % (ifr.count('data:image'), n_faces))
            else:
                problems.append('apk 里没找到 assets/dao.html')
        except Exception as e:
            problems.append('解包核对失败：%s' % e)

    # ---------- 6. 运行状态 ----------
    running = False
    try:
        tl = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq 道.exe'], capture_output=True, text=True, timeout=30, errors='replace').stdout
        running = '道.exe' in tl
    except Exception:
        pass
    checks['电脑端进程'] = '运行中' if running else '未运行'
    if not running:
        problems.append('电脑端进程没在跑（道.exe）')

    ping = None
    try:
        socket.create_connection(('127.0.0.1', 8848), timeout=4).close()
        ping = urllib.request.urlopen('http://127.0.0.1:8848/ping', timeout=6).read().decode('utf-8', 'replace')
        checks['接口 ping'] = ping.strip()
    except Exception as e:
        checks['接口 ping'] = '无响应(%s)' % type(e).__name__
    if ping and app_ver is not None and ('|%s|' % app_ver) not in ping:
        problems.append('运行中的实例版本不是 %s：%s' % (app_ver, ping))

    # ---------- 7. 两端图片逐张对应 ----------
    import base64
    imgs = re.findall(r'"data:image/[a-z]+;base64,([A-Za-z0-9+/=]+)"', faces_seg)
    mismatch = []
    for i, b in enumerate(imgs[:len(faces)]):
        try:
            raw = base64.b64decode(b)
            w2, h2 = struct.unpack('>II', raw[16:24])
        except Exception:
            mismatch.append('%d号解码失败' % i)
            continue
        info = png_info(os.path.join(BUNDLE, faces[i]))
        if not info:
            continue
        exp_w = info[0] * 300.0 / info[1]
        if abs(w2 - exp_w) > 3 or abs(h2 - 300) > 2:
            mismatch.append('%d号 页面%dx%d 素材比%.0f宽' % (i, w2, h2, exp_w))
    if mismatch:
        problems.append('WARN 页面图与素材宽高比有差（历史老图裁切不同，供参考）：' + '，'.join(mismatch))
    else:
        checks['页面图与素材'] = '%d 张比例全部对应' % min(len(imgs), len(faces))

    # ---------- 8. 线上页面版本 ----------
    try:
        live = urllib.request.urlopen(
            'https://4mf81m04wehh3.doubao.link/app/app_17hnj8acgs2', timeout=15
        ).read().decode('utf-8', 'replace')
        lv = re.findall(r'data-ver="(\d+)"', live)
        checks['线上页 data-ver'] = lv[0] if lv else '未读到'
        if lv and app_ver is not None and int(lv[0]) != app_ver:
            problems.append('线上下载页 data-ver=%s ≠ 本地版本 %s，线上没跟上' % (lv[0], app_ver))
    except Exception as e:
        checks['线上页 data-ver'] = '取不到(%s)' % type(e).__name__
        problems.append('WARN 线上页面取不到，本次未核对线上版本')

    # ---------- 9. 手机端自检结果 ----------
    phone_p = os.path.join(ROOT, '手机自检.txt')
    if os.path.exists(phone_p):
        rows = [l for l in read(phone_p).split('\n') if l.strip()]
        if rows:
            last_line = rows[-1]
            sc = last_line[last_line.find('SC|'):] if 'SC|' in last_line else last_line
            tsx = last_line.split('|')[0]
            bad_m = re.search(r'bad=([^|]*)', sc)
            bad = bad_m.group(1).strip() if bad_m else ''
            hv = re.search(r'html=(\d+)', sc)
            nf = re.search(r'faces=(\d+)', sc)
            checks['手机自检时间'] = tsx
            checks['手机自检页面版本'] = hv.group(1) if hv else '?'
            checks['手机自检形象张数'] = nf.group(1) if nf else '?'
            if bad and bad != '无':
                problems.append('手机端自检异常（%s）：%s' % (tsx, bad))
            else:
                checks['手机自检'] = '无异常'
            if hv and html_ver is not None and int(hv.group(1)) != html_ver:
                # 2026-11-17 修正：上报时间早于当前 apk 的构建时间，说明真机装的还是上一版，
                # 这是"还没更新"而不是"装错了包"，不该判 FAIL；只有上报时间晚于当前包
                # 却仍然对不上版本号，才是真问题。
                apk_p2 = os.path.join(ROOT, '道.apk')
                apk_mt = None
                if os.path.exists(apk_p2):
                    apk_mt = datetime.datetime.fromtimestamp(os.path.getmtime(apk_p2))
                stale = False
                if apk_mt is not None:
                    try:
                        rep_ts = datetime.datetime.strptime(tsx.strip(), '%Y-%m-%d %H:%M:%S')
                        if rep_ts < apk_mt:
                            stale = True
                    except Exception:
                        pass
                if stale:
                    checks['手机自检'] = '报告早于当前包，真机还没更新到 v%s' % html_ver
                    problems.append('WARN 手机端最后一次上报是 v%s（%s），早于当前包 v%s 的构建时间，'
                                    '真机装更新后才会有新数据' % (hv.group(1), tsx.strip(), html_ver))
                else:
                    problems.append('手机装的是旧包：自检版本 %s ≠ 当前 %s' % (hv.group(1), html_ver))
    else:
        checks['手机自检'] = '还没上报过'
        problems.append('WARN 手机端还没上报过自检（打开一次 App 会自动上报）')

    # ---------- 10. 待改进清单：新问题入册，修好的自动划掉 ----------
    items_p = os.path.join(ROOT, '巡检报告', '待改进.json')
    items = {}
    if os.path.exists(items_p):
        try:
            items = json.loads(read(items_p, 'utf-8'))
        except Exception:
            items = {}
    today = ts.strftime('%Y-%m-%d %H:%M')
    seen = set()
    for p_ in problems:
        if p_.startswith('WARN'):
            continue
        key = re.sub(r'\d+', '#', p_)[:90]
        seen.add(key)
        if key in items and items[key].get('status') == 'open':
            items[key]['count'] = items[key].get('count', 1) + 1
            items[key]['last'] = today
            items[key]['text'] = p_
        else:
            items[key] = {'text': p_, 'first': today, 'last': today, 'count': 1, 'status': 'open'}
    for k, v in items.items():
        if v.get('status') == 'open' and k not in seen:
            v['status'] = 'fixed'
            v['fixed'] = today
    with open(items_p, 'w', encoding='utf-8') as f:
        json.dump(items, f, ensure_ascii=False, indent=1)
    open_n = sum(1 for v in items.values() if v.get('status') == 'open')
    fixed_n = sum(1 for v in items.values() if v.get('status') == 'fixed')

    md = ['# 道 · 待改进清单', '',
          '自动巡检维护，最后更新：%s' % ts.strftime('%Y-%m-%d %H:%M:%S'), '',
          '## 未解决（%d 项）' % open_n, '']
    for k, v in sorted(items.items(), key=lambda kv: kv[1].get('last', ''), reverse=True):
        if v.get('status') != 'open':
            continue
        md.append('- [ ] %s' % v['text'])
        md.append('      %s 首次 · %s 最近 · 出现 %d 次' % (v.get('first', ''), v.get('last', ''), v.get('count', 1)))
    md += ['', '## 已修复（%d 项，自动确认）' % fixed_n, '']
    for k, v in items.items():
        if v.get('status') != 'fixed':
            continue
        md.append('- [x] %s（%s 修好）' % (v['text'], v.get('fixed', '')))
    os.makedirs(os.path.join(ROOT, '巡检报告'), exist_ok=True)
    with open(os.path.join(ROOT, '巡检报告', '待改进.md'), 'w', encoding='utf-8-sig') as f:
        f.write('\n'.join(md) + '\n')

    # ---------- 11. 报告 ----------
    has_fail = any(not p.startswith('WARN') for p in problems)
    verdict = 'FAIL' if has_fail else 'PASS'
    lines = []
    lines.append('道 · 两端巡检报告')
    lines.append('时间：%s' % ts.strftime('%Y-%m-%d %H:%M:%S'))
    lines.append('')
    lines.append('【关键指标】')
    for k, v in checks.items():
        lines.append('  %-18s %s' % (k, v))
    lines.append('')
    lines.append('【形象清单】')
    for i, (f, nm) in enumerate(zip(faces, names + [''] * n_faces)):
        info = png_info(os.path.join(BUNDLE, f))
        lines.append('  %2d  %-10s %s' % (i, nm, ('%dx%d' % (info[0], info[1])) if info else '?'))
    # ---------- 能力台账（自省账本）----------
    ab_line = None
    try:
        import urllib.request
        with urllib.request.urlopen('http://127.0.0.1:8848/abil', timeout=5) as resp:
            ab_line = resp.read().decode('utf-8', 'replace').strip()
    except Exception:
        ab_line = None
    ab_vals = None
    ab_stale = 0
    ab_last_stale = ''
    ab_txt = os.path.join(ROOT, '能力台账.txt')
    if os.path.exists(ab_txt):
        try:
            with open(ab_txt, encoding='utf-8-sig') as f:
                rows = [x.strip() for x in f.read().splitlines() if x.strip()]
            if rows:
                ab_vals = [int(float(x)) for x in rows[0].split()]
            for r2 in rows[2:]:
                if '生锈' in r2:
                    ab_stale += 1
                    ab_last_stale = r2
        except Exception:
            ab_vals = None
    names7 = ['语言', '动作', '创作', '反应', '思考', '反思', '学习']
    lines.append('【能力台账】')
    if ab_line:
        lines.append('  接口 ' + ab_line)
    elif ab_vals:
        lines.append('  文件 ' + ' '.join(str(x) for x in ab_vals))
    else:
        lines.append('  读不到（能力台账未建立，或道没在跑）')
        problems.append('WARN 能力台账读不到，自省这块是盲的')
    if ab_vals and len(ab_vals) >= 7:
        low = min(range(7), key=lambda i: ab_vals[i])
        lines.append('  短板 %s=%d（下一步优先补它）' % (names7[low], ab_vals[low]))
        if ab_vals[low] < 30:
            lines.append('  提醒：短板已低于 30，制度要求先补落地再做新东西')
    if ab_stale:
        lines.append('  生锈记录 %d 条，最近一条：%s' % (ab_stale, ab_last_stale))
    lines.append('')
    music_check(lines, problems)
    joy_check(lines, problems)
    if problems:
        lines.append('【问题】')
        for p in problems:
            lines.append('  - ' + p)
    else:
        lines.append('【问题】无')
    lines.append('')
    # 2026-11-18：待改进.md 是旧账，新账以 自我状态\问题库.json 为准，这里把两份数一起报，避免看着像两套
    lib_note = ''
    try:
        with open(os.path.join(ROOT, '自我状态', '问题库.json'), encoding='utf-8-sig') as f:
            _it = json.load(f).get('问题', [])
        _open = sum(1 for i in _it if i.get('状态') in ('open', 'wait'))
        _done = sum(1 for i in _it if i.get('状态') == 'solved')
        lib_note = '；问题库未解决 %d 项 / 已解决 %d 项（自我状态\\问题库.json）' % (_open, _done)
    except Exception:
        lib_note = '；问题库读不出来'
    lines.append('【待改进】未解决 %d 项，已修复 %d 项（清单见 巡检报告\\待改进.md）%s' % (open_n, fixed_n, lib_note))
    lines.append('')
    lines.append('【结论】' + verdict)
    text = '\n'.join(lines) + '\n'

    outdir = os.path.join(ROOT, '巡检报告')
    os.makedirs(outdir, exist_ok=True)
    fn = os.path.join(outdir, '巡检_%s.txt' % ts.strftime('%Y%m%d_%H%M'))
    with open(fn, 'w', encoding='utf-8-sig') as f:
        f.write(text)

    print(text)
    print('报告已写入：' + fn)
    return 0 if not has_fail else 1

if __name__ == '__main__':
    sys.exit(main())
