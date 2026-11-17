# -*- coding: utf-8 -*-
"""
道 · 原创歌 01《寄一封》
词曲一体：主歌 8 小节 + 副歌 8 小节，重复两遍，共 32 小节。
押 an/ian 韵；副歌钩子「雪落在信纸的边」7 字，重复两次。
音域 C4~E5；84 BPM，约 91 秒。
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from music_lib import write_smf, parse_smf, to_json, render_wav, MIDI_DIR, PPQ

BPM = 84
TITLE = 'song_01_寄一封'

# 每句 = 2 小节 = 8 拍；(音高, 拍长)
P1 = [(60, 1), (62, 1), (64, 2), (67, 2), (64, 2)]
P2 = [(64, 1), (62, 1), (60, 2), (62, 2), (60, 2)]
P3 = [(60, 1), (64, 1), (67, 2), (69, 2), (67, 2)]
P4 = [(69, 1), (67, 1), (64, 2), (62, 2), (60, 2)]
C5 = [(72, 2), (69, 1), (67, 1), (64, 2), (67, 2)]
C6 = [(67, 1), (69, 1), (72, 2), (74, 2), (72, 2)]
C8 = [(72, 1), (69, 1), (67, 2), (64, 2), (60, 2)]

for name, ph in [('P1', P1), ('P2', P2), ('P3', P3), ('P4', P4), ('C5', C5), ('C6', C6), ('C8', C8)]:
    assert sum(d for _p, d in ph) == 8, '%s 不是 8 拍：%s' % (name, sum(d for _p, d in ph))

# 四段：主歌 A / 副歌 / 主歌 B（抬一句）/ 副歌再现
SECTIONS = [
    ('A', [P1, P2, P3, P4]),
    ('C', [C5, C6, C5, C8]),
    ('B', [P1, P2, [(62, 1), (64, 1), (67, 2), (72, 2), (69, 2)], P4]),
    ('C', [C5, C6, C5, C8]),
]

LYRICS = {
    'A': ['灯芯挑到第三遍', '屋檐的水还没干', '旧年的话抄成篇', '落款留到明天'],
    'B': ['邮票贴得有些偏', '邮筒锈成了墨蓝', '我在这边也还安', '只有一句没说全'],
    'C': ['雪落在信纸的边', '一个字写上一整天', '雪落在信纸的边', '等你拆开已是春天'],
}


def build_notes():
    notes = []
    bar = 0
    for _tag, phrases in SECTIONS:
        for ph in phrases:
            beat_at = 0.0
            for pitch, dur in ph:
                start = int((bar * 4 + beat_at) * PPQ)
                notes.append((start, pitch, int(dur * PPQ), 96))
                beat_at += dur
            bar += 2
    return notes, bar


def main():
    os.makedirs(MIDI_DIR, exist_ok=True)
    notes, bars = build_notes()
    assert bars == 32, '小节数应为 32，实际 %d' % bars

    mid = os.path.join(MIDI_DIR, TITLE + '.mid')
    write_smf(mid, notes, bpm=BPM)
    bpm, parsed, ppq = parse_smf(mid)
    obj = to_json('《寄一封》（原创 · 古风 · 有词）', bpm, parsed, ppq)

    # 自校验：写出多少就读回多少，音域不超一个半八度，时长不过 150 秒
    assert obj['noteCount'] == len(notes), '音符数对不上：写 %d 读 %d' % (len(notes), obj['noteCount'])
    assert obj['bars'] == 32.0, '小节数不是 32：%s' % obj['bars']
    lo = min(n['pitch'] for n in parsed)
    hi = max(n['pitch'] for n in parsed)
    assert 48 <= lo and hi <= 84, '音域越界 %d~%d' % (lo, hi)
    assert (hi - lo) <= 18, '音域超过一个半八度：%d 半音' % (hi - lo)
    assert obj['seconds'] <= 150, '超过 150 秒：%s' % obj['seconds']

    js = os.path.join(MIDI_DIR, TITLE + '.json')
    with open(js, 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, separators=(',', ':'))

    wav = os.path.join(MIDI_DIR, TITLE + '.wav')
    sec, wsize = render_wav(js, wav)

    # 逐句时间：每句 8 拍
    per_beat = 60.0 / BPM
    phrase_sec = 8 * per_beat
    clock = 0.0
    lines = []
    blocks = [('主歌一', 'A'), ('副歌', 'C'), ('主歌二', 'B'), ('副歌再现', 'C')]
    for block_name, tag in blocks:
        lines.append('\n### %s\n' % block_name)
        for text in LYRICS[tag]:
            lines.append('| %5.1fs | %s |' % (clock, text))
            clock += phrase_sec

    md = []
    md.append('# 原创歌 01《寄一封》\n')
    md.append('古风 · 有词 · 32 小节 · %s BPM · %.1f 秒 · 音域 %s（%d 半音，在一个半八度内）\n'
              % (BPM, obj['seconds'], obj['range'], hi - lo))
    md.append('## 词（按句排）\n')
    md.append('| 起唱时间 | 歌词 |')
    md.append('| --- | --- |')
    md.extend(lines)
    md.append('\n## 写在词里的几处具体东西\n')
    md.append('- 灯芯挑到第三遍：写了又改，改了就重抄，不是"我很想你"这种空话。')
    md.append('- 邮票贴得有些偏：寄的人手不稳，比"思念"更具体。')
    md.append('- 邮筒锈成了墨蓝：等了很久，环境替人说话。')
    md.append('- 只有一句没说全：不点破，留给听的人自己填。')
    md.append('\n## 双门槛自评\n')
    md.append('| 门槛 | 要求 | 这首 | 结果 |')
    md.append('| --- | --- | --- | --- |')
    md.append('| 传唱度 | 副歌钩子 ≤12 字且重复 ≥2 次 | 「雪落在信纸的边」7 字，出现 2 次 | 过 |')
    md.append('| 传唱度 | 通押 | 全篇压 an/ian（遍/干/篇/天/偏/蓝/安/全/边/天） | 过 |')
    md.append('| 传唱度 | ≤150 秒 | %.1f 秒 | 过 |' % obj['seconds'])
    md.append('| 传唱度 | 音域 ≤1.5 八度 | %s，%d 半音 | 过 |' % (obj['range'], hi - lo))
    md.append('| 深度 | 一个主题、意象统一 | 只有"寄信"一件事，意象全在灯/雪/纸/邮筒上 | 过 |')
    md.append('| 深度 | 不用口号、有具体细节 | 见上「写在词里的几处具体东西」 | 过 |')
    md.append('| 深度 | 结尾留白 | 「只有一句没说全」收，不解释 | 过 |')
    md.append('\n## 合规自检（八条红线）\n')
    md.append('政治、宗教、暴力自伤、低俗、未成年人、侵权、虚假、隐私——逐条都无涉及；无他人作品词句，旋律原创。\n')
    md.append('\n## 文件\n')
    md.append('- `%s.mid`（标准 MIDI，可进任何编曲软件）' % TITLE)
    md.append('- `%s.json`（两端共用的谱）' % TITLE)
    md.append('- `%s.wav`（%d 字节，能直接听旋律，词照上面的时间对）' % (TITLE, wsize))
    txt = '\n'.join(md)
    open(os.path.join(MIDI_DIR, TITLE + '.词.md'), 'w', encoding='utf-8').write(txt)

    print('音符 %d / %s 小节 / %.2f 秒 / %s / %s BPM / %d 半音'
          % (obj['noteCount'], obj['bars'], obj['seconds'], obj['range'], obj['bpm'], hi - lo))
    print('WAV %d 字节' % wsize)
    print('自校验通过（音符数、小节数、音域、时长）')


if __name__ == '__main__':
    main()
