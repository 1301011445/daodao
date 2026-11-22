# -*- coding: utf-8 -*-
"""词曲音色匹配检查：三样东西必须对得上，不能各唱各的。

  1) 词的情绪 → 音色亮度（气声/频谱重心）
  2) 旋律音区 → 人声音区（按绝对音算半音差，超过 8 就是吊着唱或压着唱）
  3) 段落角色 → 音色分工（谁唱、几个人、颤音多少）

对照表在 匹配表.py，和合成器共用同一份。

用法：python 匹配检查.py [音色标签]
产出：out\匹配检查.json
"""
import importlib.util, json, math, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))


def load(path, name):
    s = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


g25 = load(os.path.join(HERE, '..', '打工人歌', '打工人歌_v25.py'), 'g25')
timbre = load(os.path.join(HERE, '..', '音色', '音色学习.py'), 'timbre')
mt = load(os.path.join(HERE, '匹配表.py'), 'mt')


def semis(freq, midi):
    return 12.0 * math.log2(freq / (440.0 * 2 ** ((midi - 69) / 12.0)))


def main():
    label = sys.argv[1] if len(sys.argv) > 1 else '旧演唱版'
    prof = timbre.blend(label)
    lib = json.load(open(timbre.LIB, encoding='utf-8'))
    base = lib.get('dao_base', timbre.DAO_BASE)
    notes, mels, secs = g25.build()
    vocal = [n for n in notes if n['ch'] in (0, 4)]

    rows, bad = [], 0
    for s in secs:
        if s['kind'] != 'lyric':
            continue
        tag = s['tag']
        role = mt.ROLE.get(tag, mt.ROLE['V'])
        seg = [n for n in mels if s['t0'] <= n['t'] < s['t1']]
        tones = [n for n in vocal if s['t0'] <= n['t'] < s['t1']]
        if not seg or not tones:
            continue
        med = float(np.median([t['pitch'] for t in tones]))
        txt = ''.join(m['text'] for m in seg)
        moods = [mt.MOOD[k] for k in mt.MOOD if k in txt]
        mood = max(set(moods), key=moods.count) if moods else 'steady'
        mtarget = mt.MOOD_TARGET[mood]
        fix = mt.TAG_FIX.get(tag, dict(bright_db=0, breath=1, vib=1))

        picks = role['voices']
        shift = {'M': -5.0, 'F': 0.0}
        hz = float(np.mean([440.0 * 2 ** ((med - 69 + shift[v] + role['reg']) / 12.0) for v in picks]))
        gap = semis(hz, med)

        # 合成时的高频提亮会抬重心，这里按经验折算进去（1dB ≈ 10% 重心）
        bright = 1.0 + 0.10 * fix['bright_db']
        c_ratio = (prof['centroid'] / base['centroid']) * bright / mtarget['centroid']
        b_ratio = (prof['breath'] / base['breath']) * fix['breath'] / mtarget['breath']
        v_ratio = (prof['vib_rate'] / base['vib_rate']) * fix['vib'] / mtarget['vib']

        ok = abs(gap) <= 8.0 and 0.85 <= c_ratio <= 1.25 and 0.8 <= b_ratio <= 1.3
        if not ok:
            bad += 1
        rows.append(dict(tag=tag, mood=mood, mel_med=round(med, 1), voice_hz=round(hz),
                         gap=round(gap, 2), centroid=round(c_ratio, 2), breath=round(b_ratio, 2),
                         vib=round(v_ratio, 2), ok=bool(ok)))
        print('%s %-4s 情绪%-6s 旋律%d 人声%.0fHz 差%+.1f | 亮度%.2f 气声%.2f 颤音%.2f %s'
              % (tag, '(副)' if tag.startswith('C') else '(主)', mood, med, hz, gap,
                 c_ratio, b_ratio, v_ratio, 'OK' if ok else 'X'))

    out = os.path.join(HERE, 'out'); os.makedirs(out, exist_ok=True)
    json.dump(dict(label=label, prof=prof, rows=rows, bad=bad),
              open(os.path.join(out, '匹配检查.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('不匹配段落 %d / %d' % (bad, len(rows)))
    return 0 if bad == 0 else 2


if __name__ == '__main__':
    sys.exit(main())
