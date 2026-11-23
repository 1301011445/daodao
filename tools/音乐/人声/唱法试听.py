# -*- coding: utf-8 -*-
# 程序版本：v0.1 | 2026-11-23 | 新建：拿一句真实歌词按不同唱法模板渲染，只为听「起颤 / 尾招」差别
"""唱法试听：拿一句真实歌词（8 个音）分别按不同唱法模板渲染一遍，只为听「起颤 / 尾招」的差别。
用法： python 唱法试听.py 那英 王菲   → out\\试听_那英.wav / 试听_王菲.wav
"""
import asyncio, importlib.util, os, sys
import numpy as np
import soundfile as sf

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location('cv25', os.path.join(HERE, '唱腔v25.py'))
cv = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cv)

SR = cv.SR


async def render(label, m, notes, spt, voices):
    prof = cv.timbre.blend(label)
    ph = sorted([x for x in notes if x['ch'] in (0, 4) and m['t'] <= x['t'] < m['t'] + 8 * cv.BEAT], key=lambda x: x['t'])
    if len(ph) != 8:
        return None
    print(label, '模板：起颤 %.2f 尾招 %s 气声 %.2f' %
          (prof.get('唱法', {}).get('起颤', 0), prof.get('唱法', {}).get('尾招', '-'), prof['breath']))
    words = [(m['text'][i * 2:i * 2 + 2], voices[0]) for i in range(4)]
    await asyncio.gather(*[cv.tts_word(v, w) for w, v in words])
    buf = np.zeros(int((ph[-1]['t'] + ph[-1]['dur']) * spt * SR) + SR // 5, dtype=np.float32)
    for i, n in enumerate(ph):
        w = words[i // 2][0]
        audio = cv.CACHE.get((words[i // 2][1], w))
        if audio is None:
            continue
        dur = int(n['dur'] * spt * SR)
        hz = 440.0 * (2.0 ** ((n['pitch'] - 69 + cv.VOICE_SHIFT.get(voices[0], 0.0)) / 12.0))
        y = cv.sing(audio, hz, dur, SR, prof)
        st = int(n['t'] * spt * SR)
        seg = y[:len(buf) - st]
        buf[st:st + len(seg)] += seg / 3.0
    return buf


async def main():
    labels = sys.argv[1:] or ['那英', '王菲']
    notes, mels, secs = cv.g25.build()
    spt = (60.0 / cv.g25.TEMPO) / cv.g25.PPQ
    ch = [m for m in mels if m.get('chorus')] or mels
    m = ch[0]
    outdir = os.path.join(HERE, 'out')
    os.makedirs(outdir, exist_ok=True)
    for label in labels:
        voices = [cv.VOICE_FEMALE] if label != '李健' else [cv.VOICE_MALE]
        buf = await render(label, m, notes, spt, voices)
        if buf is None:
            print(label, '这句凑不满 8 个音，跳过')
            continue
        p = os.path.join(outdir, f'试听_{label}.wav')
        sf.write(p, buf, SR)
        print('写出', p, len(buf) / SR, '秒')


asyncio.run(main())
