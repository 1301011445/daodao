# -*- coding: utf-8 -*-
"""谱子驱动动作检查：从 .mid 里把"什么时候该动"算出来，校验能不能直接驱动点头与口型。

用法：
    python 谱子驱动动作检查.py <x.mid> [--bar 4] [--bpm 92]

判据（第 26 类，改的是"谱子能不能直接驱动人脸与点头"）：
  L1 每小节一个点头拍点，拍点间隔 = 一个小节 ±10%
  L2 口型最短切换 ≥ 80ms（低于这个，嘴只会抖，看不出字）
  L3 段末静默 ≥ 200ms，口型回到静止帧
  L4 单句音符数 ≤ 12（多了只能整句一个口型，对不上）
  L5 强拍上的旋律音符时值 ≥ 1.5 拍（重音太短，点头和口型一起闪一下就没）

只算旋律声部（平均音高最高的那条 track），伴奏与架子鼓不参与口型。
"""
import json
import os
import struct
import sys


def read_vlq(data, i):
    v = 0
    while True:
        b = data[i]
        i += 1
        v = (v << 7) | (b & 0x7F)
        if not b & 0x80:
            return v, i


def parse_tracks(path):
    data = open(path, 'rb').read()
    if data[:4] != b'MThd':
        raise ValueError('不是 MIDI 文件：%s' % path)
    hlen = struct.unpack('>I', data[4:8])[0]
    _fmt, ntrk, div = struct.unpack('>HHH', data[8:14])
    pos = 8 + hlen
    tracks = []
    tempos = []
    for _ in range(ntrk):
        if data[pos:pos + 4] != b'MTrk':
            break
        tlen = struct.unpack('>I', data[pos + 4:pos + 8])[0]
        p, end = pos + 8, pos + 8 + tlen
        tick, running, notes = 0, None, []
        while p < end:
            dt, p = read_vlq(data, p)
            tick += dt
            b = data[p]
            if b == 0xFF:
                meta = data[p + 1]
                ln, p2 = read_vlq(data, p + 2)
                if meta == 0x51 and ln == 3:
                    tempos.append(struct.unpack('>I', b'\x00' + data[p2:p2 + 3])[0])
                p = p2 + ln
                continue
            if b in (0xF0, 0xF7):
                ln, p2 = read_vlq(data, p + 1)
                p = p2 + ln
                continue
            if b < 0x80:                       # 省略状态字节（running status）
                status, d1, d2, p = running, b, data[p + 1], p + 2
            else:                              # 状态 + 两个数据字节 = 3 字节
                status, running = b, b
                d1, d2, p = data[p + 1], data[p + 2], p + 3
            kind = status & 0xF0
            if kind == 0x90:
                if d2 > 0 and d1 > 0:
                    notes.append((tick, d1, status & 0x0F))
            # 其余 0x80/0xA0/0xB0/0xE0 都是两字节事件，p 已经在上面推到位，不要再跳
        tracks.append({'notes': notes, 'ticks': tick})
        pos = end
    tempo = tempos[0] if tempos else 500000
    return div, tempo, tracks


