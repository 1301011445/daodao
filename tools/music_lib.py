# -*- coding: utf-8 -*-
"""
道 · 音乐工具链（第一块砖）
1) 生成一个标准 MIDI 文件（SMF format 0）：古风五声音阶 8 小节旋律
2) 解析任意 SMF 成两端共用的 JSON 谱
3) 解析结果自校验（音符数 / 时长 / 音域 / 越界）

用法：
  python music_lib.py demo          # 生成示例曲 + 解析 + 自校验，落到 _bundle/music
  python music_lib.py parse <mid>   # 只解析指定 mid
"""
import json
import os
import sys
import struct

PPQ = 96
MIDI_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src', '桌面分身', '_bundle', 'music')
MIDI_DIR = os.path.normpath(MIDI_DIR)

# 五声音阶（宫商角徵羽）C4 起：C D E G A
PENTA = [60, 62, 64, 67, 69]
NOTE_NAME = {60: 'C4', 62: 'D4', 64: 'E4', 67: 'G4', 69: 'A4',
             72: 'C5', 74: 'D5', 76: 'E5', 79: 'G5', 81: 'A5',
             55: 'G3', 57: 'A3'}


def vlq(n):
    """midi 变长编码"""
    out = [n & 0x7F]
    n >>= 7
    while n:
        out.insert(0, (n & 0x7F) | 0x80)
        n >>= 7
    return bytes(out)


