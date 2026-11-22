# 程序版本：v0.2 | 2026-11-22 | C14 加认 DaoOverlay/overlayState；C17 加认 btnDesk/ovPanel（手机浮窗）
"""道的「两端自用体检」。定时跑，不是只 ping：真的走一遍两端各自的入口。

用法：python 两端自用体检.py [--sound]
输出：F:\\Daodao\\巡检报告\\两端自用_YYYYMMDD_HHMM.md + 一行 SELFTEST|...
退出码：0 全过；1 有 FAIL
"""
import os, sys, json, re, socket, zipfile, urllib.request, urllib.error, subprocess, datetime, argparse

ROOT = r'F:\Daodao'
APK = os.path.join(ROOT, '道.apk')
EXE = os.path.join(ROOT, '道.exe')
PCSRC = os.path.join(ROOT, r'src\桌面分身\pet.cs')
MANIFEST = os.path.join(ROOT, r'src\_apk\AndroidManifest.xml')
LISTURL = 'https://4mf81m04wehh3.doubao.link/app/app_17hpue26uuw/'
LANDURL = 'https://4mf81m04wehh3.doubao.link/app/app_17jdxkgf27q/'
PY = sys.executable

R = []


def rec(name, ok, detail):
    R.append((name, ok, detail))
    print(('  PASS ' if ok else '  FAIL ') + name + '  ' + str(detail))


def http(path, timeout=8):
    with urllib.request.urlopen('http://127.0.0.1:8848' + path, timeout=timeout) as r:
        return r.read().decode('utf-8', 'replace')


def get_text(url, timeout=25):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode('utf-8', 'replace')


