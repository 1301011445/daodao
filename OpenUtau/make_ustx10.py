# -*- coding: utf-8 -*-
"""v10：用对了的 pitch.data 字段做真实音高曲线（起音上滑/尾音回落/微漂），去掉直线音高的电音感"""
import io, random

SRC = r"F:\Daodao\OpenUtau\shiyin.ustx"
OUT = r"F:\Daodao\OpenUtau\shiyin_v10.ustx"

raw = io.open(SRC, encoding='utf-8').read()
head = raw.split('tracks:')[0]
head = head.replace('bpm: 120', 'bpm: 112').replace('- position: 0\n  bpm: 120', '- position: 0\n  bpm: 112')

line1 = [(64, 330, '好'), (62, 330, '日'), (60, 330, '子'), (64, 330, '就'),
         (67, 330, '在'), (69, 450, '我'), (67, 330, '肩'), (63, 720, '上')]
line2 = [(62, 330, '一'), (60, 330, '步'), (62, 330, '一'), (64, 330, '寸'),
         (65, 330, '也'), (67, 330, '是'), (69, 450, '成'), (66, 960, '长')]
gap = 140
MS_PER_TICK = 1.117

rng = random.Random(20261123)
notes, pos = [], 0
for i, (t, d, l) in enumerate(line1):
    notes.append((pos, t, d, l, i)); pos += d
pos += gap
for i, (t, d, l) in enumerate(line2):
    notes.append((pos, t, d, l, 8 + i)); pos += d

blocks = []
for p, t, d, l, idx in notes:
    dur_ms = d * MS_PER_TICK
    detune = rng.uniform(-1.6, 1.6)          # 单位 0.1 半音 = ±16 音分
    scooped = rng.uniform(-11, -6)            # 起音低于音高 60–110 音分
    fall = rng.uniform(-5.5, -2.5)             # 尾音回落
    drift = rng.uniform(-1.8, 1.8)             # 句内微漂
    pts = [
        (0.0, scooped + detune),
        (max(35.0, dur_ms * 0.10), detune),
        (max(60.0, dur_ms * 0.55), detune + drift),
        (max(80.0, dur_ms - 55), detune),
        (dur_ms, detune + fall),
    ]
    body_pts = '\n'.join(['      - x: %.1f\n        y: %.1f\n        shape: io' % (x, y) for x, y in pts])
    vib_len = int(d * 0.5)
    depth = 16 if d < 400 else 24
    bre = 24 if idx in (0, 1, 2, 8, 9, 10) else 10
    dyn = -22 if idx in (0, 1, 2, 8, 9, 10) else 6
    blocks.append("""  - position: %d
    duration: %d
    tone: %d
    lyric: "%s"
    pitch:
      data:
%s
      snap_first: true
    vibrato:
      length: %d
      period: 190
      depth: %d
      in: 60
      out: 80
      shift: 0
      drift: 20
    expressions:
      bre: %d
      dyn: %d
    tuning: 0
    tildes: 0
""" % (p, d, t, l, body_pts, vib_len, depth, bre, dyn))

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
print('written', OUT, 'ticks', pos, 'notes', len(notes))
