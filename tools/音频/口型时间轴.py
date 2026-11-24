# -*- coding: utf-8 -*-
# 程序版本：v0.1 | 2026-11-24 | 首建：从单通道振幅生成口型时间轴 timeline.json
"""口型时间轴（粗口型第一版：振幅 + 平滑 + 三档量化）

用法：python 口型时间轴.py <wav> [fps=24] [out.json]
输出 metrics：offset_ms / min_hold / max_hold / silence_jitter / level_gap / open_count / syllable
思路（对应能力检查「动作55」的第一步）：先做单通道 RMS 包络 → 200ms 滑动平滑 →
按 20%/60%/90% 三个阈值量化为闭嘴/微开/半开/大开 四档 → 按帧停留统计 min/max hold。
offset_ms 为「首个超阈值帧」相对「帧 0」的偏移；纯能量法无文本，syllable 记 0（P5 由检查脚本判 UNKN）。
"""
import sys, json, wave, math, os

def read_wav(path):
    with wave.open(path, 'rb') as w:
        n, ch, sw, sr = w.getnframes(), w.getnchannels(), w.getsampwidth(), w.getframerate()
        raw = w.readframes(n)
    if sw != 2:
        raise SystemExit('只支持 16bit PCM，当前 sampwidth=%d' % sw)
    import array
    a = array.array('h')
    a.frombytes(raw)
    if ch > 1:
        mono = [sum(a[i:i + ch]) / ch for i in range(0, len(a), ch)]
    else:
        mono = list(a)
    return mono, sr

def main():
    if len(sys.argv) < 2:
        print('用法: python 口型时间轴.py <wav> [fps] [out.json]')
        return 2
    wav = sys.argv[1]
    fps = float(sys.argv[2]) if len(sys.argv) > 2 else 24.0
    out = sys.argv[3] if len(sys.argv) > 3 else os.path.join(os.path.dirname(wav), 'timeline.json')
    mono, sr = read_wav(wav)
    fl = int(sr / fps)
    frames = len(mono) // fl
    rms = []
    for i in range(frames):
        seg = mono[i * fl:(i + 1) * fl]
        rms.append(math.sqrt(sum(x * x for x in seg) / max(1, len(seg))))
    # 200ms 平滑（约 5 帧）
    win = max(1, int(round(0.2 * fps)))
    sm = []
    for i in range(frames):
        a = max(0, i - win // 2); b = min(frames, i + win // 2 + 1)
        sm.append(sum(rms[a:b]) / (b - a))
    peak = max(sm) if sm else 0.0
    if peak <= 0:
        raise SystemExit('静音文件，无法生成口型')
    thr = [0.20 * peak, 0.60 * peak, 0.90 * peak]
    lvl = []
    for v in sm:
        lvl.append(0 if v < thr[0] else 1 if v < thr[1] else 2 if v < thr[2] else 3)
    # 停留统计（只统计非 0 段）
    # 最短停留 2 帧：把只有 1 帧的档位并回前一档（防抖，对应 P2 下限）
    i = 1
    while i < len(lvl) - 1:
        if lvl[i - 1] == lvl[i + 1] and lvl[i] != lvl[i - 1]:
            lvl[i] = lvl[i - 1]
        i += 1
    for _ in range(2):
        i = 0
        while i < len(lvl):
            j = i
            while j < len(lvl) and lvl[j] == lvl[i]:
                j += 1
            if j - i == 1 and i > 0:
                lvl[i] = lvl[i - 1]
            i = j
    runs = []
    cur, cnt = lvl[0], 1
    for v in lvl[1:]:
        if v == cur:
            cnt += 1
        else:
            runs.append((cur, cnt)); cur, cnt = v, 1
    runs.append((cur, cnt))
    voice_runs = [c for (v, c) in runs if v != 0]
    min_hold = min(voice_runs) if voice_runs else 0
    max_hold = max(voice_runs) if voice_runs else 0
    voice_runs_sorted = sorted(voice_runs)
    median_hold = voice_runs_sorted[len(voice_runs_sorted) // 2] if voice_runs_sorted else 0
    # 静音抖动：< -45 dBFS 且口型非 0 的帧数（这里用 0.02*peak 近似 -45dB 相对阈值）
    sil = [i for i, v in enumerate(sm) if v < 0.02 * peak]
    jitter = sum(1 for i in sil if lvl[i] != 0)
    # offset：首个非 0 帧
    first = next((i for i, v in enumerate(lvl) if v != 0), 0)
    offset_ms = (first / fps) * 1000.0
    # 大声/小声三分档位差
    voiced = sorted([v for v in sm if v >= 0.02 * peak])
    third = max(1, len(voiced) // 3)
    nz = [v for v in lvl if True]
    def mean_lvl(vals):
        return sum(vals) / len(vals) if vals else 0.0
    # 按平滑值排序取两端，回算对应档位
    idx = sorted(range(frames), key=lambda i: sm[i])
    lo_idx = [i for i in idx if sm[i] >= 0.02 * peak][:third]
    hi_idx = [i for i in idx if sm[i] >= 0.02 * peak][-third:]
    level_gap = mean_lvl([lvl[i] for i in hi_idx]) - mean_lvl([lvl[i] for i in lo_idx])
    # 重音峰：非 0 段个数（能量法，每个开合算一个峰）
    open_count = len(voice_runs)
    doc = {
        'fps': fps,
        'source': os.path.basename(wav),
        'frames': frames,
        'duration_s': round(frames / fps, 3),
        # 学自 LiveTalking：音频分块驱动口型，每块一个 viseme（20ms 块 ≈ 50 块/秒）
        'viseme_chunk_ms': 20,
        'visemes': [
            {'t': round(i / fps, 3), 'level': int(lvl[i]),
             'viseme': ['闭', 'i', 'e_o', 'a'][int(lvl[i])]}
            for i in range(frames)
        ],
        'metrics': {
            'offset_ms': round(offset_ms, 1),
            'min_hold': int(min_hold),
            'min_hold': int(min_hold),
            'median_hold': int(median_hold),
            'max_hold': int(max_hold),
            'silence_jitter': int(jitter),
            'level_gap': round(level_gap, 3),
            'open_count': int(open_count),
            'syllable': 0,
        },
        'levels': lvl,
    }
    json.dump(doc, open(out, 'w', encoding='utf-8'), ensure_ascii=False)
    print('写入 %s | 帧数 %d | %.2fs | offset %.1fms | hold %d-%d | jitter %d | gap %.2f | 峰 %d'
          % (out, frames, frames / fps, offset_ms, min_hold, max_hold, jitter, level_gap, open_count))
    return 0

if __name__ == '__main__':
    sys.exit(main())