def probe_size(url, timeout=60, limit=262144):
    """短链不支持 HEAD，用 Range 取一小段，读 Content-Range 里的总字节数。"""
    req = urllib.request.Request(url, headers={'Range': 'bytes=0-1023', 'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            cr = r.headers.get('Content-Range') or ''
            m = re.search(r'/(\d+)', cr)
            if m:
                return int(m.group(1)), 'range'
            n = len(r.read(limit))
            return n, 'partial'
    except urllib.error.HTTPError as e:
        if e.code in (200, 206):
            n = len(e.read(limit))
            return n, 'http%d' % e.code
        raise


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--sound', action='store_true', help='顺带真放一下电脑端曲库（会出声）')
    args = ap.parse_args()

    print('== 两端自用体检 ' + datetime.datetime.now().strftime('%F %H:%M') + ' ==')

    # 1 电脑端在跑
    try:
        ping = http('/ping')
        ver = re.search(r'\|(\d+)\|', ping)
        appver = int(re.search(r'APP_VER\s*=\s*(\d+)', open(PCSRC, encoding='utf-8').read()).group(1))
        rec('C1 电脑端在线', ping.startswith('OK|道|'), ping.strip())
        rec('C2 电脑端版本一致', ver and int(ver.group(1)) == appver, 'ping=%s APP_VER=%d' % (ver.group(1) if ver else '?', appver))
    except Exception as e:
        appver = int(re.search(r'APP_VER\s*=\s*(\d+)', open(PCSRC, encoding='utf-8').read()).group(1))
        rec('C1 电脑端在线', False, '连不上 8848: %s' % e)
        rec('C2 电脑端版本一致', False, '无法读取 ping')

    # 2 记事本真增删一轮（自检条目，跑完删掉）
    nid = None
    try:
        slug = 'SELFTEST-' + datetime.datetime.now().strftime('%H%M%S')
        add = http('/note?op=add&text=' + urllib.parse.quote(slug) + '&when=' + urllib.parse.quote('2099-01-01 09:00'))
        rec('C3 记事本能登记', add.startswith('OK|'), add.strip())
        if add.startswith('OK|'):
            nid = add.split('|')[1]
            lst = http('/note?op=list')
            rec('C4 登记后能读到', slug in lst, '列表命中=%s' % (slug in lst))
            d = http('/note?op=del&id=' + nid)
            rec('C5 能删掉（不留垃圾）', d.startswith('OK'), d.strip())
    except Exception as e:
        rec('C3 记事本能登记', False, e)
    finally:
        if nid:
            try:
                if 'SELFTEST' in http('/note?op=list'):
                    http('/note?op=del&id=' + nid)
            except Exception:
                pass

    # 3 曲库接口 + 可选真出声
    try:
        mus = http('/music')
        cnt = re.search(r'count=(\d+)', mus)
        rec('C6 曲库可列', mus.startswith('MUS|') and cnt and int(cnt.group(1)) >= 2, mus.strip()[:80])
        if args.sound:
            p0 = http('/music?play=0')
            rec('C7 电脑端真放一首', p0.startswith('MUS|PLAY'), p0.strip()[:60])
            http('/music?stop=1')
    except Exception as e:
        rec('C6 曲库可列', False, e)

    # 4 更新链：线上清单页 / 落地页
    try:
        page = get_text(LISTURL)
        mv = re.search(r'data-ver="(\d+)"', page)
        mxe = re.search(r'data-exe="([^"]+)"', page)
        mapk = re.search(r'data-apk="([^"]+)"', page)
        rec('C8 清单页版本=本机', mv and int(mv.group(1)) == appver, '线上=%s 本机=%d' % (mv.group(1) if mv else '?', appver))
        exe_sz = os.path.getsize(EXE)
        apk_sz = os.path.getsize(APK)
        if mxe:
            n, how = probe_size(mxe.group(1))
            rec('C9 短链 exe 体积对得上', n == exe_sz, '线上=%s(%s) 本地=%d' % (n, how, exe_sz))
        if mapk:
            n, how = probe_size(mapk.group(1))
            rec('C10 短链 apk 体积对得上', n == apk_sz, '线上=%s(%s) 本地=%d' % (n, how, apk_sz))
        land = get_text(LANDURL)
        rec('C11 落地页同版本', ('data-ver="%d"' % appver) in land, '页面里 data-ver=%d?=%s' % (appver, ('data-ver="%d"' % appver) in land))
    except Exception as e:
        rec('C8 清单页版本=本机', False, e)

    # 5 apk 自身（手机端那一份）
    try:
        z = zipfile.ZipFile(APK)
        names = z.namelist()
        html = z.read('assets/dao.html').decode('utf-8', 'replace')
        dex = z.read('classes.dex').decode('latin1')
        hv = re.search(r"HTML_VER\s*=\s*'(\d+)'", html)
        rec('C12 apk 内 HTML_VER=本机', hv and int(hv.group(1)) == appver, hv.group(1) if hv else '?')
        rc = re.search(r'android:versionCode="(\d+)"', open(MANIFEST, encoding='utf-8').read())
        rec('C13 清单 versionCode=本机', rc and int(rc.group(1)) == appver, rc.group(1) if rc else '?')
        rec('C14 dex 有播放/读取/浮窗桥', all(k in dex for k in ('playSongAsset', 'decodeFrame', 'songPos', 'songDiag', 'assetXhr', 'DaoOverlay', 'overlayState')), '')
        rec('C15 三首曲库都在包里', all(('assets/music/%s.adp' % k) in names for k in ('gongzuo', 'guitu', 'shaonian')), '')
        rec('C16 包里没混进备份文件', not [n for n in names if '.bak' in n], [n for n in names if '.bak' in n])
        rec('C17 手机界面新交互在包里', ('function startHold' in html) and ('win = null' in html) and ('function setStatus' in html) and ('songDiag' in html) and ('id="btnDesk"' in html) and ('id="ovPanel"' in html), '')
    except Exception as e:
        rec('C12 apk 内 HTML_VER=本机', False, e)

    # 6 程序版本档案
    try:
        out = subprocess.run([PY, os.path.join(ROOT, 'tools', '程序版本检查.py')], capture_output=True, text=True, timeout=90).stdout
        rec('C18 程序版本档案 PASS', 'PROGVER' in out and 'PASS' in out, out.strip().splitlines()[-1] if out.strip() else '')
    except Exception as e:
        rec('C18 程序版本档案 PASS', False, e)

    ok = sum(1 for _, o, _ in R if o)
    fail = len(R) - ok
    line = 'SELFTEST|n=%d|pass=%d|fail=%d|%s' % (len(R), ok, fail, 'PASS' if fail == 0 else 'FAIL')

    # 报告
    outdir = os.path.join(ROOT, '巡检报告')
    os.makedirs(outdir, exist_ok=True)
    rp = os.path.join(outdir, '两端自用_%s.md' % datetime.datetime.now().strftime('%Y%m%d_%H%M'))
    with open(rp, 'w', encoding='utf-8') as f:
        f.write('# 两端自用体检 %s\n\n' % datetime.datetime.now().strftime('%F %H:%M'))
        for n, o, d in R:
            f.write('- %s %s  `%s`\n' % ('PASS' if o else 'FAIL', n, d))
        f.write('\n%s\n' % line)
    print(line)
    print('报告 ' + rp)
    return 0 if fail == 0 else 1


if __name__ == '__main__':
    import urllib.parse
    sys.exit(main())
