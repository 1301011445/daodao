# -*- coding: utf-8 -*-
"""《麦子熟的时候》三分钟档（170–200 秒）：原创词曲，96 BPM，C 宫五声。
声库：绮萱 v2.7.0（DiffSinger 童声女歌手）。
结构：前奏(哼鸣) - 主歌A - 预副歌 - 副歌 - 间奏 - 主歌B - 预副歌 - 副歌 - 桥段 - 副歌 - 尾奏(哼鸣)
"""
import io
import random

SRC = r"F:\Daodao\OpenUtau\shiyin.ustx"
OUT = r"F:\Daodao\OpenUtau\shiyin_v17.ustx"

BPM = 96
TPB = 480
MS_TICK = 60000.0 / BPM / TPB

PENTA = [55, 57, 60, 62, 64, 67, 69, 72, 74]  # A G C D E G A C D（C 宫五声）

L = {
    1: "麦子黄了风从北边来",
    2: "我顺着田埂走回少年",
    3: "那时的月亮比现在亮",
    4: "一盏灯照亮整个夏天",
    5: "如今我站在讲台上",
    6: "粉笔灰落在肩上",
    7: "谁说长大是把梦收起来",
    8: "我偏把梦种进他们心上",
    9: "麦子熟的时候我想回家",
    10: "田里的风还记得我名字",
    11: "一声声喊我像喊个孩子",
    12: "我把这声音讲给他们听",
    13: "教室窗外的稻子又青了",
    14: "黑板擦擦过一年又一年",
    15: "有孩子问我远方有多远",
    16: "我说远方是你会想念的地方",
    17: "走过很多路才懂一件事",
    18: "走得再远也走不出那片田",
}

# (小节名, 行号列表)  —— 行号 None 表示哼鸣行
STRUCT = [
    ("前奏", [None, None, None, None]),
    ("主歌A", [1, 2, 3, 4]),
    ("预副歌", [5, 6, 7, 8]),
    ("副歌", [9, 10, 11, 12]),
    ("间奏", [None, None]),
    ("主歌B", [13, 14, 15, 16]),
    ("预副歌2", [5, 6, 7, 8]),
    ("副歌2", [9, 10, 11, 12]),
    ("桥段", [17, 18]),
    ("副歌3", [9, 10, 11, 12]),
    ("尾奏", [None, None, None, None]),
]

# 每段的音区与落音（五声音阶索引）
REG = {
    "前奏": (2, 4), "主歌A": (2, 1), "主歌B": (2, 1),
    "预副歌": (3, 2), "预副歌2": (3, 2),
    "副歌": (4, 4), "副歌2": (4, 4), "副歌3": (4, 4),
    "桥段": (3, 3), "间奏": (3, 4), "尾奏": (2, 1),
}

rng = random.Random(20261124)
GAP = 170


def walk_melody(n, start, end):
    """在五声音阶索引空间里从 start 走到 end，恰好 n 个音，步长限制在 ±2 内。"""
    if n == 1:
        return [start]
    seq = [start]
    for i in range(n - 1):
        left = n - 1 - i
        cur = seq[-1]
        # 需要在这 left 步内走到 end，允许的下一步范围
        lo = max(0, end - 2 * left, cur - 2)
        hi = min(len(PENTA) - 1, end + 2 * left, cur + 2)
        cand = [x for x in range(lo, hi + 1) if x != cur] or [cur]
        # 靠近结尾时向 end 收敛
        if left <= 2:
            cand = [x for x in cand if abs(x - end) <= left]
            if not cand:
                cand = [end]
        seq.append(rng.choice(cand))
    seq[-1] = end
    return seq


notes, pos, total_dur = [], 0, 0
for sec, lines in STRUCT:
    for ln in lines:
        if ln is None:
            chars = ["啦"] * 5
            durs = [700, 700, 700, 700, 900]
            mel = walk_melody(5, *REG[sec])
            last_flag = [False] * 4 + [True]
        else:
            text = L[ln]
            chars = list(text)
            n = len(chars)
            durs = [300] * n
            durs[-1] = 660
            mel = walk_melody(n, *REG[sec])
            last_flag = [False] * (n - 1) + [True]
        for ch, tone_idx, d, lf in zip(chars, mel, durs, last_flag):
            notes.append((pos, PENTA[tone_idx], d, ch, lf))
            pos += d
        pos += GAP

pos -= GAP  # 末尾不留空
total_dur = pos * MS_TICK / 1000.0
print("音符 %d 个，总长 %.1f 秒" % (len(notes), total_dur))

blocks = []
for p, tone, d, ch, last in notes:
    dur_ms = d * MS_TICK
    detune = rng.uniform(-1.2, 1.2)
    scoop = -rng.uniform(5.0, 9.0)
    fall = -rng.uniform(1.0, 3.5) if last else -rng.uniform(0.6, 1.6)
    drift = rng.uniform(-1.6, 1.6)
    pts = [(0.0, scoop + detune), (max(35.0, dur_ms * 0.12), detune),
           (max(60.0, dur_ms * 0.55), detune + drift),
           (max(80.0, dur_ms - 55), detune), (dur_ms, detune + fall)]
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

raw = io.open(SRC, encoding="utf-8").read()
head = raw.split("tracks:")[0].replace("bpm: 120", "bpm: %d" % BPM)

body = '''tracks:
- singer: qixuan
  phonemizer: OpenUtau.Core.DiffSinger.DiffSingerChinesePhonemizer
  renderer_settings: {}
  track_name: 麦子熟的时候_三分钟
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

io.open(OUT, "w", encoding="utf-8", newline="\n").write(head + body)
print("written", OUT, "约 %.1f 秒" % (pos * MS_TICK / 1000))
