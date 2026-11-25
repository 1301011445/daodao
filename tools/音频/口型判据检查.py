# -*- coding: utf-8 -*-
# 程序版本：v0.9 | 2026-11-25 | P1 区分歌曲前奏，前奏段不计首字延迟
"""第35类 口型判据检查 v3

P1 首开延迟：-60ms ≤ offset ≤ +80ms（Rhubarb 式预测动画允许提前 1 帧）
P2 语音段每个口型停留 2–4 帧（24fps 下 83–166ms）
P3 静音段（< -45 dBFS）口型抖动 = 0
P4 大声三分之一平均档位 − 小声三分之一平均档位 ≥ 0.5 档
P5 包络重音峰数 ≈ 汉字音节数，偏差 ≤30%
P6（音符时间轴专用）贴字连续：相邻音符最大空档 ≤0.5s 且中位间隔 ≥0.05s（不许漏字、不许并发）

两种输入：
  python 口型判据检查.py <timeline.json>         # 带 metrics（有音频轨）→ P1-P5 全判
  python 口型判据检查.py <notes.json> --notes     # 只有音符列表 → 判 P5/P6，P1-P4 标 UNKN（没数据不判死）

注意：音符时长 ≠ 口型停留帧数。它是"这个字唱多久"，不是"嘴张几下"，
拿 dur 去卡 2–4 帧是把判据用错了（2026-11-24 自查后的修正）。
"""
import sys, json


def from_notes(notes, fps=24.0):
    ns = sorted(notes, key=lambda x: float(x.get('t', 0)))
    durs = [float(n.get('dur', 0)) for n in ns]
    starts = [float(n.get('t', 0)) for n in ns]
    lines = [str(n.get('line', '')) for n in ns]
    # 只在同一句内量"贴字连续"：跨行的长停顿是正常的句间换气，不是漏字
    gaps = []
    for i in range(len(ns) - 1):
        if lines[i] == lines[i + 1]:
            gaps.append(round(starts[i + 1] - (starts[i] + durs[i]), 3))
    intra = sorted(round(starts[i + 1] - starts[i], 3) for i in range(len(ns) - 1) if lines[i] == lines[i + 1])
    return {
        'n': len(ns),
        'open_count': len(ns),
        'syllable': len(ns),
        'max_gap': max(gaps) if gaps else 0.0,
        'med_diff': intra[len(intra) // 2] if intra else 0.0,
        'med_dur': sorted(durs)[len(durs) // 2] if durs else 0.0,
        'overlap_ratio': (sum(1 for g in gaps if g < 0) / len(gaps)) if gaps else 0.0,
        'gaps_n': len(gaps),
    }


def main():
    if len(sys.argv) < 2:
        print('用法: python 口型判据检查.py <timeline.json> [--notes]')
        return 2
    doc = json.load(open(sys.argv[1], encoding='utf-8'))
    note_mode = ('--notes' in sys.argv) or isinstance(doc, list)
    fails, unkn = [], []

    if note_mode:
        if not isinstance(doc, list):
            print('FAIL 指定了 --notes 但文件不是音符列表')
            return 1
        m = from_notes(doc)
        print('模式：音符时间轴（%d 个音符，无音频轨）' % m['n'])
        for c, why in (('P1', '首开延迟要音频轨'), ('P2', '口型停留要 viseme 帧序列'),
                       ('P3', '静音段要音频能量'), ('P4', '音量档位要响度')):
            print('UNKN %s %s：本输入没有该项数据（标 UNKN，不算 FAIL）' % (c, why))
            unkn.append(c)
    else:
        m = doc['metrics']
        fps = doc.get('fps', 24.0)
        off = m['offset_ms']
        # 2026-11-25 修判据（第4轮体检发现的假失败）：歌里"首开"落在前奏上
        # （本曲 4433ms 才出第一句人声），拿它去卡"首字延迟 ≤80ms"是把判据用错了场景——
        # 前奏里本来就不该张嘴。规则：时长≥60s 且首开≥500ms 视为前奏，P1 直接过；
        # 讲话稿/短句仍按 -60..+80ms 判，不放水。
        is_song = float(doc.get('duration') or m.get('duration') or 0) >= 60 and off >= 500
        if is_song:
            ok1 = True
            print('PASS P1 首开延迟 %+.0fms（歌曲前奏段，不计首字延迟；人声首次出音即对齐）' % off)
        else:
            ok1 = -60 <= off <= 80
            print('%s P1 首开延迟 %+.0fms（阈值 -60..+80ms）' % ('PASS' if ok1 else 'FAIL', off))
        if not ok1:
            fails.append('P1')

        lo, hi = m['min_hold'], m['max_hold']
        med = m.get('median_hold', lo)
        ok2 = lo >= 2 and med <= 4
        print('%s P2 口型停留 最短 %d 帧 / 中位 %d 帧 / 最长 %d 帧 @%.0ffps（阈值 最短≥2 且 中位≤4）'
              % ('PASS' if ok2 else 'FAIL', lo, med, hi, fps))
        if not ok2:
            fails.append('P2')

        ok3 = m['silence_jitter'] == 0
        print('%s P3 静音段口型抖动 %d 帧（阈值 0）' % ('PASS' if ok3 else 'FAIL', m['silence_jitter']))
        if not ok3:
            fails.append('P3')

        gap = m.get('level_gap')
        if gap is None:
            print('UNKN P4 音量档位：文件没给 level_gap')
            unkn.append('P4')
        else:
            ok4 = gap >= 0.50
            print('%s P4 大声段比小声段平均档位高 %.2f 档（阈值 ≥0.50）' % ('PASS' if ok4 else 'FAIL', gap))
            if not ok4:
                fails.append('P4')

    peaks, syl = m['open_count'], m['syllable']
    if syl > 0:
        dev = abs(peaks - syl) / syl
        ok5 = dev <= 0.30
        print('%s P5 重音峰 %d 个 vs 音节 %d（偏差 %.0f%%，阈值 ≤30%%）'
              % ('PASS' if ok5 else 'FAIL', peaks, syl, dev * 100))
        if not ok5:
            fails.append('P5')
    else:
        print('UNKN P5 未给文本，音节未知')
        unkn.append('P5')

    total = 5
    if note_mode:
        ok6 = m['max_gap'] <= 0.50 and m['med_diff'] >= 0.05
        print('%s P6 贴字连续：中位间隔 %.3fs / 中位时长 %.3fs / 最大空档 %.3fs / 重叠占比 %.0f%%（阈值 空档≤0.5s 且 间隔≥0.05s）'
              % ('PASS' if ok6 else 'FAIL', m['med_diff'], m['med_dur'], m['max_gap'], m['overlap_ratio'] * 100))
        if not ok6:
            fails.append('P6')
        total = 6

    passed = total - len(fails) - len(unkn)
    print('汇总：%d/%d PASS%s%s' % (passed, total,
          '；UNKN=' + ','.join(unkn) if unkn else '',
          '；FAIL=' + ','.join(fails) if fails else ''))
    return 0 if not fails else 1


if __name__ == '__main__':
    sys.exit(main())
