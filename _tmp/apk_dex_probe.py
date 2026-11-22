# -*- coding: utf-8 -*-
"""查已发 apk 的 dex 里到底有没有 playSongAsset / assetB64 这些桥接方法"""
import zipfile, io

APK = r'F:\Daodao\道.apk'
names = [b'playSongAsset', b'assetB64', b'stopSong', b'nowSong', b'speakCloud', b'noteAlarm', b'syncNow']
z = zipfile.ZipFile(APK)
dex = [n for n in z.namelist() if n.endswith('.dex')]
print('dex 文件:', dex)
for n in dex:
    data = z.read(n)
    print('---', n, len(data), 'bytes')
    for k in names:
        print('   %-14s %s' % (k.decode(), '有' if k in data else '没有'))
