# -*- coding: utf-8 -*-
"""把「唱法模板」落到 OpenUtau：同一句词，按模板改气声/颤音/尾招/失谐幅度，渲两版对照"""
import io, random, sys

SRC = r"F:\Daodao\OpenUtau\shiyin.ustx"

STYLES = {
    # 王力宏：字头清、尾音直收、亮而不刺 —— 少气、颤音稍快、尾音几乎不落
    'wanglihong': dict(out=r"F:\Daodao\OpenUtau\shiyin_v13.ustx", seed=1313,
                       detune=1.0, scoop=(-7, -4), fall=(-1.2, -0.4), drift=1.0,
                       vib_depth=20, vib_period=175, vib_len=0.55,
                       bre_hi=10, bre_lo=6, dyn_hi=-18, dyn_lo=8),
    # 泰勒斯威夫特：叙事气声、尾音轻拖落 —— 多气、颤音缓、尾音落得软
    'taylor': dict(out=r"F:\Daodao\OpenUtau\shiyin_v14.ustx", seed=1414,
                   detune=1.8, scoop=(-12, -8), fall=(-6.5, -4.0), drift=2.5,
                   vib_depth=14, vib_period=210, vib_len=0.60,
                   bre_hi=32, bre_lo=18, dyn_hi=-26, dyn_lo=2),
}

line1 = [(64, 330, '好'), (62, 330, '日'), (60, 330, '子'), (64, 330, '就'),
         (67, 330, '在'), (69, 450, '我'), (67, 330, '肩'), (63, 720, '上')]
line2 = [(62, 330, '一'), (60, 330, '步'), (62, 330, '一'), (64, 330, '寸'),
         (65, 330, '也'), (67, 330, '是'), (69, 450, '成'), (66, 960, '长')]
gap = 140
MS_PER_TICK = 1.117

name = sys.argv[1]
S = STYLES[name]
raw = io.open(SRC, encoding='utf-8').read()
head = raw.split('tracks:')[0]
head = head.replace('bpm: 120', 'bpm: 112').replace('- position: 0\n  bpm: 120', '- position: 0\n  bpm: 112')

rng = random.Random(S['seed'])
notes, pos = [], 0
for i, (t, d, l) in enumerate(line1):
    notes.append((pos, t, d, l, i)); pos += d
pos += gap
for i, (t, d, l) in enumerate(line2):
    notes.append((pos, t, d, l, 8 + i)); pos += d

blocks = []
for p, t, d, l, idx in notes:
    dur_ms = d * MS_PER_TICK
    detune = rng.uniform(-S['detune'], S['detune'])
    scooped = rng.uniform(*S['scoop'])
    fall = rng.uniform(*S['fall'])
    drift = rng.uniform(-S['drift'], S['drift'])
    pts = [
        (0.0, scooped + detune),
        (max(35.0, dur_ms * 0.10), detune),
        (max(60.0, dur_ms * 0.55), detune + drift),
        (max(80.0, dur_ms - 55), detune),
        (dur_ms, detune + fall),
    ]
    body_pts = '\n'.join(['      - x: %.1f\n        y: %.1f\n        shape: io' % (x, y) for x, y in pts])
    vib_len = int(d * S['vib_len'])
    bre = S['bre_hi'] if idx in (0, 1, 2, 8, 9, 10) else S['bre_lo']
    dyn = S['dyn_hi'] if idx in (0, 1, 2, 8, 9, 10) else S['dyn_lo']
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
      period: %d
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
""" % (p, d, t, l, body_pts, vib_len, S['vib_period'], S['vib_depth'], bre, dyn))

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

io.open(S['out'], 'w', encoding='utf-8', newline='\n').write(head + body)
print('written', S['out'], 'notes', len(notes))
