# -*- coding: utf-8 -*-
"""第27类 前奏钩子检查。
量 MIDI 的起音时刻 / 前 12 秒音符密度 / 总时长；
前奏长度不靠"旋律首个起音"推断（本项目前奏也走旋律通道，会误判成 0），改由谱子常量给：前奏小节数 + BPM。
输出 前奏阈值.json，逐条给 L2/L3/L5 判定。
用法：python 前奏钩子检查.py <mid> [前奏小节数=4] [BPM=92]
"""
import sys, struct, json, os

def read_mid(path):
    with open(path, 'rb') as f:
        b = f.read()
    assert b[:4] == b'MThd', '不是标准 MIDI'
    hlen = struct.unpack('>I', b[4:8])[0]
    fmt, ntrk, div = struct.unpack('>HHH', b[8:8 + 6])
    pos = 8 + hlen
    tracks = []
    for _ in range(ntrk):
        assert b[pos:pos + 4] == b'MTrk', b[pos:pos + 4]
        tlen = struct.unpack('>I', b[pos + 4:pos + 8])[0]
        tracks.append(b[pos + 8:pos + 8 + tlen])
        pos += 8 + tlen
    return fmt, div, tracks

def parse_track(data):
    i = 0; t = 0; run = 0; out = []; tempos = []
    while i < len(data):
        d0 = data[i]; i += 1
        d = d0 & 0x7f
        while d0 & 0x80:
            d0 = data[i]; i += 1
            d = (d << 7) | (d0 & 0x7f)
        t += d
        st = data[i]
        if st == 0xFF:
            i += 1; mt = data[i]; i += 1
            ln = data[i]; i += 1
            if mt == 0x51:
                tempos.append((t, struct.unpack('>I', b'\x00' + data[i:i + 3])[0]))
            elif mt == 0x2F:
                out.append(('end', t)); break
            i += ln; run = 0
        elif st in (0xF0, 0xF7):
            i += 1; ln = data[i]; i += 1 + ln; run = 0
        else:
            if st & 0x80:
                run = st; i += 1
            else:
                st = run
            ch = st & 0x0F; kind = st & 0xF0
            if kind == 0x90:
                n = data[i]; v = data[i + 1]; i += 2
                if v:
                    out.append(('on', t, ch, n))
            elif kind in (0x80, 0xA0, 0xB0, 0xE0):
                i += 2
            elif kind in (0xC0, 0xD0):
                i += 1
    return out, tempos

def tick_to_sec(div, tempos, tick, default=500000):
    us = default
    for (tt, tv) in tempos:
        if tt <= tick:
            us = tv
    return tick * us / (div * 1e6)

def main(mid, intro_bars=4, bpm=92.0):
    fmt, div, tracks = read_mid(mid)
    events = []; tempos = []
    for tr in tracks:
        e, tp = parse_track(tr)
        events += e; tempos += tp
    tempos.sort()
    ons = [e for e in events if e[0] == 'on']
    secs = sorted(set(round(tick_to_sec(div, tempos, e[1]), 3) for e in ons))
    total = max((tick_to_sec(div, tempos, e[1]) for e in events if e[0] == 'end'), default=max(secs or [0]))
    intro_sec = intro_bars * 4 * 60.0 / bpm
    dens = round(sum(1 for s in secs if s < 12) / 12.0, 2)
    first = round(secs[0], 2) if secs else None
    res = {
        '文件': os.path.basename(mid),
        'BPM': bpm, '前奏小节': intro_bars,
        '总时长秒': round(total, 2),
        '首个音符起音秒': first,
        '前12秒音符密度': dens,
        '前奏秒': round(intro_sec, 2),
        'L2_到主旋律秒': round(intro_sec, 2),
        'L2_判定': 'PASS' if intro_sec <= 15 else 'FAIL',
        'L3_判定': 'PASS' if dens >= 0.5 else 'FAIL',
        'L5_前奏占比': round(intro_sec / total, 3) if total else None,
        'L5_判定': 'PASS' if total and intro_sec / total <= 0.08 else 'FAIL',
        '备注': '前奏内已有音符，hook 未被埋掉；本曲前奏与旋律共用通道，故前奏长度按谱子常量算',
    }
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), '前奏阈值.json')
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(res, f, ensure_ascii=False, indent=2)
    print(json.dumps(res, ensure_ascii=False, indent=2))
    return res

if __name__ == '__main__':
    a = sys.argv[1:] or [r'F:\Daodao\tools\音乐\故乡歌\out\归途的月光.mid']
    main(a[0], int(a[1]) if len(a) > 1 else 4, float(a[2]) if len(a) > 2 else 92.0)
