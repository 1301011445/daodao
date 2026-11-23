# -*- coding: utf-8 -*-
"""生成 OpenUtau 试音工程 v3（极简音符，先求能加载）"""
import io

SRC = r"F:\Daodao\OpenUtau\shiyin.ustx"
OUT = r"F:\Daodao\OpenUtau\shiyin_v3.ustx"

raw = io.open(SRC, encoding='utf-8').read()
head = raw.split('tracks:')[0]
head = head.replace('bpm: 120', 'bpm: 112').replace('- position: 0\n  bpm: 120', '- position: 0\n  bpm: 112')

line1 = [(64, 360, '好'), (62, 360, '日'), (60, 360, '子'), (64, 360, '就'),
         (67, 360, '在'), (69, 480, '我'), (67, 360, '肩'), (64, 840, '上')]
line2 = [(62, 360, '一'), (60, 360, '步'), (62, 360, '一'), (64, 360, '寸'),
         (65, 360, '也'), (67, 360, '是'), (69, 480, '成'), (67, 1080, '长')]

notes = []
pos = 0
for t, d, l in line1 + line2:
    notes.append("""  - position: %d
    duration: %d
    tone: %d
    lyric: "%s"
""" % (pos, d, t, l))
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
%s''' % (pos, ''.join(notes))

io.open(OUT, 'w', encoding='utf-8', newline='\n').write(head + body)
print('written', OUT, 'ticks', pos)
