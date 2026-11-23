# -*- coding: utf-8 -*-
"""生成 OpenUtau 试音工程 v6（真声库演唱：加句间换气、句尾颤音、起音微滑）"""
import io

SRC = r"F:\Daodao\OpenUtau\shiyin.ustx"
OUT = r"F:\Daodao\OpenUtau\shiyin_v6.ustx"

raw = io.open(SRC, encoding='utf-8').read()
head = raw.split('tracks:')[0]
head = head.replace('bpm: 120', 'bpm: 112').replace('- position: 0\n  bpm: 120', '- position: 0\n  bpm: 112')

line1 = [(64, 330, '好'), (62, 330, '日'), (60, 330, '子'), (64, 330, '就'),
         (67, 330, '在'), (69, 450, '我'), (67, 330, '肩'), (63, 720, '上')]
gap = 120
line2 = [(62, 330, '一'), (60, 330, '步'), (62, 330, '一'), (64, 330, '寸'),
         (65, 330, '也'), (67, 330, '是'), (69, 450, '成'), (66, 960, '长')]

def note(pos, tone, dur, lyric, vib=0, points=None):
    pitch = "    pitch:\n      points: []\n      snap_first: false\n"
    if points:
        pts = '\n'.join(['      - x: %d\n        y: %d\n        shape: io' % (x, y) for x, y in points])
        pitch = "    pitch:\n      points:\n%s\n      snap_first: true\n" % pts
    return """  - position: %d
    duration: %d
    tone: %d
    lyric: "%s"
%s    vibrato:
      length: %d
      period: 220
      depth: %d
      in: 40
      out: 90
      shift: 0
      drift: 30
    tuning: 0
    tildes: 0
""" % (pos, dur, tone, lyric, pitch, vib, 45 if vib else 0)

notes = []
pos = 0
for i, (t, d, l) in enumerate(line1):
    pts = [(0, 0), (25, -18), (-90, 0)] if i % 4 == 3 else None
    notes.append(note(pos, t, d, l, vib=(240 if i == 7 else 0), points=pts))
    pos += d
pos += gap
for i, (t, d, l) in enumerate(line2):
    pts = [(0, 0), (25, -22), (-110, 0)] if i == 0 else None
    notes.append(note(pos, t, d, l, vib=(300 if i == 7 else 0), points=pts))
    pos += d

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
%s''' % (pos, ''.join(notes))

io.open(OUT, 'w', encoding='utf-8', newline='\n').write(head + body)
print('written', OUT, 'ticks', pos)
