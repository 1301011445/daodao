# -*- coding: utf-8 -*-
# 程序版本：v0.1 | 2026-11-22 | 基线建档（此前无版本头）
"""第35类：口型时序生成器（audio -> viseme timeline）v2

来源：Meta Oculus Lipsync 15 viseme 约定（sil/PP/FF/TH/.../aa/E/I/O/U，MPEG-4 对齐）
      Rhubarb Lip Sync 官方文档（6 基本口型 + 3 扩展，TSV 时间戳；1.4.0 起"让嘴一直在动"）
      OpenFaceFX（Cohen–Massaro dominance blending：协同发音，开口提前）
本机无 phoneme 对齐器，只做「能量包络 -> 4 档口型」这一层：
  0=sil 闭(静音) 1=A 微开(齿关) 2=C 开 3=D 大张
v2 改动（都是被 v1 真跑结果逼出来的）：
  ① 长停顿切成 ≤4 帧的小段并降一档（原来 max_hold 到 6 帧）
  ② 包络先做 3 帧滑动平均，避免毛刺把档位抖碎
  ③ 增加"重音峰"计数（清辅音不产生能量峰，故与音节数天然有偏差，判据给 ±30%）
用法：python 口型时序.py <音频> [--fps 24] [--text "句子"] [--out x.json]
"""
import sys, json, os, argparse, math
import numpy as np
import soundfile as sf

SIL_DB = -45.0
MIN_HOLD = 2
MAX_HOLD = 4
ANTICIPATE = 1


def load_mono(path):
    data, sr = sf.read(path, dtype='float32', always_2d=True)
    if data.shape[1] > 1:
        data = data.mean(axis=1, keepdims=True)
    return data[:, 0], sr


def frame_db(x, sr, fps):
    hop = max(1, int(round(sr / fps)))
    n = len(x) // hop
    out = np.empty(n, dtype=np.float32)
    for i in range(n):
        seg = x[i * hop:(i + 1) * hop]
        rms = float(np.sqrt(np.mean(seg * seg))) if len(seg) else 0.0
        out[i] = 20.0 * math.log10(max(rms, 1e-9))
    return out


def smooth(v, k=3):
    if len(v) < k:
        return v
    pad = k // 2
    p = np.pad(v, (pad, pad), mode='edge')
    return np.array([p[i:i + k].mean() for i in range(len(v))], dtype=np.float32)


def db_to_state(db):
    if db < SIL_DB:
        return 0
    amp = min(1.0, (db - SIL_DB) / 35.0)
    if amp < 0.35:
        return 1
    if amp < 0.65:
        return 2
    return 3


def runs_of(states):
    out = [[states[0], 1]]
    for v in states[1:]:
        if v == out[-1][0]:
            out[-1][1] += 1
        else:
            out.append([v, 1])
    return out


def flatten(runs):
    o = []
    for s, ln in runs:
        o.extend([s] * ln)
    return o


def split_long(s, ln):
    """把超 4 帧的语音段切成 ≤4 帧的小段，交替降档，让嘴一直在动。"""
    segs = []
    left = ln
    cur = s
    while left > 0:
        take = min(MAX_HOLD, left)
        if left - take == 1:      # 避免留下 1 帧的尾巴
            take = MAX_HOLD - 1 if MAX_HOLD - 1 >= MIN_HOLD else take
        if take < MIN_HOLD:
            take = min(left, MIN_HOLD)
        segs.append([cur, take])
        left -= take
        cur = max(1, s - 1) if cur == s else s
    return segs


def enforce(states):
    # 协同发音：开口提前 1 帧（用快照，避免一路倒推把整段静音都点亮）
    orig = list(states)
    for i in range(1, len(states)):
        if orig[i] >= 2 and orig[i - 1] <= 1:
            states[i - 1] = 2
    # 最短停留
    changed = True
    while changed:
        changed = False
        runs = runs_of(states)
        for idx, (s, ln) in enumerate(runs):
            if s >= 1 and ln < MIN_HOLD:
                if idx > 0:
                    runs[idx - 1][1] += ln
                elif idx + 1 < len(runs):
                    runs[idx + 1][1] += ln
                else:
                    runs[idx][1] = MIN_HOLD
                del runs[idx]
                states = flatten(runs)
                changed = True
                break
    # 最长停留：合并会把相邻同档段拉长，所以循环切到稳定为止
    for _ in range(8):
        out = []
        bad = False
        for s, ln in runs_of(states):
            if s >= 1 and ln > MAX_HOLD:
                bad = True
                out.extend(split_long(s, ln))
            else:
                out.append([s, ln])
        if not bad:
            break
        states = flatten(out)
    return states


