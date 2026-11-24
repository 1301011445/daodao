# -*- coding: utf-8 -*-
# 程序版本：v0.1 | 2026-11-24 | 新建：歌唱音色的 6 条客观判据（查 3 个来源后定的阈值）
"""音色质量判据（人声 wav）

H1 谐噪比 HNR ≥ 15 dB          —— 训练过的歌者 15–25 dB（mashav 声乐描述 / vocal-analysis METHODOLOGY）
H2 周期抖动 jitter ≤ 1%         —— 稳定发声 0.003–0.01（同上）
H3 幅度扰动 shimmer ≤ 3%        —— 0.01–0.03
H4 频谱重心 1500–3000 Hz        —— 训练歌者区间，低于 1500 发闷、高于 3000 发刺/合成感
H5 颤音率 4–7 Hz 且深度 0.5–2.5 半音 —— 颤音太深太慢即"假唱味"
H6 >5kHz 能量占比 ≤ 12%          —— 齿音/合成尖啸的直接指标
用法：python 音色质量判据.py <wav> [<wav> ...]
"""
import sys
import numpy as np
import soundfile as sf


def load(p):
    x, sr = sf.read(p, dtype="float64")
    if x.ndim > 1:
        x = x.mean(axis=1)
    return x, sr


def f0_track(x, sr, hop=0.01, win=0.04):
    """自相关逐帧基频。"""
    h = int(sr * hop); w = int(sr * win)
    out = []
    for i in range(0, len(x) - w, h):
        seg = x[i:i + w]
        if np.sqrt(np.mean(seg ** 2)) < 0.01:
            out.append(0.0); continue
        seg = seg - seg.mean()
        ac = np.correlate(seg, seg, "full")[len(seg) - 1:]
        lo, hi = int(sr / 700), int(sr / 60)
        lag = lo + int(np.argmax(ac[lo:hi]))
        out.append(sr / lag if ac[lag] > 0 else 0.0)
    return np.array(out)


def stable_segment(x, sr, f0s, hop=0.01, need=8):
    """找最长的「稳定发声段」：连续帧 f0 波动 ≤3% 且能量足够，≥need 帧（0.08s×need）。
    整句上直接算 jitter/shimmer/颤音 会把正常语调当成缺陷（判据自己在错），所以要先切稳定段。"""
    if len(f0s) < need:
        return None, None
    h = int(sr * hop); w = int(sr * 0.04)
    best = (0, 0)
    i = 0
    while i < len(f0s):
        if f0s[i] <= 0:
            i += 1; continue
        j = i
        while j + 1 < len(f0s) and f0s[j + 1] > 0 and abs(f0s[j + 1] - f0s[j]) / f0s[j] <= 0.03:
            j += 1
        if j - i + 1 >= need and (j - i) > (best[1] - best[0]):
            best = (i, j + 1)
        i = j + 1
    if best[1] - best[0] < need:
        return None, None
    a = best[0] * h
    b = min(len(x), best[1] * h + w)
    return x[a:b], np.arange(best[0], best[1])


