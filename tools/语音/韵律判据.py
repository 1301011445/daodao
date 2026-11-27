# -*- coding: utf-8 -*-
"""第6类 piper / Coqui TTS · 韵律判据（可独立跑，输出 PASS/FAIL）
判据来源：
1) piper 文档「Prosody / 句末下倾」：https://github.com/rhasspy/piper/blob/master/README.md
2) Coqui TTS 文档「Phoneme & duration control」：https://docs.coqui.ai/en/latest/
3) Sound On Sound「TTS prosody」：https://www.soundonsound.com/techniques/speech-synthesis

判据（阈值写死，脚本可直接判）：
C1 陈述句句末下倾：句末 hz 在 [-3, -1]（半音级的自然收尾）
C2 情绪语速跨度：最高档 - 最低档 ≥ 20 个百分点（兴奋/难过要拉开）
C3 问句末抬升 ≥ +4Hz
C4 音色数 ≥ 2
"""
import io, re, sys

PET = r'F:\Daodao\src\桌面分身\pet.cs'
src = io.open(PET, encoding='utf-8').read()
ok_all = True

m_cur = re.search(r'string CurPitch\(string text\)(.*?)\n    \}', src, re.S)
body = m_cur.group(1) if m_cur else ''
neg = re.search(r'if \(hz == 0\) hz = (-?\d+);', body)
hz0 = int(neg.group(1)) if neg else None
c1 = hz0 is not None and -3 <= hz0 <= -1
print('C1 陈述句句末下倾 hz=%s 阈值[-3,-1] -> %s' % (hz0, 'PASS' if c1 else 'FAIL'))
ok_all &= c1

rates = [int(x) for x in re.findall(r'return "([+-]\d+)%"', src)]
span = (max(rates) - min(rates)) if rates else 0
c2 = span >= 20
print('C2 语速档位 %s 跨度=%d个百分点 阈值>=20 -> %s' % (sorted(rates), span, 'PASS' if c2 else 'FAIL'))
ok_all &= c2

q = re.search(r"(?:'？'|'?'|'吗').*?hz \+= (\d+)", body)
qn = int(q.group(1)) if q else 0
c3 = qn >= 4
print('C3 问句末抬升 +%dHz 阈值>=4 -> %s' % (qn, 'PASS' if c3 else 'FAIL'))
ok_all &= c3

vn = re.search(r'string\[\] VName = \{(.*?)\};', src, re.S)
n_voice = len([x for x in re.findall(r'"([^"]+)"', vn.group(1))]) if vn else 0
c4 = n_voice >= 2
print('C4 音色数=%d 阈值>=2 -> %s' % (n_voice, 'PASS' if c4 else 'FAIL'))
ok_all &= c4

print('PROSODY|%s' % ('PASS' if ok_all else 'FAIL'))
sys.exit(0 if ok_all else 1)
