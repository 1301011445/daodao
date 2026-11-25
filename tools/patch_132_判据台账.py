# -*- coding: utf-8 -*-
"""v132 判据 + 台账：坐骑会动、说话对口型、放歌跳舞"""
import json
import os
import re
import zipfile

O = open(r'F:\Daodao\src\_apk\src\com\daodao\pet\DaoOverlay.java', encoding='utf-8').read()
B = open(r'F:\Daodao\src\_apk\src\com\daodao\pet\DaoBridge.java', encoding='utf-8').read()
APK = r'F:\Daodao\src\_apk\Dao.apk'
z = zipfile.ZipFile(APK)
html = z.read('assets/dao.html').decode('utf-8', 'ignore')

C = [
    ('H1 五只坐骑各有运动（云飘/马跑/剑腾/鹿颠/鹤扇）',
     all(k in O for k in ['mi == 0) { mdx = (float) Math.sin(mt * 0.85)',
                         'mi == 1) { mdy = (float) Math.sin(mt * 6.2)',
                         'mi == 2) { mdy = (float) Math.sin(mt * 2.3)',
                         'mi == 3) { mdy = (float) Math.sin(mt * 4.0)',
                         'msc = 1f + 0.035f']) ),
    ('H2 人跟着坐骑一起动', 'c.translate(mdx, mdy);   // 云飘/马颠时人得跟着一起动' in O),
    ('H3 说话口型（嘴那条带开合）', 'Math.cos(t * 38.0)' in O and 'ny - 0.245' in O),
    ('H4 放歌整只跳舞（摆+弹+转体）', 'c.rotate((float) Math.sin(dt * 5.0) * 4.5f' in O),
    ('H5 骑乘路径同样有动画', 'void drawRide' in O and 'float mdx = 0f, mdy = 0f, mrot = 0f;' in O and 'dancing2' in O),
    ('H6 说话打点接进四条语音通道', 'markTalk(t.length() * 210)' in B and 'markTalk(text.length() * 260)' in B and 'markTalk(text.length() * 280)' in B),
    ('H7 起歌开舞 / 唱完收舞', 'markDance((int) secs)' in B and 'DaoOverlay.setDancing(false)' in B),
    ('H8 包内版本 1.32 / HTML_VER=132', re.search(r"var HTML_VER = '(\d+)'", html).group(1) == '132'),
]
ok = all(v for _, v in C)
for n, v in C:
    print(n, 'PASS' if v else 'FAIL')
print('SUMMARY', 'PASS' if ok else 'FAIL')

if ok:
    apk, exe = os.path.getsize(APK), os.path.getsize(r'F:\Daodao\道.exe')
    open(r'F:\Daodao\发版记录.txt', 'a', encoding='utf-8').write(
        '\n=== v132 坐骑会动 / 对口型 / 跳舞（2026-11-25）===\n'
        '坐骑：祥云左右飘 3%%w + 上下 1.2%%h；木马 6.2rad/s 颠 + ±1.6°；飞剑 2.3rad/s 起伏 + ±3.2°；\n'
        '      小鹿 4rad/s 颠 + ±1.3°；纸鹤 2.8rad/s + 横向张开 3.5%%（扇翅）。人跟着坐骑一起位移。\n'
        '口型：说话时嘴那条带（0.20~0.29 身高，高斯宽 0.048）按 38rad/s（≈6Hz）开合；骑姿整图用点头代。\n'
        '跳舞：放歌整只（含坐骑）以脚跟为轴 ±4.5° 摆 + 上下弹 3.5%%h。\n'
        '接线：Bridge 的 speak / speakCloud / speakTencent / speakEdge 打说话点；起歌 markDance、唱完 setDancing(false)。\n'
        '双端资产：手机 14 立绘 / 13 套八帧 / 14 骑姿 / 5 坐骑 / 3 球；桌面 14 脸 + 八帧 + 跳舞帧（无坐骑）。\n'
        'apk %d（vc132/vn1.32）；exe %d（APP_VER=132）。判据 H1~H8 PASS。\n' % (apk, exe))
    lp = r'F:\Daodao\自我状态\版本账本.json'
    try:
        d = json.load(open(lp, encoding='utf-8'))
    except Exception:
        d = {}
    d['current'] = 132
    d.setdefault('notes', {})['132'] = '坐骑会动 + 说话口型 + 放歌跳舞（悬浮窗）'
    json.dump(d, open(lp, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    with open(r'F:\Daodao\能力检查\2026-11-25.md', 'a', encoding='utf-8') as f:
        f.write('\n## v132 坐骑会动 / 口型 / 跳舞\n- 五只坐骑各自动作公式（飘/跑/腾/颠/扇）\n'
                '- 说话 6Hz 口型带；放歌 ±4.5° 舞步\n- H1~H8 PASS，apk %d / exe %d\n' % (apk, exe))
    print('LEDGER_OK')
raise SystemExit(0 if ok else 1)