def count_peaks(db_s, min_prom=2.0):
    """数包络重音峰：局部最大且左右 2 帧内起伏够 2dB。"""
    n = len(db_s)
    peaks = 0
    for i in range(2, n - 2):
        if db_s[i] < SIL_DB + 3:
            continue
        if db_s[i] > db_s[i - 1] and db_s[i] >= db_s[i + 1] and db_s[i] >= db_s[i - 2] and db_s[i] >= db_s[i + 2]:
            around = min(db_s[max(0, i - 3):i].min(), db_s[i + 1:i + 4].min())
            if db_s[i] - around >= min_prom:
                peaks += 1
    return peaks


def count_syllables(text):
    return sum(1 for ch in text if '\u4e00' <= ch <= '\u9fff')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('audio')
    ap.add_argument('--fps', type=float, default=24.0)
    ap.add_argument('--text', default='')
    ap.add_argument('--out', default='')
    a = ap.parse_args()

    x, sr = load_mono(a.audio)
    db = frame_db(x, sr, a.fps)
    db_s = smooth(db, 3)
    raw = [db_to_state(float(v)) for v in db_s]
    states = enforce(list(raw))

    onset = next((i for i, v in enumerate(db) if v >= SIL_DB), 0)   # 用未平滑的原始帧判起点
    first_open = next((i for i, v in enumerate(states) if v >= 2), -1)
    offset_ms = (first_open - onset) * 1000.0 / a.fps if first_open >= 0 else -1
    holds = [ln for s, ln in runs_of(states) if s >= 1]
    # 静音抖动：只数"真静音段"（连续 ≥3 帧低于门限）的内部，首尾 1 帧过渡允许
    sil_jitter = 0
    i = 0
    while i < len(states):
        if db_s[i] < SIL_DB:
            j = i
            while j < len(states) and db_s[j] < SIL_DB:
                j += 1
            if j - i >= 3:
                sil_jitter += sum(1 for k in range(i + 1, j - 1) if states[k] != 0)
            i = j
        else:
            i += 1
    opens = count_peaks(db_s)
    # 大声三档 vs 小声三档的平均档位（真判"嘴跟音量走"）
    talk = [i for i, v in enumerate(db_s) if v >= SIL_DB]
    if len(talk) >= 6:
        talk_db = [db_s[i] for i in talk]
        order = sorted(range(len(talk)), key=lambda k: talk_db[k])
        third = len(order) // 3
        quiet = np.mean([states[talk[k]] for k in order[:third]])
        loud = np.mean([states[talk[k]] for k in order[-third:]])
        level_gap = float(loud - quiet)
    else:
        level_gap = 0.0
    syl = count_syllables(a.text)

    metrics = {
        'fps': a.fps, 'duration': round(len(states) / a.fps, 3), 'sr': sr,
        'onset_frame': onset, 'first_open_frame': first_open,
        'offset_ms': round(offset_ms, 1),
        'min_hold': int(min(holds)) if holds else 0,
        'max_hold': int(max(holds)) if holds else 0,
        'silence_jitter': sil_jitter, 'open_count': opens, 'syllable': syl,
        'level_gap': round(level_gap, 2), 'frames': len(states),
    }
    doc = {
        'source': os.path.basename(a.audio), 'fps': a.fps,
        'duration': metrics['duration'], 'text': a.text,
        'viseme_set': ['sil', 'A', 'C', 'D'],
        'frames': states, 'amp': [round(float(v), 1) for v in db_s],
        'metrics': metrics,
    }
    out = a.out or os.path.splitext(a.audio)[0] + '.viseme.json'
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
    print('TIMELINE|frames=%d|dur=%.2fs|first_open=%.0fms|hold=%d-%d|sil_jitter=%d|peaks=%d|syl=%d|gap=%.2f|out=%s'
          % (metrics['frames'], metrics['duration'], offset_ms, metrics['min_hold'],
             metrics['max_hold'], sil_jitter, opens, syl, level_gap, out))


if __name__ == '__main__':
    main()
