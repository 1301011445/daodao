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
    s = prof.get('唱法', {})
    print(label, '模板：起颤 %.2f 尾招 %s 气声 %.2f' % (s.get('起颤', 0), s.get('尾招', '-'), prof['breath']))
    # 跟主流程一致：整句 4 个词组，每组切成两个字，每个音符唱一个字（原来我给每个音符塞整组两个字，糊成杂音）
    words = [(m['text'][wi * 2:wi * 2 + 2], voices[0]) for wi in range(4)]
    await asyncio.gather(*[cv.tts_word(v, w) for w, v in words])
    parts = {wi: cv.split_two(cv.CACHE.get((voices[0], w)), SR) for wi, (w, _) in enumerate(words)}
    t0 = ph[0]['t']
    end = ph[-1]['t'] + ph[-1]['dur']
    buf = np.zeros(int((end - t0) * spt * SR) + SR // 5, dtype=np.float32)
    for ci, n in enumerate(ph):
        wi = ci // 2
        audio = parts[wi][ci % 2]
        if audio is None or len(audio) == 0:
            continue
        dur = int(n['dur'] * spt * SR * (0.99 if m.get('chorus') else 0.92))
        hz = 440.0 * (2.0 ** ((n['pitch'] - 69 + cv.VOICE_SHIFT.get(voices[0], 0.0)) / 12.0))
        y = cv.sing(audio, hz, max(int(SR * 0.12), dur), SR, prof, 1.25 if m.get('chorus') else 1.0)
        st = int((n['t'] - t0) * spt * SR)
        seg = y[:len(buf) - st]
        if len(seg) > 0:
            buf[st:st + len(seg)] += seg
    pk = float(np.abs(buf).max()) or 1.0
    buf *= 0.9 / pk
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
