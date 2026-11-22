# -*- coding: utf-8 -*-
# 程序版本：v0.1 | 2026-11-22 | 基线建档（此前无版本头）
"""判据检查（第二批）：把总表里标"未实现"的几条补上，拿《把好日子扛在肩上》实跑。
L1 大跳后反向级进：出现 ≥5 半音跳进，下一音必须反向且 ≤2 半音
L2 一句词内的和弦换档：一句最多 1 次（跨两个小节和弦属正常，跨三个算错）
L3 段落交界留白：进副歌前必须留出 ≥1 拍的静音（"最响之前先撤掉"）
L4 句尾押韵：同段四句末字须同韵（词表法，词表外的字报"未知"，不硬判）
"""
import importlib.util, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location('song', os.path.join(HERE, '..', '打工人歌', '打工人歌.py'))
sg = importlib.util.module_from_spec(spec); spec.loader.exec_module(sg)

BEAT = sg.BEAT
# 词表法韵母（只覆盖本歌用到的字；词表外的字报"未知"，不瞎判）
FINALS = {}
for ch in '潮饱稿好': FINALS[ch] = 'ao'
for ch in '上闯光': FINALS[ch] = 'ang'
for ch in '黄忙慌扛': FINALS[ch] = 'ang' if ch in '忙扛' else 'uang'
for ch in '凡看': FINALS[ch] = 'an'
FINALS['亮'] = 'iang'; FINALS['岗'] = 'ang'; FINALS['平'] = 'ing'
# 十三辙归并：ang / iang / uang 是一个辙（江阳），an / ian / uan 是另一个（言前）
ZHE = {'ang': '江阳', 'iang': '江阳', 'uang': '江阳', 'an': '言前', 'ian': '言前', 'uan': '言前',
       'ao': '遥条', 'ing': '中东', 'eng': '中东'}

def melody_notes(notes, t0):
    # 人声轨是 0(少年声)/4(自然声)/5(戏曲腔)，只认 ch==0 会在双音色歌里取空（2026-11-20 踩过）
    return [x for x in notes if x['ch'] in (0, 4, 5) and t0 <= x['t'] < t0 + 8 * BEAT]

def check_leap(notes, mel):
    print('═ L1 大跳后反向级进 ═')
    bad = []
    for m in mel:
        ph = sorted(melody_notes(notes, m['t']), key=lambda x: x['t'])
        ivs = [ph[i + 1]['pitch'] - ph[i]['pitch'] for i in range(len(ph) - 1)]
        for i, iv in enumerate(ivs):
            if abs(iv) >= 5:
                nxt = ivs[i + 1] if i + 1 < len(ivs) else None
                if nxt is None or (nxt > 0) == (iv > 0) or abs(nxt) > 2:
                    bad.append('%s 第%d→%d音跳%d，后面接%s' % (m['text'], i + 1, i + 2, iv,
                                                    ('无音' if nxt is None else '%+d' % nxt)))
    print('跳进违规 %d 处%s' % (len(bad), '' if not bad else '：' + '；'.join(bad)))
    return len(bad) == 0

def check_chord_per_phrase(notes, mel):
    print('═ L2 句内和弦换档 ═')
    chords = sorted([x['t'] for x in notes if x['ch'] == 1 and x['dur'] == 4 * BEAT])
    bad = 0
    for m in mel:
        lo, hi = m['t'], m['t'] + 8 * BEAT
        n = len([c for c in chords if lo <= c < hi])
        if n > 2:
            bad += 1
            print('  %s 句内换了 %d 次和弦（上限 2）' % (m['text'], n))
    print('违规 %d 句（上限：一句 2 小节可换 1 次）' % bad)
    return bad == 0

def check_gap_before_chorus(notes, mel):
    print('═ L3 进副歌前留白 ═')
    bad = 0
    for i in range(1, len(mel)):
        if mel[i]['chorus'] and not mel[i - 1]['chorus']:
            boundary = mel[i]['t']
            prev_end = max(x['t'] + x['dur'] for x in melody_notes(notes, mel[i - 1]['t']))
            gap = (boundary - prev_end) / float(BEAT)
            if gap > 8:      # 中间隔着间奏，不是"没留白"，是整段间奏在托
                print('  %s → 副歌：中间隔间奏 %.0f 小节（留白由间奏承担）✓'
                      % (mel[i - 1]['text'], gap / 4.0))
                continue
            ok = gap >= 1.0
            print('  %s → 副歌：尾部留白 %.1f 拍 %s' % (mel[i - 1]['text'], gap, '✓' if ok else '✗'))
            if not ok:
                bad += 1
    return bad == 0

def check_rhyme(mel):
    print('═ L4 句尾押韵（词表法） ═')
    ok_all = True
    for si in range(0, len(mel), 4):
        group = mel[si:si + 4]
        finals, unknown = [], 0
        for m in group:
            ch = m['text'][-1]
            f = FINALS.get(ch)
            if f is None:
                unknown += 1
            finals.append(f)
        zhes = [ZHE.get(f, '?') for f in finals if f]
        same = len(set(zhes)) == 1
        print('  段%d：韵母 %s → 辙 %s%s %s'
              % (si // 4 + 1, '/'.join(f or '?' for f in finals), '/'.join(sorted(set(zhes))),
                 ('（%d 字不在词表）' % unknown) if unknown else '', '✓' if same else '✗'))
        ok_all = ok_all and same
    return ok_all

def main():
    notes, mel = sg.build()[:2]
    r1 = check_leap(notes, mel)
    r2 = check_chord_per_phrase(notes, mel)
    r3 = check_gap_before_chorus(notes, mel)
    r4 = check_rhyme(mel)
    print('\n汇总：L1 %s | L2 %s | L3 %s | L4 %s'
          % tuple('过' if x else '不过' for x in (r1, r2, r3, r4)))
    print('（L4 只看词表内可判的字；词表外的报"?"，不硬判）')

if __name__ == '__main__':
    main()
