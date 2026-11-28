# -*- coding: utf-8 -*-
# DPI 对齐判据（第1类·微软 WinForms 二轮：高 DPI 缩放与 1px 对齐）
# 来源：Microsoft Learn《High DPI support in Windows Forms》、《Painting and drawing》、
#       docs《SetProcessDPIAware function》
# 判据全部从源码里数真数，不靠人工断言。
import re, sys, io, os
SRC = r'F:\Daodao\src\桌面分身\pet.cs'
if len(sys.argv) > 1:
    SRC = sys.argv[1]

txt = io.open(SRC, encoding='utf-8', errors='ignore').read()
lines = txt.split('\n')

fails = []
def chk(code, ok, msg):
    print(('PASS' if ok else 'FAIL') + ' ' + code + ' ' + msg)
    if not ok:
        fails.append(code)

# D1 DPI 感知：必须显式声明（否则系统位图拉伸，1px 线全变糊）
d1 = ('SetProcessDPIAware' in txt and re.search(r'SetProcessDPIAware\s*\(\s*\)\s*;', txt))
chk('D1', bool(d1), '进程 DPI 感知：SetProcessDPIAware() 调用 %d 处' % len(re.findall(r'SetProcessDPIAware\s*\(\s*\)\s*;', txt)))

# D2 绘制坐标吸附：只看"带偏移量"的绘制——画满整个位图的 (0,0,w,h) 天然就是整数像素，
# 需要吸附的是那些带浮点偏移、贴边、跟角色位置走的绘制；否则 1px 线在 125%/150% 下粗细不均。
blocks = []
for i, ln in enumerate(lines):
    if '.DrawImage(' not in ln:
        continue
    buf, depth = '', 0
    for k in range(i, min(i + 6, len(lines))):
        seg = lines[k]
        depth += seg.count('(') - seg.count(')')
        buf += seg
        if depth <= 0 and k > i - 1:
            break
    blocks.append(buf)
anchor_only = [b for b in blocks if re.search(r'DrawImage\s*[,(]\s*[A-Za-z0-9_.]*\w*\s*,\s*0\s*,\s*0', b)
               or 'new Rectangle(0, 0' in b or '0, 0, ' in b.split(',', 2)[-1]]
offset_draws = [b for b in blocks if b not in anchor_only]
draw = len(offset_draws)
snap = len(re.findall(r'Snap(?:X|Y|XY)\s*\(', txt))
ratio = (snap / draw) if draw else 1.0
chk('D2', ratio >= 0.80, '偏移绘制吸附覆盖率 %.1f%%（Snap 调用 %d / 带偏移 DrawImage %d，满图直画 %d 处不计，阈值 ≥80%%）' % (ratio * 100, snap, draw, len(anchor_only)))

# D3 缩放系数：必须来自真实 DPI，且不能靠硬编码倍率
src_ok = re.search(r'dpi\s*>=?\s*96', txt) or 'GetDeviceCaps' in txt or 'LOGPIXELSX' in txt
hard = len(re.findall(r'uiScale\s*=\s*[0-9.]+', txt))
chk('D3', bool(src_ok) and hard == 0, '缩放来源：读 DPI 比值（dpi/96）%s，硬编码倍率 %d 处' % ('是' if src_ok else '否', hard))

# D4 1px 线宽补偿：非 100% 缩放下 1px 描边会被抗锯齿吃掉，须有 1/scale 或 Math.Max(1,·)
d4 = bool(re.search(r'1\s*(?:f)?\s*/\s*(?:uiScale|scale)|Math\.Max\s*\(\s*1', txt))
chk('D4', d4, '细线补偿：1/scale 或 Math.Max(1,·) 处理 %s' % ('存在' if d4 else '缺失'))

# D5 自绘窗口禁止系统自动缩放（否则与手动 uiScale 双重放大，整体偏大 1.25 倍）
auto_none = 'AutoScaleMode.None' in txt
d5 = auto_none and ('(int)(W * uiScale)' in txt or '(int)(H * uiScale)' in txt)
chk('D5', d5, '缩放单点：AutoScaleMode.None %s，尺寸按 uiScale 换算 %s' % ('有' if auto_none else '无', '有' if '(int)(W * uiScale)' in txt else '无'))

print('DPIALIGN|n=5|pass=%d|fail=%d|%s' % (5 - len(fails), len(fails), 'PASS' if not fails else 'FAIL:' + ','.join(fails)))
