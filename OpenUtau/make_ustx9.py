# -*- coding: utf-8 -*-
"""v9：在 v4 可加载结构上加 ①全程微颤 ②气声(bre) ③音量曲线(dyn)，去电音"""
import io

SRC = r"F:\Daodao\OpenUtau\shiyin.ustx"
OUT = r"F:\Daodao\OpenUtau\shiyin_v9.ustx"

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
    notes.append((pos, t, d, l, i))
    pos += d
pos += gap
for i, (t, d, l) in enumerate(line2):
    notes.append((pos, t, d, l, 8 + i))
    pos += d

blocks = []
for p, t, d, l, idx in notes:
    # 全程微颤：长度=音符 55%，小起颤
    vib_len = int(d * 0.55)
    depth = 18 if d < 400 else 26
    # 气声：弱起音多气，句中适中
    bre = 28 if idx in (0, 1, 2, 8, 9, 10) else 14
    dyn = -25 if idx in (0, 1, 2, 8, 9, 10) else 8
    blocks.append("""  - position: %d
    duration: %d
    tone: %d
    lyric: "%s"
    pitch:
      points: []
      snap_first: false
    vibrato:
      length: %d
      period: 190
      depth: %d
      in: 70
      out: 90
      shift: 0
      drift: 25
    expressions:
      bre: %d
      dyn: %d
    tuning: 0
    tildes: 0
""" % (p, d, t, l, vib_len, depth, bre, dyn))

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
