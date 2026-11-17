# -*- coding: utf-8 -*-
"""和弦引擎：给一段旋律配和弦层，出 MIDI（旋律轨 + 和弦轨）和 wav 混音。
纯标准库，不依赖 numpy/sounddevice（本机没有）。

用法：
  python chord_lib.py demo          # 生成 16 小节对比样片（主歌 1645 / 副歌 4536251）
"""
import json, math, os, struct, sys, wave, random

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, '..', '和弦对比')
SR = 22050

NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

def p(name):
    """'C4' -> midi 音号"""
    pc = name[:-1]
    octv = int(name[-1])
    return 12 * (octv + 1) + NAMES.index(pc)

def chord_pitches(root, quality, octv=3):
    """根音名 + maj/min -> 三个音的音号"""
    r = p(root + str(octv))
    if quality == 'm':
        return [r, r + 3, r + 7]
    return [r, r + 4, r + 7]

# ── 和弦走位（学到的东西落在这里）────────────────────────────
# 主歌：I–vi–IV–V（主功能开场，平铺直叙）
VERSE = [('C', 'maj'), ('A', 'm'), ('F', 'maj'), ('G', 'maj')] * 2
# 副歌：IV–V–iii–vi–ii–V–I（下属开场制造冲突，4536251 收尾）
CHORUS = [('F', 'maj'), ('G', 'maj'), ('E', 'm'), ('A', 'm'),
          ('D', 'm'), ('G', 'maj'), ('C', 'maj'), ('C', 'maj')]

# ── 旋律（同一动机，副歌抬 7 半音）────────────────────────────
MOTIF = ['C4', 'D4', 'E4', 'G4']          # 主歌
MOTIF_UP = ['G4', 'A4', 'B4', 'D5']       # 副歌：同型上移纯五度

BEAT = 480   # 一拍 = 480 tick（ppq）

def build():
    """每小节 2 个旋律音、各 2 拍；和弦整小节 4 拍"""
    notes = []
    t = 0
    for bar in range(16):
        m = (MOTIF if bar < 8 else MOTIF_UP)
        for i in range(2):
            notes.append({'t': t + i * 2 * BEAT, 'pitch': p(m[i]), 'dur': 2 * BEAT, 'vel': 90, 'ch': 0})
        ch = (VERSE if bar < 8 else CHORUS)[bar % 8]
        for q in chord_pitches(ch[0], ch[1]):
            notes.append({'t': t, 'pitch': q, 'dur': 4 * BEAT, 'vel': 60, 'ch': 1})
        t += 4 * BEAT
    return notes

def write_mid(notes, ppq, path, tempo=84):
    (notes.sort(key=lambda x: (x['t'], x['ch'])))
    ev = []
    for n in notes:
        ev.append((n['t'], 0x90 | n['ch'], n['pitch'], n['vel']))
        ev.append((n['t'] + n['dur'], 0x80 | n['ch'], n['pitch'], 0))
    ev.sort(key=lambda e: (e[0], e[1]))
    trk = bytearray()
    trk += b'\x00\xff\x51\x03' + struct.pack('>I', int(round(60000000.0 / tempo)))[1:]
    last = 0
    for t, st, pi, ve in ev:
        d = t - last
        last = t
        trk += vlq(d) + bytes([st, pi, ve])
    trk += b'\x00\xff\x2f\x00'
    hdr = b'MThd' + struct.pack('>IHHH', 6, 0, 1, ppq)
    trk = b'MTrk' + struct.pack('>I', len(trk)) + bytes(trk)
    open(path, 'wb').write(hdr + trk)

def vlq(v):
    out = [v & 0x7F]
    v >>= 7
    while v:
        out.insert(0, (v & 0x7F) | 0x80)
        v >>= 7
    return bytes(out)

