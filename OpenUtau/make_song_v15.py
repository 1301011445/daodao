# -*- coding: utf-8 -*-
"""《麦子熟的时候》试听版：原创词曲，96 BPM，C 宫五声，八句。
唱法用上一轮验证过最干净的一套（王力宏式：少气、尾音直收、起音轻上滑、逐音符失谐）。"""
import io, random

SRC = r"F:\Daodao\OpenUtau\shiyin.ustx"
OUT = r"F:\Daodao\OpenUtau\shiyin_v15.ustx"

BPM = 96
TICKS_PER_BEAT = 480
MS_PER_TICK = 60000.0 / BPM / TICKS_PER_BEAT   # 1.302 ms

# 词（每句八字）
LYRICS = [
    ("麦", "子", "黄", "了", "风", "从", "北", "边"),
    ("我", "顺", "着", "田", "埂", "走", "回", "少", "年"),
    ("那", "时", "的", "月", "亮", "比", "现", "在"),
    ("一", "盏", "灯", "照", "亮", "整", "个", "夏", "天"),
    ("如", "今", "我", "站", "讲", "台", "说", "起", "远", "方"),
    ("粉", "笔", "灰", "落", "在", "我", "的", "肩", "膀"),
    ("谁", "说", "长", "大", "是", "把", "梦", "收", "起", "来"),
    ("我", "偏", "把", "梦", "种", "进", "他", "们", "心", "上"),
]

# 旋律（MIDI 音高，C 宫五声：C D E G A）
MELODY = [
    [64, 62, 60, 62, 64, 67, 69, 67],
    [64, 62, 60, 62, 60, 57, 55, 55, 55],
    [69, 67, 64, 62, 64, 67, 69, 69],
    [67, 64, 62, 60, 62, 64, 60, 60, 60],
    [64, 67, 69, 67, 64, 62, 60, 62, 67, 67],
    [64, 62, 60, 62, 64, 67, 67, 67, 67],
    [69, 69, 67, 64, 62, 64, 67, 69, 69, 69],
    [67, 64, 62, 60, 62, 60, 57, 60, 60, 60],
]

GAP = 170          # 句间换气（tick）
rng = random.Random(20261123)

notes = []
pos = 0
for li, (words, mel) in enumerate(zip(LYRICS, MELODY)):
    for i, (ch, tone) in enumerate(zip(words, mel)):
        last = (i == len(words) - 1)
        dur = 720 if last else 330
        notes.append((pos, tone, dur, ch, last))
        pos += dur
    pos += GAP

blocks = []
for p, tone, d, ch, last in notes:
    dur_ms = d * MS_PER_TICK
    detune = rng.uniform(-1.2, 1.2)
    scoop = -rng.uniform(5.0, 9.0)
    fall = -rng.uniform(1.0, 3.5) if last else -rng.uniform(0.6, 1.6)
    drift = rng.uniform(-1.6, 1.6)
    pts = [
        (0.0, scoop + detune),
        (max(35.0, dur_ms * 0.12), detune),
        (max(60.0, dur_ms * 0.55), detune + drift),
        (max(80.0, dur_ms - 55), detune),
        (dur_ms, detune + fall),
    ]
    body = '\n'.join(['      - x: %.1f\n        y: %.1f\n        shape: io' % (x, y) for x, y in pts])
    vib_len = 60 if last else int(d * 0.45)
    depth = 22 if last else 14
    bre = 10 if last else 6
    dyn = 4 if last else 10
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
      period: 180
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
""" % (p, d, tone, ch, body, vib_len, depth, bre, dyn))

raw = io.open(SRC, encoding='utf-8').read()
head = raw.split('tracks:')[0]
head = head.replace('bpm: 120', 'bpm: %d' % BPM)

body = '''tracks:
- singer: kumi_chn
  phonemizer: OpenUtau.Plugin.Builtin.ChineseCVVCPhonemizer
  renderer_settings: {}
  track_name: 麦子熟的时候
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
print('written', OUT, 'notes', len(notes), 'ticks', pos, '约 %.1f s' % (pos * MS_PER_TICK / 1000))
