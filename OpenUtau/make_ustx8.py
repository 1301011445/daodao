# -*- coding: utf-8 -*-
"""v8：沿用 v4 可加载结构，仅改音符位置（加换气）与句尾颤音"""
import io

SRC = r"F:\Daodao\OpenUtau\shiyin.ustx"
OUT = r"F:\Daodao\OpenUtau\shiyin_v8.ustx"

raw = io.open(SRC, encoding='utf-8').read()
head = raw.split('tracks:')[0]
head = head.replace('bpm: 120', 'bpm: 112').replace('- position: 0\n  bpm: 120', '- position: 0\n  bpm: 112')

line1 = [(64, 330, '好'), (62, 330, '日'), (60, 330, '子'), (64, 330, '就'),
         (67, 330, '在'), (69, 450, '我'), (67, 330, '肩'), (63, 720, '上')]
line2 = [(62, 330, '一'), (60, 330, '步'), (62, 330, '一'), (64, 330, '寸'),
         (65, 330, '也'), (67, 330, '是'), (69, 450, '成'), (66, 960, '长')]
gap = 140

notes = []
pos = 0
for i, (t, d, l) in enumerate(line1):
    vib = 240 if i == 7 else 0
    notes.append((pos, t, d, l, vib))
    pos += d
pos += gap
for i, (t, d, l) in enumerate(line2):
    vib = 300 if i == 7 else 0
    notes.append((pos, t, d, l, vib))
    pos += d

blocks = []
for p, t, d, l, vib in notes:
    blocks.append("""  - position: %d
    duration: %d
    tone: %d
    lyric: "%s"
    pitch:
      points: []
      snap_first: false
    vibrato:
      length: %d
      period: 220
      depth: %d
      in: 40
      out: 90
      shift: 0
      drift: 20
    tuning: 0
    tildes: 0
""" % (p, d, t, l, vib, 40 if vib else 0))

body = '''tracks:
- singer: kumi_chn
  phonemizer: OpenUtau.Plugin.Builtin.ChineseCVVCPhonemizer
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
%s''' % (pos, ''.join(blocks))

io.open(OUT, 'w', encoding='utf-8', newline='\n').write(head + body)
print('written', OUT, 'ticks', pos)