def render(notes, ppq, path, tempo=84):
    sec_per_tick = (60.0 / tempo) / ppq
    total = max(n['t'] + n['dur'] for n in notes)
    length = int(total * sec_per_tick * SR) + SR // 5
    buf = [0.0] * length
    for n in notes:
        f = 440.0 * (2.0 ** ((n['pitch'] - 69) / 12.0))
        st = int(n['t'] * sec_per_tick * SR)
        ln = int(n['dur'] * sec_per_tick * SR)
        amp = (0.30 if n['ch'] == 0 else 0.11) * (n['vel'] / 127.0)
        for i in range(ln):
            if st + i >= length:
                break
            tsec = i / float(SR)
            env = min(1.0, i / 200.0) * min(1.0, (ln - i) / 400.0)
            s = math.sin(2 * math.pi * f * tsec) + 0.28 * math.sin(4 * math.pi * f * tsec)
            buf[st + i] += amp * env * s
    peak = max(1e-9, max(abs(x) for x in buf))
    g = 0.92 / peak if peak > 1 else 1.0
    w = wave.open(path, 'wb')
    w.setnchannels(1)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes(b''.join(struct.pack('<h', int(max(-1, min(1, x * g)) * 32767)) for x in buf))
    w.close()
    return length / float(SR)

def parse(path):
    """读回自己写的 MIDI（只认 running status 关闭的简单轨道）"""
    d = open(path, 'rb').read()
    ppq = struct.unpack('>H', d[12:14])[0]
    i = 14
    notes = []
    while i < len(d):
        assert d[i:i + 4] == b'MTrk'
        ln = struct.unpack('>I', d[i + 4:i + 8])[0]
        body = d[i + 8:i + 8 + ln]
        j = 0
        t = 0
        on = {}
        while j < len(body):
            dlt = 0
            while True:
                b = body[j]; j += 1
                dlt = (dlt << 7) | (b & 0x7F)
                if not b & 0x80:
                    break
            t += dlt
            st = body[j]; j += 1
            if st == 0xFF:
                j += 1
                meta_len = body[j]; j += 1 + meta_len
                continue
            pi = body[j]; ve = body[j + 1]; j += 2
            ch = st & 0x0F
            if st & 0xF0 == 0x90 and ve > 0:
                on[(ch, pi)] = t
            else:
                if (ch, pi) in on:
                    st0 = on.pop((ch, pi))
                    notes.append({'t': st0, 'dur': t - st0, 'pitch': pi, 'ch': ch})
        i += 8 + ln
    return ppq, sorted(notes, key=lambda n: (n['t'], n['ch']))

def cmd_demo():
    os.makedirs(OUT, exist_ok=True)
    ppq = 480
    ns = build()
    mid = os.path.join(OUT, '和弦对比.mid')
    js = os.path.join(OUT, '和弦对比.json')
    wav = os.path.join(OUT, '和弦对比.wav')
    write_mid(ns, ppq, mid)
    sec = render(ns, ppq, wav)
    json.dump({'ppq': ppq, 'tempo': 84, 'beatsPerBar': 4,
               'chords': [c[0] + ('m' if c[1] == 'm' else '') for c in VERSE + CHORUS],
               'notes': ns}, open(js, 'w', encoding='utf-8'), ensure_ascii=False)
    print('MIDI %s %d 字节' % (mid, os.path.getsize(mid)))
    print('WAV  %s %d 字节 %.2f 秒' % (wav, os.path.getsize(wav), sec))

    # 自校验
    ppq2, back = parse(mid)
    assert ppq2 == ppq, 'ppq 不一致'
    assert len(back) == len(ns), '音符数对不上：写 %d 读回 %d' % (len(ns), len(back))
    mel = [n for n in back if n['ch'] == 0]
    chs = [n for n in back if n['ch'] == 1]
    v_hi = max(n['pitch'] for n in mel if n['t'] < 8 * 4 * BEAT)
    c_hi = max(n['pitch'] for n in mel if n['t'] >= 8 * 4 * BEAT)
    print('音符 %d（旋律 %d / 和弦 %d），旋律音区 主歌最高 %d 副歌最高 %d 差 %d 半音，和弦音 %d 个'
          % (len(back), len(mel), len(chs), v_hi, c_hi, c_hi - v_hi, len(chs)))
    assert c_hi - v_hi == 7, '副歌没按第14类规律抬 7 半音'
    assert len(chs) == 16 * 3, '和弦应该是每小节 3 个音 × 16 小节'
    print('自校验通过')

if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'demo'
    if cmd == 'demo':
        cmd_demo()
