# -*- coding: utf-8 -*-
"""把 OpenUtau 逐段缓存的对齐：用旋律轮廓把每段 wav 对到工程时间轴上。
思路：工程里每个音符的音高是确定的（PENTA 五声音阶随机游走，轮廓独特），
所以先按音符搭一条「以厘分(cents)为单位」的参考曲线，再把每段 wav 估出的 F0
滑窗比对，取吻合度最高的偏移。窗口之间不重叠，天然可排序。
"""
import io
import json
import os
import re
import sys

import numpy as np
import soundfile as sf

USTX = r"F:\Daodao\OpenUtau\shiyin_v17.ustx"
CACHE = r"F:\Daodao\OpenUtau\_x\Cache"
HOP = 0.010   # 参考/实测都用 10ms 网格
WIN = 0.040   # F0 分析窗


def midi_to_cents(tone):
    return (tone - 69) * 100.0


def load_score(path):
    txt = io.open(path, encoding="utf-8").read()
    bpm = float(re.search(r"bpm:\s*([0-9.]+)", txt).group(1))
    tick = 60.0 / bpm / 480.0
    notes = []
    for m in re.finditer(r"  - position: (\d+)\n    duration: (\d+)\n    tone: (\d+)\n    lyric:", txt):
        pos, dur, tone = int(m.group(1)), int(m.group(2)), int(m.group(3))
        notes.append((pos * tick, (pos + dur) * tick, midi_to_cents(tone)))
    end = max(n[1] for n in notes)
    n_frames = int(end / HOP) + 2
    ref = np.full(n_frames, np.nan)
    for s, e, c in notes:
        i0, i1 = int(round(s / HOP)), int(round(e / HOP))
        ref[max(0, i0):max(0, i1)] = c
    return ref, end, notes


def est_f0(x, sr):
    """10ms 网格、40ms 窗的自相关基频（50–1000 Hz），返回 (f0 数组, 每帧能量)。"""
    hop = int(sr * HOP)
    win = int(sr * WIN)
    n = (len(x) - win) // hop + 1
    if n <= 0:
        return np.zeros(0), np.zeros(0)
    lo, hi = int(sr / 1000.0), int(sr / 50.0)
    f0 = np.zeros(n)
    rms = np.zeros(n)
    for i in range(n):
        seg = x[i * hop:i * hop + win]
        seg = seg - seg.mean()
        r = float(np.sqrt(np.mean(seg ** 2)))
        rms[i] = r
        if r < 1e-4:
            continue
        # FFT 自相关
        nfft = 1 << int(np.ceil(np.log2(len(seg) * 2)))
        sp = np.fft.rfft(seg, nfft)
        ac = np.fft.irfft(sp * np.conj(sp))[:len(seg)]
        ac /= (ac[0] + 1e-12)
        seg_hi = min(hi, len(ac) - 2)
        if seg_hi <= lo + 2:
            continue
        sub = ac[lo:seg_hi]
        k = int(np.argmax(sub))
        lag = lo + k
        # 抛物线细化
        if 0 < k < len(sub) - 1:
            a, b, c2 = sub[k - 1], sub[k], sub[k + 1]
            den = (a - 2 * b + c2)
            if abs(den) > 1e-9:
                lag += 0.5 * (a - c2) / den
        if lag > 0 and ac[k] > 0.25:
            f0[i] = sr / lag
    return f0, rms


def to_cents(f0):
    out = np.full(len(f0), np.nan)
    ok = f0 > 0
    out[ok] = 1200.0 * np.log2(f0[ok] / 440.0) + 1200.0 * 0  # 相对 A4 的厘分
    return out


def align(ref, ch_cents, min_overlap=18, tol=140.0):
    """返回 (最佳偏移帧, 吻合率)。ref 为 nan 处不可比。"""
    L = len(ch_cents)
    if L <= min_overlap: return None, 0.0
    best = (-1, None)
    max_off = len(ref) - min_overlap
    for off in range(0, max_off):
        seg = ref[off:min(off + L, len(ref))]
        if len(seg) < L:
            seg = np.concatenate([seg, np.full(L - len(seg), np.nan)])
        m = (~np.isnan(seg)) & (~np.isnan(ch_cents))
        cnt = int(m.sum())
        if cnt < min_overlap:
            continue
        d = np.abs(seg[m] - ch_cents[m])
        # 允许 +/-一个八度误判
        d = np.minimum(d, np.abs(d - 1200.0))
        d = np.minimum(d, np.abs(d - 2400.0))
        good = int((d < tol).sum())
        if good > best[0]:
            best = (good, off, cnt)
    if best[1] is None:
        return None, 0.0
    return best[1], best[0] / max(1, best[2])


def main():
    ref, end, notes = load_score(USTX)
    print("工程 %.2f 秒，%d 音符，参考网格 %d 帧" % (end, len(notes), len(ref)))
    parts = sorted([p for p in os.listdir(CACHE) if p.startswith("ds-") and p.endswith("steps20.wav")],
                   key=lambda p: os.path.getmtime(os.path.join(CACHE, p)))
    rows = []
    for p in parts:
        x, sr = sf.read(os.path.join(CACHE, p), dtype="float32")
        if x.ndim > 1:
            x = x.mean(axis=1)
        f0, rms = est_f0(x, sr)
        c = to_cents(f0)
        off, rate = align(ref, c)
        dur = len(x) / sr
        rows.append({"文件": p, "时长": round(dur, 2),
                     "起点": None if off is None else round(off * HOP, 2),
                     "吻合率": round(rate, 3),
                     "mtime": os.path.getmtime(os.path.join(CACHE, p))})
    rows.sort(key=lambda r: (r["起点"] if r["起点"] is not None else 9e9))
    for r in rows:
        print("%-42s %5.2fs  起点 %6s  吻合 %.2f" % (r["文件"], r["时长"],
              ("%.2f" % r["起点"]) if r["起点"] is not None else "-", r["吻合率"]))
    good = [r for r in rows if r["起点"] is not None and r["吻合率"] >= 0.55]
    good.sort(key=lambda r: r["起点"])
    cover = 0.0
    gaps = []
    for r in good:
        s, e = r["起点"], r["起点"] + r["时长"]
        if s > cover + 0.30:
            gaps.append((round(cover, 2), round(s, 2)))
        cover = max(cover, e)
    print("\n可用 %d 段，覆盖到 %.2f 秒 / 目标 %.2f 秒" % (len(good), cover, end))
    print("缺口:", gaps if gaps else "无")
    json.dump({"目标": end, "可用": good, "缺口": gaps},
              io.open(r"F:\Daodao\OpenUtau\_align.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
