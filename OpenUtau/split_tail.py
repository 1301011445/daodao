# -*- coding: utf-8 -*-
"""把 shiyin_ds15.ustx 的后半段拆成独立工程，分段渲染，避免一次长播放崩掉。

真实格式（OpenUtau 0.1.576 写出的 YAML，CRLF）：
    tracks:
    - singer: xxx
      notes:
      - position: 0
        duration: 330
        tone: 64
        lyric: "麦"
"""
import io
import re
import sys

SRC = r"F:\Daodao\OpenUtau\shiyin_ds15.ustx"
DST = r"F:\Daodao\OpenUtau\shiyin_ds15_tail.ustx"
CUT = float(sys.argv[1]) if len(sys.argv) > 1 else 27.4

txt = io.open(SRC, "rb").read().decode("utf-8").replace("\r\n", "\n")
bpm = float(re.search(r"^  bpm: ([0-9.]+)", txt, re.M).group(1))
tick_s = 60.0 / bpm / 480.0

m_notes = re.search(r"^  notes:\n", txt, re.M)
start = m_notes.end()
m_end = re.search(r"^(?!(  - position:|    )[ ])[ ]{0,2}[a-z_]+:", txt[start:], re.M)
end = start + m_end.start() if m_end else len(txt)
head, notes_txt, tail = txt[:start], txt[start:end], txt[end:]

blocks = [b for b in re.split(r"(?m)^(?=  - position:)", notes_txt) if b.strip().startswith("- position:")]
parsed = []
for b in blocks:
    mp = re.search(r"^  - position: (\d+)", b, re.M)
    md = re.search(r"^    duration: (\d+)", b, re.M)
    if mp and md:
        parsed.append((int(mp.group(1)), int(md.group(1)), b))

total = max(p + d for p, d, _ in parsed) * tick_s
kept, shift = [], None
for pos, dur, b in parsed:
    if (pos + dur) * tick_s <= CUT:
        continue
    if shift is None:
        shift = pos
    kept.append((pos, b))

print("音符 %d 个，全长 %.2fs，切点 %.2fs" % (len(parsed), total, CUT))
if not kept:
    raise SystemExit("切点之后没有音符")

out = head
for pos, b in kept:
    out += re.sub(r"^  - position: \d+", "  - position: %d" % (pos - shift), b, count=1, flags=re.M)
out += tail
out = re.sub(r"^name: .*", "name: ds15tail", out, count=1, flags=re.M)
io.open(DST, "w", encoding="utf-8", newline="\n").write(out)
print("保留 %d 个音符，原起点 %.2fs -> %s" % (len(kept), shift * tick_s, DST))
