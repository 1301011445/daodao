# -*- coding: utf-8 -*-
"""从 积极歌_v26 的 build() 导出代唱时间轴（line/char/t/dur/midi，t 为秒）。"""
import importlib.util, io, json, os

MOD = r"F:\Daodao\tools\音乐\打工人歌\积极歌_v26.py"
OUT = r"F:\Daodao\tools\音乐\人声\out\代唱_v26_时间轴.json"

sp = importlib.util.spec_from_file_location('v26', MOD)
m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m)
notes, mel, secs = m.build()
BEAT, TEMPO = m.BEAT, m.TEMPO
VCH = m.VOCAL_CH

spb = 60.0 / TEMPO            # 每拍秒数
rows = []
for meta in mel:
    t0 = meta['t']
    ph = sorted([x for x in notes if x['ch'] in VCH and t0 <= x['t'] < t0 + 8 * BEAT], key=lambda x: x['t'])
    text = meta['text']
    vc = '少年' if meta['chorus'] else '自然'     # 大模型评审：副歌要更亮更高 → 副歌用少年声
    for ch, n in zip(text, ph):
        rows.append(dict(line=text, char=ch, voice=vc,
                         t=round(n['t'] / BEAT * spb, 3),
                         dur=round(n['dur'] / BEAT * spb, 3),
                         midi=int(round(n['pitch']))))
io.open(OUT, 'w', encoding='utf-8').write(json.dumps(rows, ensure_ascii=False, indent=1))
print('写出 %s | %d 条 = %d 句' % (OUT, len(rows), len(mel)))
print('音区 %d–%d，首句 %.2fs 起，末句 %.2fs 止'
      % (min(r['midi'] for r in rows), max(r['midi'] for r in rows),
         rows[0]['t'], rows[-1]['t'] + rows[-1]['dur']))
# 积极性量化：上行音程占比 / 句尾是否上扬
up = down = 0
tail_up = 0
for li in range(len(mel)):
    seg = [r['midi'] for r in rows[li * 8:(li + 1) * 8]]
    for a, b in zip(seg, seg[1:]):
        if b > a: up += 1
        elif b < a: down += 1
    if seg[-1] > seg[-3]: tail_up += 1
print('上行 %d / 下行 %d（上行占比 %.0f%%） | 句尾上扬 %d/%d 句'
      % (up, down, 100.0 * up / max(1, up + down), tail_up, len(mel)))