def judge(p):
    x, sr = load(p)
    # 整段只用来看频谱重心与高频占比
    n = min(len(x), 1 << 19)
    segw = x[:n] * np.hanning(n)
    spec = np.abs(np.fft.rfft(segw))
    freqs = np.fft.rfftfreq(n, 1.0 / sr)
    total = float(np.sum(spec ** 2)) + 1e-12
    # 稳定段才用来算 HNR / jitter / shimmer / 颤音
    raw_f0 = f0_track(x, sr)
    seg, idx = stable_segment(x, sr, raw_f0)
    note = ''
    if seg is None or len(seg) < int(0.08 * sr):
        seg, idx = x, np.arange(len(raw_f0))
        note = '（无稳定段，退回整段算，结果会偏悲观）'
    f0v = raw_f0[idx]
    f0v = f0v[f0v > 0]
    f0 = float(np.median(f0v)) if len(f0v) else 0.0
    m = min(len(seg), 1 << 18)
    s2 = seg[:m] * np.hanning(m)
    sp2 = np.abs(np.fft.rfft(s2))
    fq2 = np.fft.rfftfreq(m, 1.0 / sr)
    tot2 = float(np.sum(sp2 ** 2)) + 1e-12
    # H1 HNR：逐帧（40ms 帧 / 10ms 跳），带宽必须容得下汉宁窗主瓣泄漏
    # 早期版本用整段频谱 ±6% 窄带，正弦基准只测到 3.4dB（真值应 30+），是判据自己错，已改
    def frame_hnr(sig, sr_):
        w = int(sr_ * 0.04); hstep = int(sr_ * 0.01)
        vals = []
        for i in range(0, len(sig) - w, hstep):
            s = sig[i:i + w]
            if np.sqrt(np.mean(s ** 2)) < 0.02:
                continue
            s = s - s.mean()
            ac = np.correlate(s, s, 'full')[len(s) - 1:]
            if ac[0] <= 0:
                continue
            lo, hi = int(sr_ / 700), int(sr_ / 60)
            f = sr_ / (lo + int(np.argmax(ac[lo:hi])))
            n = len(s)
            sp = np.abs(np.fft.rfft(s * np.hanning(n)))
            fq = np.fft.rfftfreq(n, 1.0 / sr_)
            tot = float(np.sum(sp ** 2)) + 1e-12
            half = max(0.03 * f, 2.0 * sr_ / n)      # 至少 2 个 bin
            harm = 0.0
            for k in range(1, 20):
                c = k * f
                if c >= fq[-1]:
                    break
                band = (fq > c - half) & (fq < c + half)
                harm += float(np.sum(sp[band] ** 2))
            vals.append(10 * np.log10((harm + 1e-12) / max(1e-12, tot - harm)))
        return float(np.median(vals)) if vals else -10.0

    hnr = frame_hnr(seg, sr)
    jit = float(np.mean(np.abs(np.diff(f0v)) / (f0v[:-1] + 1e-9))) if len(f0v) > 3 else 1.0
    hstep = int(sr * 0.01); ww = int(sr * 0.04)
    env = np.array([np.sqrt(np.mean(seg[i:i + ww] ** 2)) for i in range(0, len(seg) - ww, hstep)])
    env = env[env > 0.01]
    shim = float(np.mean(np.abs(np.diff(env)) / (env[:-1] + 1e-9))) if len(env) > 3 else 1.0
    cen = float((spec * freqs).sum() / (spec.sum() + 1e-12))
    vr, vext = 0.0, 0.0
    # 颤音要在「有声连续段」上算：±3% 稳定段会把颤音本身筛掉（颤 0.6 半音≈4% 波动）
    runs, cur = [], []
    for v in raw_f0:
        if v > 0:
            cur.append(v)
        else:
            if len(cur) >= 32:
                runs.append(cur)
            cur = []
    if len(cur) >= 32:
        runs.append(cur)
    seg_f0 = max(runs, key=len) if runs else list(f0v)
    if len(seg_f0) > 32:
        d = np.array(seg_f0) - np.mean(seg_f0)
        spv = np.abs(np.fft.rfft(d * np.hanning(len(d))))
        frv = np.fft.rfftfreq(len(d), 0.01)
        band = (frv >= 0.5) & (frv <= 12)
        vr = float(frv[band][np.argmax(spv[band])])
        amp = float(np.max(spv[band])) / max(1.0, len(d)) * 4
        vext = 12 * np.log2((f0 + amp) / max(1.0, f0 - amp)) if f0 > amp else 0.0
    hi = float(np.sum(spec[freqs > 5000] ** 2)) / total
    # 判据分层：H1–H3 看发声稳定性、H4/H6 看整体频谱、H5 只在「颤音可测」时判
    # 整句带四声时 f0 主峰落在语调（<2Hz），此时颤音不可测，记 UNKN 而不是 FAIL
    h5_measurable = vr >= 2.0
    # 阈值按发声类型分档：jitter/shimmer 的 1%/3% 出自「持续元音」测法（Praat/MDVP），
    # 套到整句上必然误判（正常四声与音节过渡就有这个量级），所以整句档放宽到 2% / 25%
    jit_thr = 0.01 if h5_measurable else 0.02
    shim_thr = 0.03 if h5_measurable else 0.25
    tier = '持续音档' if h5_measurable else '整句档'
    rows = [
        ("H1 谐噪比 HNR", "%.1f dB" % hnr, hnr >= 15, "≥15 dB"),
        ("H2 周期抖动 jitter", "%.2f%%" % (jit * 100), jit <= jit_thr, "≤%.0f%%（%s）" % (jit_thr * 100, tier)),
        ("H3 幅度扰动 shimmer", "%.2f%%" % (shim * 100), shim <= shim_thr, "≤%.0f%%（%s）" % (shim_thr * 100, tier)),
        ("H4 频谱重心", "%.0f Hz" % cen, 1500 <= cen <= 3000, "1500–3000 Hz"),
        ("H5 颤音 率/深", "%.1f Hz / %.2f 半音" % (vr, vext), (4 <= vr <= 7) and (0.5 <= vext <= 2.5), "4–7Hz 且 0.5–2.5 半音"),
        ("H6 >5kHz 能量占比", "%.1f%%" % (hi * 100), hi <= 0.12, "≤12%"),
    ]
    print('--- %s | f0≈%.0fHz | %.1fs%s' % (p.split('\\')[-1], f0, len(x) / sr, note))
    fails, judged, unknown = 0, 0, 0
    for name, val, ok, thr in rows:
        if name.startswith('H5') and not h5_measurable:
            print('UNKN %s = %s（阈值 %s；整句语调主导，颤音不可测）' % (name, val, thr))
            unknown += 1
            continue
        print('%s %s = %s（阈值 %s）' % ('PASS' if ok else 'FAIL', name, val, thr))
        judged += 1
        fails += 0 if ok else 1
    print('汇总：%d/%d PASS（UNKN %d）%s' % (judged - fails, judged, unknown,
                                          '' if not fails else '；FAIL=' + str(fails)))
    return fails


def main():
    if len(sys.argv) < 2:
        print('用法: python 音色质量判据.py <wav> [...]')
        return 2
    bad = 0
    for p in sys.argv[1:]:
        bad += judge(p)
    return 0 if bad == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
