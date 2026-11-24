# -*- coding: utf-8 -*-
# 程序版本：v0.1 | 2026-11-24 | 换声源试听：同一句词、同一个旋律，用三个新 TTS 源各唱一遍
"""试听_三声.py

用法：python 试听_三声.py
产出 out\\试听_少年声.wav / 试听_自然声.wav / 试听_低语声.wav（人声 + v2 音色链）
"""
import asyncio, importlib.util, os, sys
import numpy as np
import soundfile as sf

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location('cv25', os.path.join(HERE, '唱腔v25.py'))
cv = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cv)
spec2 = importlib.util.spec_from_file_location(
    'mix', os.path.join(HERE, '..', '音色', '道音色融合.py'))
mx = importlib.util.module_from_spec(spec2)
spec2.loader.exec_module(mx)

SR = cv.SR
LYRIC = '风从故乡吹来的歌'      # 8 字，4 个两字词组
MELODY = [67, 69, 71, 72, 72, 71, 69, 67]   # G A B C C B A G

SOURCES = {
    '少年声': ('zh-CN-YunxiaNeural', 0.0),
    '自然声': ('zh-CN-XiaoxiaoNeural', 0.0),
    '低语声': ('zh-CN-YunjianNeural', -1.5),
}


def main():
    beat = 0.55
    for label, (voice, shift) in SOURCES.items():
        prof = cv.timbre.blend(label)
        words = [LYRIC[i * 2:i * 2 + 2] for i in range(4)]

        async def warm():
            for w in words:
                await cv.tts_word(voice, w)

        asyncio.run(warm())
        parts = {i: cv.split_two(cv.CACHE[(voice, w)], SR) for i, w in enumerate(words)}
        buf = np.zeros(int(8 * beat * SR) + SR // 4, dtype=np.float32)
        for i, pitch in enumerate(MELODY):
            wi, ci = i // 2, i % 2
            audio = parts[wi][ci]
            if audio is None or len(audio) == 0:
                continue
            hz = 440.0 * (2.0 ** ((pitch - 69 + shift) / 12.0))
            dur = int(beat * SR * 0.94)
            y = cv.sing(audio, hz, max(int(SR * 0.15), dur), SR, prof, 1.0)
            st = int(i * beat * SR)
            en = min(len(buf), st + len(y))
            buf[st:en] += y[:en - st]
        # 归一 + v2 音色链
        buf = buf / (np.max(np.abs(buf)) + 1e-9) * 0.9
        y = mx.apply_eq(buf.astype(np.float64), SR, 'v2')
        y = y / (np.max(np.abs(y)) + 1e-9) * 0.85
        out = os.path.join(HERE, 'out', '试听_%s.wav' % label)
        sf.write(out, y.astype(np.float32), SR)
        print('%s <- %s | 模板 vib %.2f/%.3f breath %.2f | %.2fs | peak %.2f'
              % (label, voice, prof['vib_rate'], prof['vib_depth'], prof['breath'],
                 len(y) / SR, float(np.max(np.abs(y)))))
    return 0


if __name__ == '__main__':
    sys.exit(main())
