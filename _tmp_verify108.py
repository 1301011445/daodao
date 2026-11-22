# 程序版本：v0.1 | 2026-11-22 | 一次性：核对 0.108 两端包内容
import zipfile, re, os, hashlib

APK = r'F:\Daodao\道.apk'
EXE = r'F:\Daodao\道.exe'
z = zipfile.ZipFile(APK)
h = z.read('assets/dao.html').decode('utf-8')
print('apk 内 HTML_VER', re.search(r"HTML_VER *= *'(\d+)'", h).group(1))
print('按住说话', 'function startHold' in h, '| 面板重开', 'win = null' in h,
      '| SPR<200', 'a < 200' in h, '| 失败带字节', '读到 0 字节' in h)
print('曲库', [n for n in z.namelist() if 'music' in n])
d = z.read('classes.dex').decode('latin1')
print('dex: playPcm', 'playPcm' in d, 'assetXhr', 'assetXhr' in d)
print('apk', os.path.getsize(APK), hashlib.sha256(open(APK, 'rb').read()).hexdigest()[:16])
print('exe', os.path.getsize(EXE), hashlib.sha256(open(EXE, 'rb').read()).hexdigest()[:16])
