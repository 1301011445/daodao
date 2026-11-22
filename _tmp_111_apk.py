# 2026-11-22 一次性：核对 111 包（浮窗代码在不在、权限、页面按钮、精灵图）
import zipfile, re, subprocess

APK = r'F:\Daodao\src\_apk\Dao.apk'
z = zipfile.ZipFile(APK)
names = z.namelist()
print('entries', len(names), 'dex', 'classes.dex' in names,
      z.getinfo('classes.dex').file_size if 'classes.dex' in names else 0)
print('bak', [n for n in names if n.endswith('.bak') or '.bak_' in n][:3])

h = z.read('assets/dao.html').decode('utf-8')
print('HTML_VER', re.search(r"HTML_VER\s*=\s*'(\d+)'", h).group(1))
print('btnDesk', 'id="btnDesk"' in h, '| ovPanel', 'id="ovPanel"' in h,
      '| overlayOn', 'overlayOn(' in h, '| 上桌面', '上桌面' in h)
print('old4', all(k in h for k in ['btnSwap', 'btnAct', 'btnSong', 'btnNote']),
      '| setStatus', 'function setStatus' in h, '| songDiag', 'songDiag' in h)

d = z.read('classes.dex')
for k in [b'DaoOverlay', b'overlayState', b'SYSTEM_ALERT_WINDOW', b'APPLICATION_OVERLAY',
          b'overlayOn', b'decodeFrame', b'songPos', b'songDiag']:
    print('dex', k.decode(), k in d)
print('dex bytes', len(d), '| decodePcm', b'decodePcm' in d)
print('walk8', 'assets/walk8.png' in names,
      z.getinfo('assets/walk8.png').file_size if 'assets/walk8.png' in names else 0)
print('music', [n for n in names if n.startswith('assets/music/')])

bt = r'E:\AndroidTools\sdk\build-tools\34.0.0'
r = subprocess.run([bt + r'\aapt2.exe', 'dump', 'badging', APK], capture_output=True, text=True, encoding='utf-8', errors='replace')
for line in r.stdout.splitlines():
    if line.startswith('package:') or 'launchable-activity' in line:
        print('BADGING', line)
