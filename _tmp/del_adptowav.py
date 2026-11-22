# -*- coding: utf-8 -*-
"""删掉已被 decodePcm/writeWavFile 取代的 adpToWav，避免两份解码逻辑"""
import io

P = r'F:\Daodao\src\_apk\src\com\daodao\pet\DaoBridge.java'
s = io.open(P, encoding='utf-8').read()
start = s.index('    private boolean adpToWav(')
# 从方法体第一个 { 开始配平
b0 = s.index('{', start)
depth = 0
i = b0
in_str = None
while i < len(s):
    c = s[i]
    if in_str:
        if c == '\\':
            i += 2
            continue
        if c == in_str:
            in_str = None
    elif c in '"\'"':
        in_str = c
    elif c == '{':
        depth += 1
    elif c == '}':
        depth -= 1
        if depth == 0:
            break
    i += 1
end = i + 1
# 连带后面的空行一起删
while end < len(s) and s[end] in '\r\n':
    end += 1
removed = s[start:end]
s = s[:start] + s[end:]
io.open(P, 'w', encoding='utf-8').write(s)
print('删掉 %d 字符，剩 %d 字符' % (len(removed), len(s)))
print('还剩 adpToWav 引用：', s.count('adpToWav'))
print('decodePcm 引用：', s.count('decodePcm'), ' writeWavFile 引用：', s.count('writeWavFile'), ' playPcm 引用：', s.count('playPcm'))
