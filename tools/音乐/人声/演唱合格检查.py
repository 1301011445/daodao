# -*- coding: utf-8 -*-
"""演唱合格检查（复出门槛）v0.1
用途：任何「唱」的音频在被当成品之前，必须过三关：
  D 句内动态差（dB）：每句 95 分位帧能量 - 10 分位帧能量，按句加权平均，须 >= 6.0
  V 音高微颤（占比）：长句（>=0.8s）中 f0 轨迹在 4–7Hz 调制能量明显的帧占比，须 >= 30%
  B 换气位置（占比）：句间静音（断句）落在 150–1200ms 的占比，须 >= 80%
三关全过才 PASS。语音类（朗读）本来就该 FAIL——本脚本是给「唱」用的。
用法：python 演唱合格检查.py  <音频文件...>
"""
import sys, os, math
import numpy as np
import soundfile as sf

SR_TARGET = 16000
FRAME = 0.020
HOP = 0.010
F0_MIN, F0_MAX = 80.0, 500.0


def load(path):
    try:
        y, sr = sf.read(path, dtype='float64', always_2d=False)
    except Exception as e:
        return None, None, 'READ_FAIL:%s' % e
    if y.ndim > 1:
        y = y.mean(axis=1)
    if sr != SR_TARGET:
        # 简单线性重采样
        n = int(round(len(y) * SR_TARGET / float(sr)))
        x_old = np.linspace(0, 1, len(y), endpoint=False)
        x_new = np.linspace(0, 1, n, endpoint=False)
        y = np.interp(x_new, x_old, y)
        sr = SR_TARGET
    return y, sr, ''


def frames_rms(y, sr):
    n = int(FRAME * sr)
    h = int(HOP * sr)
    if len(y) < n:
        return np.array([]), np.array([])
    rms = []
    for i in range(0, len(y) - n, h):
        seg = y[i:i + n]
        rms.append(math.sqrt(float(np.mean(seg * seg)) + 1e-12))
    return np.array(rms), h


db = lambda x: 20.0 * math.log10(max(x, 1e-9))


def split_phrases(rms_db, hop, min_sil=0.06, drop_from_peak=30.0):
    """按能量跌落切句：低于（峰值-drop）连续 >= min_sil 视为句间静音。"""
    if len(rms_db) == 0:
        return []
    peak = float(np.max(rms_db))
    thr = peak - drop_from_peak
    sil = rms_db < thr
    need = max(1, int(min_sil / hop))
    phrases = []
    s = None
    run = 0
    for i, v in enumerate(sil):
        if v:
            run += 1
            if s is not None and run >= need:
                phrases.append((s, i - run + 1))
                s = None
        else:
            run = 0
            if s is None:
                s = i
    if s is not None:
        phrases.append((s, len(sil) - 1))
    # 丢掉极短碎片
    phrases = [p for p in phrases if (p[1] - p[0]) * hop >= 0.25]
    return phrases


def f0_track(y, sr):
    n = int(FRAME * sr)
    h = int(HOP * sr)
    out = []
    for i in range(0, max(0, len(y) - n), h):
        seg = y[i:i + n] * np.hanning(n)
        # 自相关
        ac = np.correlate(seg, seg, 'full')[n - 1:]
        lo = int(sr / F0_MAX)
        hi = min(len(ac) - 1, int(sr / F0_MIN))
        if hi <= lo + 1:
            out.append(0.0)
            continue
        seg_ac = ac[lo:hi]
        k = int(np.argmax(seg_ac)) + lo
        lag = k
        strength = ac[k] / (ac[0] + 1e-12)
        if strength < 0.30:
            out.append(0.0)
        else:
            out.append(sr / float(lag))
    return np.array(out)


def vib_ratio(f0, phrases, hop, spf):
    """长句里 f0 被 4–7Hz 调制的比例：用 200ms 滑动窗，算 f0 偏离滑窗均值的符号翻转次数。"""
    long_ids = [(a, b) for a, b in phrases if (b - a) * hop >= 0.8]
    if not long_ids:
        return 0, 0
    tot = 0
    good = 0
    win = max(3, int(0.2 / hop))
    for a, b in long_ids:
        seg = f0[max(0, a - spf):min(len(f0), b + spf)]
        for i in range(0, max(1, len(seg) - win), win // 2):
            w = seg[i:i + win]
            v = w[w > 0]
            if len(v) < win * 0.6:
                continue
            tot += 1
            # 去趋势后符号翻转
            d = v - np.mean(v)
            sc = np.sign(d)
            flips = int(np.sum(np.abs(np.diff(sc)) > 0))
            rate_hz = flips / (win * hop) / 2.0
            rel = float(np.std(d) / (np.mean(v) + 1e-9))
            if 3.0 <= rate_hz <= 8.0 and rel >= 0.004:
                good += 1
    return good, tot


def check(path):
    y, sr, err = load(path)
    if y is None:
        print('FAIL|%s|%s' % (os.path.basename(path), err))
        return 'FAIL'
    if len(y) < int(1.0 * sr):
        print('FAIL|%s|太短(<1s)' % os.path.basename(path))
        return 'FAIL'
    y = y / (np.max(np.abs(y)) + 1e-12)
    rms, h = frames_rms(y, sr)
    rms_db = np.array([db(v) for v in rms])
    phrases = split_phrases(rms_db, HOP)
    if not phrases:
        print('FAIL|%s|切不出句（整段能量无起伏）' % os.path.basename(path))
        return 'FAIL'

    # D 句内动态差
    dyns = []
    peak = float(np.max(rms_db))
    for a, b in phrases:
        seg = rms_db[a:b + 1]
        seg = seg[seg > peak - 45.0]  # 句内剔除近静音帧，避免把伴奏空档算成动态
        if len(seg) < 5:
            continue
        dyns.append(np.percentile(seg, 95) - np.percentile(seg, 10))
    d_val = float(np.mean(dyns)) if dyns else 0.0

    # V 音高微颤
    f0 = f0_track(y, sr)
    spf = int(FRAME / HOP) - 1
    g, t = vib_ratio(f0, phrases, HOP, max(0, spf))
    v_val = (100.0 * g / t) if t else 0.0

    # B 换气位置
    ok = 0
    gaps = []
    for i in range(1, len(phrases)):
        gap_s = (phrases[i][0] - phrases[i - 1][1]) * HOP
        gaps.append(gap_s)
        if 0.15 <= gap_s <= 1.2:
            ok += 1
    b_val = (100.0 * ok / len(gaps)) if gaps else 0.0

    d_pass = d_val >= 6.0
    v_pass = v_val >= 30.0
    b_pass = b_val >= 80.0 and len(gaps) > 0
    overall = d_pass and v_pass and b_pass
    print('DET|%s|句数=%d|动态差=%.2fdB(%s)|微颤=%.0f%%(%s)|换气=%.0f%%(%s)|%s' % (
        os.path.basename(path), len(phrases),
        d_val, 'PASS' if d_pass else 'FAIL',
        v_val, 'PASS' if v_pass else 'FAIL',
        b_val, 'PASS' if b_pass else 'FAIL',
        'PASS' if overall else 'FAIL'))
    return 'PASS' if overall else 'FAIL'


def main():
    args = sys.argv[1:]
    if not args:
        print('用法: python 演唱合格检查.py <音频文件...>')
        return 2
    res = [check(p) for p in args]
    print('RESULT|文件=%d|PASS=%d|FAIL=%d|%s' % (
        len(res), res.count('PASS'), res.count('FAIL'),
        'PASS' if res.count('FAIL') == 0 else 'FAIL'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
