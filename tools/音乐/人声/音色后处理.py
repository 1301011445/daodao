# -*- coding: utf-8 -*-
"""音色后处理 v0.1：给合成唱/合成语音加「人气」——短混响、气息噪声床、软压缩、立体声微错位。
用于歌声试音与实时语音的离线校验；所有参数可单独关掉，便于 A/B。
"""
import numpy as np
import soundfile as sf


def _env(x, sr, win_ms=10):
    n = max(1, int(sr * win_ms / 1000))
    k = np.ones(n) / n
    e = np.sqrt(np.convolve(x * x, k, mode='same') + 1e-12)
    return e


def breath_bed(x, sr, amount=0.035, seed=7):
    """在发声段叠一层带包络的高频噪声，模拟气息。"""
    rng = np.random.default_rng(seed)
    noise = rng.normal(0, 1, len(x))
    # 一阶高通，让噪声偏高频
    hp = np.empty_like(noise)
    a = 0.92
    prev_x = 0.0
    prev_y = 0.0
    for i, v in enumerate(noise):
        y = a * (prev_y + v - prev_x)
        hp[i] = y
        prev_x = v
        prev_y = y
    e = _env(x, sr)
    e = e / (e.max() + 1e-9)
    return x + hp * e * amount


def soft_comp(x, sr, thresh_db=-20.0, ratio=2.0, win_ms=30):
    e = _env(x, sr, win_ms)
    edb = 20 * np.log10(e + 1e-9)
    over = np.maximum(0.0, edb - thresh_db)
    gain_db = -over * (1 - 1.0 / ratio)
    g = 10 ** (gain_db / 20.0)
    return x * g


def reverb(x, sr, wet=0.28, decay=0.6, predelay_ms=18):
    """Schroeder 简化混响：4 梳状 + 2 全通。"""
    out = np.zeros_like(x)
    for d_ms, g in [(29, 0.72), (37, 0.68), (41, 0.64), (53, 0.60)]:
        d = int(sr * d_ms / 1000)
        buf = np.zeros(len(x) + d)
        y = np.zeros(len(x))
        for i in range(len(x)):
            v = x[i] + g * buf[i]
            buf[i + d] = v
            y[i] = v
        out += y / 4.0
    for d_ms, g in [(5, 0.5), (7, 0.5)]:
        d = int(sr * d_ms / 1000)
        src = out
        y = np.zeros_like(src)
        for i in range(len(src)):
            xd = src[i - d] if i >= d else 0.0
            yd = y[i - d] if i >= d else 0.0
            y[i] = -g * src[i] + xd + g * yd
        out = y
    out *= decay
    pd = int(sr * predelay_ms / 1000)
    out = np.concatenate([np.zeros(pd), out[:-pd]]) if pd else out
    return x * (1 - wet) + out * wet


def eq_soften(x, sr, shelf_hz=3200.0, cut_db=-2.0, low_hz=120.0, low_db=1.0):
    """简单的两段搁架：削一点刺耳高频，抬一点低频温度。"""
    spec = np.fft.rfft(x)
    freq = np.fft.rfftfreq(len(x), 1.0 / sr)
    gain = np.ones_like(freq)
    # 高频 shelf（一阶）
    hi = freq > shelf_hz
    gain[hi] = 10 ** (cut_db / 20.0)
    # 低频抬升
    lo = freq < low_hz
    gain[lo] = 10 ** (low_db / 20.0)
    # 平滑过渡
    k = max(1, len(gain) // 200)
    kern = np.ones(k) / k
    gain = np.convolve(gain, kern, mode='same')
    return np.fft.irfft(spec * gain, n=len(x))


def stereo_widen(x, sr, delay_ms=9.0, mix=0.55):
    d = int(sr * delay_ms / 1000)
    r = np.concatenate([np.zeros(d), x[:-d]]) if d else x
    r = 0.55 * r + 0.45 * x
    l = 0.45 * r + 0.55 * x
    st = np.stack([l, r], axis=1)
    st = st * mix + np.stack([x, x], axis=1) * (1 - mix)
    return st


def process(path_in, path_out, sr_out=None, wet=0.30, breath=0.035, comp=True):
    x, sr = sf.read(path_in)
    if x.ndim > 1:
        x = x.mean(axis=1)
    x = eq_soften(x, sr)
    x = breath_bed(x, sr, amount=breath)
    if comp:
        x = soft_comp(x, sr)
    x = reverb(x, sr, wet=wet)
    st = stereo_widen(x, sr)
    st = st / (np.max(np.abs(st)) + 1e-9) * 0.92
    sf.write(path_out, st, sr_out or sr)
    return st, sr


def realtime_profile(x, sr, breath=0.015, fade_ms=5.0, soften_db=-1.5):
    """实时语音可用的一套（无混响、无 FFT 长窗）：轻削高频 + 微量气息 + 首尾淡入淡出防爆音。
    注意：真实时里 EQ 需换成双二阶（biquad），这里的 FFT 版本只做离线验证。"""
    y = eq_soften(x, sr, shelf_hz=3400.0, cut_db=soften_db, low_hz=150.0, low_db=0.5)
    y = breath_bed(y, sr, amount=breath)
    n = int(sr * fade_ms / 1000)
    if n > 0 and len(y) > 2 * n:
        ramp = np.linspace(0, 1, n)
        y[:n] *= ramp
        y[-n:] *= ramp[::-1]
    return y


def mix_mono(x, sr, wet=0.18, breath=0.010, soften_db=-1.5, comp=True):
    """单声道自然混音：不搞延迟叠加（那会带合唱味/电味），只做轻 EQ + 微量气息 + 短混响。"""
    y = eq_soften(x, sr, shelf_hz=3400.0, cut_db=soften_db, low_hz=150.0, low_db=0.5)
    y = breath_bed(y, sr, amount=breath)
    if comp:
        y = soft_comp(y, sr)
    y = reverb(y, sr, wet=wet)
    m = np.max(np.abs(y)) + 1e-9
    return y / m * 0.90


if __name__ == '__main__':
    import sys
    src, dst = sys.argv[1], sys.argv[2]
    st, sr = process(src, dst)
    print('OK|%s|%d|dur=%.2fs|peak=%.3f' % (dst, sr, st.shape[0] / sr, np.max(np.abs(st))))
