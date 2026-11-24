# -*- coding: utf-8 -*-
# 程序版本：v0.1 | 2026-11-24 | 整句合成人声（不再逐字贴音符），轻颤 + 暖 EQ
"""人声_整句.py

用法：python 人声_整句.py
产出 out\\人声_少年.wav / 人声_自然.wav / 人声_低语.wav（纯人声，无伴奏）
思路：
- 逐两字切碎再按音符硬拉，是 HNR −5dB / jitter 20% 的根因（字与字之间没有共振延续）
- 改成整句一次合成，保留 TTS 自身的连读与共振
- 只加 4.6–5.0Hz / 0.6–0.9 半音的轻颤（文献里训练歌者 4–7Hz、幅度 0.5–2.5 半音）
- EQ 用 v2 链条但收敛一点，避免把人声压扁
"""
import asyncio, os, sys
import numpy as np
import soundfile as sf
import edge_tts

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out')
SR = 44100

TEXT = '风从故乡吹来，落在肩上。我把旧歌唱完，天就亮了。'
VOICES = {
    '少年': ('zh-CN-YunxiaNeural', -10, '+8Hz', 5.0, 0.60),
    '自然': ('zh-CN-XiaoxiaoNeural', -12, '+0Hz', 4.6, 0.75),
    '低语': ('zh-CN-YunjianNeural', -14, '-6Hz', 4.8, 0.90),
}


def vibrato(x, sr, rate, semi):
    """按半音深度做轻颤：pos 累加受正弦调制的速率，时长不变。"""
    d = 2 ** (semi / 12.0) - 1
    n = len(x)
    t = np.arange(n) / sr
    pos = np.cumsum(1 + d * np.sin(2 * np.pi * rate * t))
    pos = pos / pos[-1] * (n - 1)
    return np.interp(pos, np.arange(n), x)


def warm_eq(x, sr):
    """暖 EQ（比 v2 温和）：只压 5k 以上，抬 180/320，去 900 的箱音。"""
    sys.path.insert(0, os.path.join(HERE, '..', '音色'))
    import importlib.util
    sp = importlib.util.spec_from_file_location('mx', os.path.join(HERE, '..', '音色', '道音色融合.py'))
    mx = importlib.util.module_from_spec(sp); sp.loader.exec_module(mx)
    chain = [('highpass', 80.0, 0.0, 0.7071),
             ('lowshelf', 180.0, 1.4, 0.60),
             ('lowshelf', 320.0, 0.8, 0.70),
             ('peaking', 900.0, -1.2, 0.80),
             ('highshelf', 5000.0, -1.0, 0.7071),
             ('highshelf', 11000.0, -0.8, 0.7071)]
    y = x.astype(np.float64)
    for kind, f, g, q in chain:
        b, a = mx._biquad(y, sr, kind, f, g, q)
        y = mx._lfilter(b, a, y)
    return y


async def synth(text, voice, rate, pitch, path):
    await edge_tts.Communicate(text, voice, rate='%+d%%' % rate, pitch=pitch).save(path)


def decode(path):
    """edge-tts 出 mp3，soundfile（libsndfile 1.1+）直接能读。"""
    x, sr = sf.read(path, dtype='float32')
    if x.ndim > 1:
        x = x.mean(axis=1)
    return x.astype(np.float64), sr


def main():
    os.makedirs(OUT, exist_ok=True)
    for label, (voice, rate, pitch, vr, vs) in VOICES.items():
        mp3 = os.path.join(OUT, '_tts_%s.mp3' % label)
        asyncio.run(synth(TEXT, voice, rate, pitch, mp3))
        x, sr = decode(mp3)
        if sr != SR:
            x = np.interp(np.linspace(0, len(x) - 1, int(len(x) * SR / sr)), np.arange(len(x)), x)
            sr = SR
        x = vibrato(x, sr, vr, vs)
        y = warm_eq(x, sr)
        # 首尾 30ms 淡入淡出
        n = int(0.03 * sr)
        y[:n] *= np.linspace(0, 1, n)
        y[-n:] *= np.linspace(1, 0, n)
        y = y / (np.max(np.abs(y)) + 1e-9) * 0.88
        out = os.path.join(OUT, '人声_%s.wav' % label)
        sf.write(out, y, SR)
        print('%s <- %s | 时长 %.2fs | peak %.2f | 颤 %.1fHz/%.2f半音'
              % (label, voice, len(y) / SR, float(np.max(np.abs(y))), vr, vs))
        # 出厂闸门：用音色质量判据自检，H1（谐噪比）不达标就不算成品
        import importlib.util as iu
        sp2 = iu.spec_from_file_location('q', os.path.join(HERE, '..', '音色', '音色质量判据.py'))
        q = iu.module_from_spec(sp2); sp2.loader.exec_module(q)
        if q.judge(out) > 0:
            print('   ↑ 判据未全过，标 _待修 不出片')
            os.replace(out, out.replace('.wav', '_待修.wav'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
