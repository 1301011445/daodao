# -*- coding: utf-8 -*-
"""生成试唱工程：qixuan(DiffSinger) 唱《把好日子扛在肩上》副歌两句，BPM 116。"""
import io, os

SRC = r"F:\Daodao\OpenUtau\shiyin_v17.ustx"
OUT = r"F:\Daodao\OpenUtau\试唱_积极.ustx"

raw = io.open(SRC, encoding='utf-8').read()
head = raw.split('voice_parts:')[0]
head = head.replace('bpm: 96', 'bpm: 116')
head = head.replace('track_name: 麦子熟的时候_三分钟', 'track_name: 把好日子扛在肩上_试唱')
head = head.replace('- position: 0\n  bpm: 96', '- position: 0\n  bpm: 116')

L1 = [(62, 360, '好'), (64, 360, '日'), (66, 360, '子'), (68, 360, '就'),
      (65, 480, '在'), (67, 480, '我'), (70, 360, '肩'), (66, 960, '上')]
L2 = [(64, 360, '一'), (66, 360, '步'), (68, 360, '一'), (70, 480, '寸'),
      (68, 360, '也'), (66, 360, '是'), (64, 360, '成'), (62, 1080, '长')]


def note(pos, tone, dur, lyric, last=False):
    vib = ('    vibrato:\n      length: %d\n      period: 200\n      depth: 24\n      in: 40\n      out: 60\n'
           '      shift: 0\n      drift: 0\n' % (max(0, dur - 240))) if last else ''
    return ('  - position: %d\n    duration: %d\n    tone: %d\n    lyric: "%s"\n    pitch:\n'
            '      points:\n      - x: 0\n        y: 20\n        shape: io\n'
            '      - x: 60\n        y: -8\n        shape: io\n      - x: -90\n        y: 0\n        shape: io\n'
            '%s    tuning: 0\n    tildes: 0\n' % (pos, dur, tone, lyric, vib))


notes, pos = [], 0
for i, (t, d, l) in enumerate(L1):
    notes.append(note(pos, t, d, l, last=(i == 7)))
    pos += d
pos += 240
for i, (t, d, l) in enumerate(L2):
    notes.append(note(pos, t, d, l, last=(i == 15)))
    pos += d

part = ('voice_parts:\n- name: Part1\n  comment: ""\n  track_no: 0\n  position: 0\n'
        '  duration: %d\n  notes:\n' % (pos + 720)) + ''.join(notes)
io.open(OUT, 'w', encoding='utf-8').write(head + part)
print('写出', OUT, '音符', len(notes), '总长 tick', pos)
