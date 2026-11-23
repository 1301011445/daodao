# -*- coding: utf-8 -*-
"""生成 OpenUtau 试音工程（16 字，两乐句，带起音摸高与句尾颤音）。"""
import io, re

SRC = r"F:\Daodao\OpenUtau\shiyin.ustx"
OUT = r"F:\Daodao\OpenUtau\shiyin_v2.ustx"

raw = io.open(SRC, encoding='utf-8').read()
head = raw.split('tracks:')[0]
head = head.replace('bpm: 120', 'bpm: 112')
head = head.replace('- position: 0\n  bpm: 120', '- position: 0\n  bpm: 112')

# (tone, duration_ticks, lyric, vibrato_len)
line1 = [(64, 360, '好'), (62, 360, '日'), (60, 360, '子'), (64, 360, '就'),
         (67, 360, '在'), (69, 480, '我'), (67, 360, '肩'), (64, 840, '上')]
line2 = [(62, 360, '一'), (60, 360, '步'), (62, 360, '一'), (64, 360, '寸'),
         (65, 360, '也'), (67, 360, '是'), (69, 480, '成'), (67, 1080, '长')]

def note(i, tone, dur, lyric, vib=False, dyn=0):
    pts = [
        {'x': 0, 'y': 40, 'shape': 'io'},
        {'x': 30, 'y': -10, 'shape': 'io'},
        {'x': -30, 'y': 0, 'shape': 'io'},
    ]
    vib_block = """    vibrato:
      length: %d
      period: 200
      depth: 28
      in: 40
      out: 60
      shift: 0
      drift: 0
""" % (240 if vib else 0)
    expr = """    expressions:
      dyn: %d
""" % dyn
    return """  - position: %d
    duration: %d
    tone: %d
    lyric: "%s"
    pitch:
      points:
      - x: 0
        y: 40
        shape: io
      - x: 30
        y: -12
        shape: io
      - x: -120
        y: 0
        shape: io
      snap_first: true
%s%s    tuning: 0
    tildes: 0
""" % (i, dur, tone, lyric, vib_block, expr)

notes = []
pos = 0
for idx, (t, d, l) in enumerate(line1):
    notes.append(note(pos, t, d, l, vib=(idx == 7), dyn=(-40 if idx in (0, 1, 2) else 10)))
    pos += d
for idx, (t, d, l) in enumerate(line2):
    notes.append(note(pos, t, d, l, vib=(idx == 15), dyn=(-30 if idx in (8, 9, 10) else 15)))
    pos += d

body = '''tracks:
- singer: kumi_chn
  phonemizer: Chinese CVVC Phonemizer
  renderer_settings: {}
  track_name: 声库试音
  track_color: Blue
  mute: false
  solo: false
  volume: 1
  pan: 0
  track_expressions: []
  voice_color_names:
  - ""

voice_parts:
- name: Part1
  comment: ""
  track_no: 0
  position: 0
  duration: %d
  notes:
%s  curves: []
''' % (pos, ''.join(notes))

io.open(OUT, 'w', encoding='utf-8', newline='\n').write(head + body)
print('written', OUT, 'notes', len(line1) + len(line2), 'ticks', pos)