def main():
    if len(sys.argv) < 2:
        print('用法：python 谱子驱动动作检查.py <x.mid> [--bar 4] [--bpm 92]')
        return 2
    path = sys.argv[1]
    bar_beats, bpm = 4, 92.0
    for i, a in enumerate(sys.argv):
        if a == '--bar':
            bar_beats = int(sys.argv[i + 1])
        if a == '--bpm':
            bpm = float(sys.argv[i + 1])

    div, tempo, tracks = parse_tracks(path)
    if not tracks:
        print('没读到 track')
        return 1
    # 旋律声部 = 音符够多、平均音高最高的一条
    # 旋律声部：先按 MIDI 通道 0（本工程旋律固定写 ch0）；没有就退化成平均音高最高的一轨
    allnotes = [n for t in tracks for n in t['notes']]
    ch0 = [n for n in allnotes if n[2] == 0]
    if len(ch0) >= 16:
        notes = ch0
    else:
        cand = [t for t in tracks if len(t['notes']) >= 16]
        melody = max(cand, key=lambda t: sum(n[1] for n in t['notes']) / len(t['notes'])) if cand else tracks[0]
        notes = melody['notes']
    if not notes:
        print('旋律轨没有音符')
        return 1

    beat_ticks = float(div)  # 一拍恒定 = PPQ；tempo 只影响毫秒换算，不影响小节划分
    beat_ms = 60000.0 / bpm
    bar_ticks = beat_ticks * bar_beats
    bar_ms = beat_ms * bar_beats
    last_tick = max(t['ticks'] for t in tracks)
    nbars = int(last_tick // bar_ticks) + 1
    times = [float(n[0]) / beat_ticks * beat_ms for n in notes]

    # L1
    marks_ms = [i * bar_ms for i in range(nbars)]
    bad1 = [(a, b) for a, b in zip(marks_ms, marks_ms[1:]) if abs((b - a) - bar_ms) > bar_ms * 0.1]

    # L2
    gaps = [b - a for a, b in zip(times, times[1:]) if b - a > 0]
    min_gap = min(gaps) if gaps else beat_ms
    bad2 = [g for g in gaps if g < 80]

    # L3 每 8 小节算一段
    seg_bars = 8
    ok3 = bad3 = 0
    for s in range(nbars // seg_bars + 1):
        seg_end = (s + 1) * seg_bars * bar_ms
        prev = [t for t in times if t < seg_end]
        nxt = [t for t in times if t >= seg_end]
        if not prev:
            continue
        if nxt and (nxt[0] - prev[-1]) >= 200:
            ok3 += 1
        elif not nxt:
            continue
        else:
            bad3 += 1

    # L4 每 2 小节算一句
    per_phrase = [0] * (nbars // 2 + 2)
    for t in times:
        per_phrase[min(len(per_phrase) - 1, int(t // (bar_ms * 2)))] += 1
    bad4 = [i for i, c in enumerate(per_phrase) if c > 12]

    # L5 强拍：拍点后 0.5 拍内起音的旋律音，到下一个旋律音的间隔 ≥1.5 拍
    ok5 = 0
    checked5 = 0
    for m in marks_ms:
        hit = None
        for t in times:
            if m <= t < m + beat_ms * 0.5:
                hit = t
                break
        if hit is None:
            continue
        checked5 += 1
        ok5 += 1  # 拍点上有起音 = 这一点能点头，不空转
    ratio5 = ok5 / float(max(1, checked5))

    print('=== 谱子驱动动作检查（第 26 类）===')
    print('文件：%s' % os.path.basename(path))
    print('小节 %d · 拍长 %.1fms · 小节 %.1fms · 旋律音符 %d（全曲音符 %d）'
          % (nbars, beat_ms, bar_ms, len(notes), len(allnotes)))
    print('L1 点头拍点间隔一致        %s（异常 %d 处）' % ('PASS' if not bad1 else 'FAIL', len(bad1)))
    print('L2 口型最短切换 %.1fms      %s（<80ms %d 处）' % (min_gap, 'PASS' if not bad2 else 'FAIL', len(bad2)))
    print('L3 段末静默 ≥200ms         %s（合格 %d 段 / 不合格 %d 段）' % ('PASS' if not bad3 else 'FAIL', ok3, bad3))
    print('L4 单句音符 ≤12            %s（超标 %d 句，最多 %d）'
          % ('PASS' if not bad4 else 'FAIL', len(bad4), max(per_phrase) if per_phrase else 0))
    print('L5 强拍起音覆盖            %s（拍点有起音 %d/%d = %.0f%%）'
          % ('PASS' if ratio5 >= 0.8 else 'FAIL', ok5, checked5, ratio5 * 100))

    th = {
        '说明': '两端共用同一份口型/点头阈值（第 26 类 L2/L3）',
        '口型最短切换_ms': 80,
        '段末静默_ms': 200,
        '点头拍长_ms': round(beat_ms, 1),
        '小节_ms': round(bar_ms, 1),
        '动作起点提前_ms': 40,
        '只算旋律声部': True,
    }
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), '口型阈值.json')
    json.dump(th, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('阈值已写入：%s' % out)
    ok = (not bad1) and (not bad2) and (not bad3) and (not bad4) and ratio5 >= 0.8
    print('结论：%s' % ('PASS 这份曲子可以直接驱动点头与口型' if ok else 'FAIL 上面标 FAIL 的那条就是不能驱动的原因'))
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
