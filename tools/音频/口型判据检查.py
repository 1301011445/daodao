# -*- coding: utf-8 -*-
# 程序版本：v0.1 | 2026-11-22 | 基线建档（此前无版本头）
"""第35类 口型判据检查（5 条，全 PASS 才算过）v2

P1 首开延迟：-60ms ≤ offset ≤ +80ms（允许提前 1 帧开口，这是 Rhubarb 式的预测动画）
P2 语音段每个口型停留 2–4 帧（24fps 下 83–166ms）
P3 静音段（< -45 dBFS）口型抖动 = 0
P4 大声三分之一平均档位 − 小声三分之一平均档位 ≥ 0.5 档（嘴张多大跟音量走）
P5 包络重音峰数 ≈ 汉字音节数，偏差 ≤30%（能量法看不到清辅音，天生偏低，故放宽到 30%）

用法：python 口型判据检查.py <timeline.json>
"""
import sys, json


def main():
    if len(sys.argv) < 2:
        print('用法: python 口型判据检查.py <timeline.json>')
        return 2
    doc = json.load(open(sys.argv[1], encoding='utf-8'))
    m = doc['metrics']
    fps = doc.get('fps', 24.0)
    fails = []

    off = m['offset_ms']
    ok1 = -60 <= off <= 80
    print('%s P1 首开延迟 %+.0fms（阈值 -60..+80ms）' % ('PASS' if ok1 else 'FAIL', off))
    if not ok1:
        fails.append('P1')

    lo, hi = m['min_hold'], m['max_hold']
    ok2 = lo >= 2 and hi <= 4
    print('%s P2 口型停留 %d–%d 帧 @%.0ffps（阈值 2–4 帧）' % ('PASS' if ok2 else 'FAIL', lo, hi, fps))
    if not ok2:
        fails.append('P2')

    ok3 = m['silence_jitter'] == 0
    print('%s P3 静音段口型抖动 %d 帧（阈值 0）' % ('PASS' if ok3 else 'FAIL', m['silence_jitter']))
    if not ok3:
        fails.append('P3')

    gap = m.get('level_gap', 0.0)
    ok4 = gap >= 0.50
    print('%s P4 大声段比小声段平均档位高 %.2f 档（阈值 ≥0.50）' % ('PASS' if ok4 else 'FAIL', gap))
    if not ok4:
        fails.append('P4')

    peaks, syl = m['open_count'], m['syllable']
    if syl > 0:
        dev = abs(peaks - syl) / syl
        ok5 = dev <= 0.30
        print('%s P5 重音峰 %d 个 vs 音节 %d（偏差 %.0f%%，阈值 ≤30%%）' % ('PASS' if ok5 else 'FAIL', peaks, syl, dev * 100))
        if not ok5:
            fails.append('P5')
    else:
        print('UNKN P5 未给文本，音节未知（--text 填了才判）')
        fails.append('P5')

    print('汇总：%d/5 PASS%s' % (5 - len(fails), '' if not fails else '；FAIL=' + ','.join(fails)))
    return 0 if not fails else 1


if __name__ == '__main__':
    sys.exit(main())
