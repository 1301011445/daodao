# -*- coding: utf-8 -*-
"""词曲协同检查器：看词和曲是不是在一根绳上。
判定七条，都是能算出来的：
 R1 字数与音符数对得上（差 0 才算过）
 R2 每句至少 3/4 的音落在强拍（4/4 里第 1、3 拍）
 R3 句末字要长（≥1.5 拍）且收在强拍上（不是掉在句末弱拍）
 R4 副歌最高音必须落在句子里最实的那个字（人工标 hook 位）
 R5 全曲音域 ≤16 半音
 R6 副歌最高音 ≥ 主歌最高音 +7 半音（第 14 类）
 R7 句末字同韵（本版只报，不判，因为韵母表要人工填）

用法：python3 词曲协同.py
"""
import os, sys, importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
# 复用和弦引擎的渲染与写谱
spec = importlib.util.spec_from_file_location(
    'chord_lib', os.path.join(HERE, '..', '和弦对比', 'chord_lib.py'))
cl = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cl)

BEAT = 480
PPQ = 480
TEMPO = 84

# ── 词：故乡 · 婉转语气（说话人对自己，不说"想"字）──────────
LINES = ['屋檐落雨', '滴三十年', '路还在这', '等你回头', '路还在这']
SECTION = ['主歌', '主歌', '副歌', '副歌', '副歌']
HOOK_IDX = [None, None, 3, None, 3]   # 每句里最实的那个字（R4 用它判）

# ── 曲 v1：未协同（故意犯错，用来对照）────────────────────
V1 = [
    [(0, 2, 60), (2, 2, 62), (3, 1, 60), (4, 1, 64), (6, 1, 62), (7, 1, 60)],   # 6 音对 4 字
    [(0, 2, 62), (2, 1, 64), (3, 1, 66), (4, 1, 68), (6, 1, 66), (7, 1, 68)],   # 主歌顶到 68
    [(0, 2, 72), (1, 1, 74), (3, 1, 70), (5, 1, 72), (6, 1, 70), (7, 1, 68)],   # 峰值落"还"、末音弱拍
    [(0, 2, 70), (2, 1, 68), (4, 1, 66), (6, 1, 64), (7, 1, 62), (7, 0, 62)],
    [(0, 2, 72), (1, 1, 74), (3, 1, 70), (5, 1, 72), (6, 1, 70), (7, 1, 68)],
]
# ── 曲 v2：协同（字数对齐、重字落强拍、句末长音收在强拍、峰值落钩子字）
V2 = [
    [(0, 2, 60), (2, 2, 62), (4, 2, 60), (6, 2, 64)],
    [(0, 2, 62), (2, 2, 64), (4, 2, 60), (6, 2, 62)],
    [(0, 2, 72), (2, 2, 70), (4, 2, 72), (6, 2, 74)],
    [(0, 2, 72), (2, 2, 70), (4, 2, 68), (6, 2, 66)],
    [(0, 2, 72), (2, 2, 70), (4, 2, 72), (6, 2, 74)],
]

def check(mel, tag):
    print('══ %s ══' % tag)
    fails = []
    tops = []
    for i, (line, notes) in enumerate(zip(LINES, mel)):
        n = len(notes)
        strong = sum(1 for b, d, p in notes if abs(b % 2) < 1e-9)
        end_b, end_d, _ = notes[-1]
        endpos = end_b + end_d
        top = max(p for b, d, p in notes)
        tops.append((i, top))
        mark = []
        if n != len(line):
            mark.append('R1 字数%d/音符%d' % (len(line), n))
        if strong < 0.75 * n:
            mark.append('R2 强拍%.0f%%' % (strong * 100.0 / n))
        if end_d < 1.5 or abs(endpos % 2) > 1e-9:
            mark.append('R3 句末%.1f拍收在%.0f' % (end_d, endpos))
        if HOOK_IDX[i] is not None:
            hi = HOOK_IDX[i]
            if hi >= n:
                mark.append('R4 钩子下标 %d 超出音符数 %d' % (hi, n))
            else:
                hook_p = notes[hi][2]
                if hook_p != top:
                    mark.append('R4 峰值%d 没落在钩子字「%s」(该字音高%d)'
                                % (top, line[hi] if hi < len(line) else '?', hook_p))
        print('%d %s %s | 字数%d 音符%d 强拍%.0f%% 峰值%d 末音(拍%.0f 长%.1f → 结束%.0f) %s'
              % (i, SECTION[i], line, len(line), n, strong * 100.0 / n, top,
                 end_b, end_d, endpos, ('✗ ' + '、'.join(mark)) if mark else '✓'))
        fails += mark
    vmax = max(t for i, t in tops if SECTION[i] == '主歌')
    cmax = max(t for i, t in tops if SECTION[i] == '副歌')
    span = max(p for l in mel for _, _, p in l) - min(p for l in mel for _, _, p in l)
    ok6 = cmax >= vmax + 7
    print('R5 音域 %d 半音 (≤16 %s) | R6 副歌峰值 %d − 主歌峰值 %d = %d (≥7 %s)'
          % (span, '✓' if span <= 16 else '✗', cmax, vmax, cmax - vmax, '✓' if ok6 else '✗'))
    if span > 16:
        fails.append('R5 音域')
    if not ok6:
        fails.append('R6 副歌抬不够')
    print('结论：%s（%d 处不合）\n' % ('过' if not fails else '不过', len(fails)))
    return not fails

def to_notes(mel):
    out = []
    for pi, line in enumerate(mel):
        base = pi * 8 * BEAT
        for b, d, p in line:
            out.append({'t': base + int(b * BEAT), 'pitch': p, 'dur': int(d * BEAT),
                        'vel': 92, 'ch': 0})
    return out

def main():
    os.makedirs(os.path.join(HERE, 'out'), exist_ok=True)
    r1 = check(V1, 'v1 未协同')
    r2 = check(V2, 'v2 协同')
    for mel, name in [(V1, 'v1_未协同'), (V2, 'v2_协同')]:
        ns = to_notes(mel)
        mid = os.path.join(HERE, 'out', name + '.mid')
        wav = os.path.join(HERE, 'out', name + '.wav')
        cl.write_mid(ns, PPQ, mid, TEMPO)
        sec = cl.render(ns, PPQ, wav, TEMPO)
        print('%s: mid %d 字节, wav %.1f 秒 %d 字节' % (name, os.path.getsize(mid), sec, os.path.getsize(wav)))
    print('\n判定：v1 %s / v2 %s' % ('过' if r1 else '不过', '过' if r2 else '不过'))

if __name__ == '__main__':
    main()