def write_smf(path, notes, bpm=100, ppq=PPQ):
    """notes: [(start_tick, pitch, dur_tick, vel)] -> 标准 SMF format 0"""
    events = []
    for st, pitch, dur, vel in notes:
        events.append((st, 0, bytes([0x90, pitch, vel])))          # note on
        events.append((st + dur, 1, bytes([0x80, pitch, 0])))      # note off
    events.sort(key=lambda e: (e[0], e[1]))

    track = bytearray()
    # 速度：四分音符 = 60_000_000 / bpm 微秒
    track += vlq(0) + bytes([0xFF, 0x51, 0x03]) + struct.pack('>I', int(60000000 // bpm))[1:]
    # 拍号 4/4
    track += vlq(0) + bytes([0xFF, 0x58, 0x04, 4, 2, 24, 8])
    last = 0
    for tick, _pri, ev in events:
        track += vlq(tick - last) + ev
        last = tick
    track += vlq(0) + bytes([0xFF, 0x2F, 0x00])   # end of track

    data = b'MThd' + struct.pack('>IHHH', 6, 0, 1, ppq) + b'MTrk' + struct.pack('>I', len(track)) + bytes(track)
    with open(path, 'wb') as f:
        f.write(data)
    return len(data)


def parse_smf(path):
    """解析 SMF（含 running status），返回（bpm, 音符列表）"""
    raw = open(path, 'rb').read()
    assert raw[:4] == b'MThd', '不是 MIDI 文件'
    _len, fmt, ntracks, ppq = struct.unpack('>IHHH', raw[4:14])
    pos = 14
    bpm = 120.0
    notes = []
    on = {}          # pitch -> [(start_tick, vel), ...]  同音重叠要排队，不能覆盖
    for _t in range(ntracks):
        assert raw[pos:pos + 4] == b'MTrk', '轨道头不对'
        tlen = struct.unpack('>I', raw[pos + 4:pos + 8])[0]
        p = pos + 8
        end = p + tlen
        tick = 0
        running = None
        while p < end:
            # delta
            d = 0
            while True:
                b = raw[p]
                p += 1
                d = (d << 7) | (b & 0x7F)
                if not (b & 0x80):
                    break
            tick += d
            b = raw[p]
            if b == 0xFF:                       # meta
                p += 1
                mtype = raw[p]
                p += 1
                ln = 0
                while True:
                    bb = raw[p]
                    p += 1
                    ln = (ln << 7) | (bb & 0x7F)
                    if not (bb & 0x80):
                        break
                payload = raw[p:p + ln]
                p += ln
                if mtype == 0x51 and ln == 3:
                    bpm = round(60000000 / int.from_bytes(payload, 'big'), 1)
                running = None
                continue
            if b & 0x80:
                status = b
                p += 1
                running = status
            else:
                status = running
                if status is None:
                    raise ValueError('running status 缺失')
            kind = status & 0xF0
            if kind in (0x80, 0x90):
                pitch = raw[p]
                vel = raw[p + 1]
                p += 2
                if kind == 0x90 and vel > 0:
                    on.setdefault(pitch, []).append((tick, vel))
                else:
                    q = on.get(pitch)
                    if q:
                        st, v = q.pop(0)
                        notes.append({'t': st, 'pitch': pitch, 'dur': max(1, tick - st), 'vel': v})
            elif kind in (0xA0, 0xB0, 0xE0):
                p += 2
            elif kind in (0xC0, 0xD0):
                p += 1
            else:
                raise ValueError('未知状态字节 %02X' % status)
        # 收尾：还没收到 note-off 的，补一个最短音
        for pitch, q in list(on.items()):
            for st, v in q:
                notes.append({'t': st, 'pitch': pitch, 'dur': 1, 'vel': v})
            on.pop(pitch)
        pos = end
    notes.sort(key=lambda n: n['t'])
    return bpm, notes, ppq


def to_json(title, bpm, notes, ppq):
    total = max((n['t'] + n['dur']) for n in notes) if notes else 0
    bars = int(round(total / (ppq * 4.0), 2))
    lo = min(n['pitch'] for n in notes)
    hi = max(n['pitch'] for n in notes)
    return {
        'title': title,
        'bpm': bpm,
        'ppq': ppq,
        'bars': bars,
        'durTick': total,
        'seconds': round(total / ppq * (60.0 / bpm), 2),
        'noteCount': len(notes),
        'range': '%s~%s' % (NOTE_NAME.get(lo, lo), NOTE_NAME.get(hi, hi)),
        'notes': notes,
    }


def make_demo():
    """8 小节古风旋律：主题 4 小节 + 抬高变奏 4 小节，落 2 次属音做终止感"""
    beat = PPQ
    notes = []
    # (小节, 拍, 音级, 时长拍)
    phrase = [
        (0, 0.0, 0, 0.5), (0, 0.5, 2, 0.5), (0, 1.0, 4, 1.0), (0, 2.0, 3, 0.5), (0, 2.5, 2, 1.5),
        (1, 0.0, 0, 0.5), (1, 0.5, 0, 0.5), (1, 1.0, 1, 1.0), (1, 2.0, 0, 2.0),
        (2, 0.0, 2, 0.5), (2, 0.5, 3, 0.5), (2, 1.0, 4, 1.0), (2, 2.0, 4, 0.5), (2, 2.5, 3, 1.5),
        (3, 0.0, 2, 1.0), (3, 1.0, 1, 1.0), (3, 2.0, 0, 2.0),
    ]
    phrase2 = [
        (4, 0.0, 2, 0.5), (4, 0.5, 4, 0.5), (4, 1.0, 7, 1.0), (4, 2.0, 5, 0.5), (4, 2.5, 4, 1.5),
        (5, 0.0, 2, 0.5), (5, 0.5, 2, 0.5), (5, 1.0, 4, 1.0), (5, 2.0, 2, 2.0),
        (6, 0.0, 4, 0.5), (6, 0.5, 5, 0.5), (6, 1.0, 7, 1.0), (6, 2.0, 7, 0.5), (6, 2.5, 5, 1.5),
        (7, 0.0, 4, 1.0), (7, 1.0, 2, 1.0), (7, 2.0, 0, 2.0),
    ]
    for bar, b, deg, durn in phrase + phrase2:
        pitch = PENTA[deg] if deg < len(PENTA) else PENTA[deg - 5] + 12
        start = int((bar * 4 + b) * beat)
        notes.append((start, pitch, int(durn * beat), 96))
    return notes


def render_wav(json_path, wav_path, rate=22050, gain=0.55):
    """把 JSON 谱渲染成能听的 wav：正弦基频 + 二倍泛音 + 淡入淡出包络"""
    import math
    import wave
    obj = json.load(open(json_path, encoding='utf-8'))
    bpm, ppq = obj['bpm'], obj['ppq']
    total = obj['durTick']
    seconds = total / ppq * 60.0 / bpm
    frames = int(seconds * rate) + int(0.6 * rate)
    buf = [0.0] * frames
    per_tick = 60.0 / bpm / ppq
    for n in obj['notes']:
        start = int(n['t'] * per_tick * rate)
        dur = int(n['dur'] * per_tick * rate)
        if dur <= 0:
            continue
        f0 = 440.0 * (2 ** ((n['pitch'] - 69) / 12.0))
        amp = (n['vel'] / 127.0) * gain
        fade_in = int(0.004 * rate) + 1
        for i in range(dur):
            k = start + i
            if k >= frames:
                break
            env = 1.0
            if i < fade_in:
                env = i / fade_in
            tail = dur - i
            if tail < int(0.01 * rate):
                env = min(env, tail / (0.01 * rate))
            t = i / rate
            v = math.sin(2 * math.pi * f0 * t) + 0.34 * math.sin(4 * math.pi * f0 * t)
            buf[k] += v * amp * env
    peak = max(1.0, max(abs(x) for x in buf))
    frames_out = bytearray()
    for x in buf:
        frames_out.append(int(max(-1.0, min(1.0, x / peak)) * 127 + 128))
    with wave.open(wav_path, 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(1)
        w.setframerate(rate)
        w.writeframes(bytes(frames_out))
    return seconds, os.path.getsize(wav_path)


def main():
    os.makedirs(MIDI_DIR, exist_ok=True)
    if len(sys.argv) > 1 and sys.argv[1] == 'parse':
        bpm, notes, ppq = parse_smf(sys.argv[2])
        print(json.dumps(to_json('parse', bpm, notes, ppq), ensure_ascii=False)[:400])
        return

    notes = make_demo()
    mid = os.path.join(MIDI_DIR, 'demo_01_五声主题.mid')
    size = write_smf(mid, notes, bpm=100)
    bpm, parsed, ppq = parse_smf(mid)
    obj = to_json('demo_01_五声主题（古风 · 器乐）', bpm, parsed, ppq)

    # ---- 自校验：三条硬要求 ----
    assert obj['noteCount'] == len(notes), '音符数对不上：写 %d 读 %d' % (len(notes), obj['noteCount'])
    assert abs(obj['bars'] - 8.0) < 0.01, '小节数不是 8：%s' % obj['bars']
    bad = [n for n in parsed if n['pitch'] < 48 or n['pitch'] > 84]
    assert not bad, '音域越界'
    for n in parsed:
        assert n['dur'] >= 1 and n['vel'] > 0, '有 0 时长或 0 力度音符'

    js = os.path.join(MIDI_DIR, 'demo_01_五声主题.json')
    with open(js, 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, separators=(',', ':'))
    wav = os.path.join(MIDI_DIR, 'demo_01_五声主题.wav')
    sec, wsize = render_wav(js, wav)
    print('WAV  %s  %d 字节 / %.2f 秒' % (os.path.basename(wav), wsize, sec))
    print('MID  %s  %d 字节' % (os.path.basename(mid), size))
    print('JSON %s  %d 字节' % (os.path.basename(js), os.path.getsize(js)))
    print('音符 %d 个 / %s 小节 / %.2f 秒 / %s / %s BPM' % (
        obj['noteCount'], obj['bars'], obj['seconds'], obj['range'], obj['bpm']))
    print('自校验通过（音符数、小节数、音域、时长力度）')


if __name__ == '__main__':
    main()
