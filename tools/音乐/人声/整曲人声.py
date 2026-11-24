# -*- coding: utf-8 -*-
# 程序版本：v0.1 | 2026-11-24 | 整句对齐：一句一合成，整句拉伸+连续音高曲线（不再逐字切碎）
"""整曲人声.py

用法：python 整曲人声.py [voice_label] [--mix]
流程：
1. 读 out\\代唱_v25_时间轴.json（每字 t/dur/midi）
2. 每一句：整句 TTS（不切词）→ WSOLA 拉到该句时长
3. 按每字 midi 插值出连续目标音高曲线 → 用变速重采样施加（音高随旋律走，字与字之间不断）
4. 再整体归一化时长、轻颤、暖 EQ、峰值归一
5. 判据闸门：HNR <15dB 就不出片（改名 _待修）
"""
import asyncio, json, os, sys
import numpy as np
import soundfile as sf
import edge_tts

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out')
SR = 44100
VOICES = {
    '少年': ('zh-CN-YunxiaNeural', -3, 0.55),
    '自然': ('zh-CN-XiaoxiaoNeural', 0, 0.6),
    '低语': ('zh-CN-YunjianNeural', 0, 0.55),
}


def wsola(x, k, N=1024, Hs=256, search=32):
    if abs(k - 1.0) < 1e-3:
        return x.copy()
    src_hop = max(1, int(round(Hs / k)))
    win = np.hanning(N)
    out = np.zeros(int(len(x) * k) + 2 * N)
    wsum = np.zeros_like(out)
    idx, o = 0, 0
    while idx + N < len(x) and o + N <= len(out):
        cont = x[idx - src_hop:idx - src_hop + N] if idx >= src_hop and idx - src_hop + N <= len(x) else x[idx:idx + N]
        best, bestd = 0, -1e18
        for d in range(-search, search + 1, 4):
            j = idx + d
            if j < 0 or j + N > len(x):
                continue
            c = float(np.dot(x[j:j + N], cont))
            if c > bestd:
                bestd, best = c, d
        j = max(0, min(len(x) - N, idx + best))
        out[o:o + N] += x[j:j + N] * win
        wsum[o:o + N] += win
        idx += src_hop
        o += Hs
    wsum[wsum < 1e-6] = 1e-6
    return out[:o] / wsum[:o]


def _lowpass(x, sr, cutoff, taps=65):
    """窗函数素 sinc 低通。压缩重采样前必须先过它，否则高频折叠回 4~8k，
    听起来就是一片沙哑（2026-11-25 查到的根因之一）。"""
    if cutoff >= sr * 0.45:
        return x
    n = np.arange(taps) - (taps - 1) / 2.0
    fc = cutoff / sr
    h = 2.0 * fc * np.sinc(2.0 * fc * n) * np.hamming(taps)
    s = h.sum()
    if s <= 1e-9:
        return x
    h /= s
    return np.convolve(x, h, 'same')


def resample_aa(x, newn, sr):
    """重采样到 newn 点；压缩时先低通，避免折叠出沙哑。"""
    if newn <= 0:
        return x[:0]
    k = newn / float(len(x))
    src = _lowpass(x, sr, 0.45 * sr * k) if k < 0.98 else x
    return np.interp(np.linspace(0, len(src) - 1, newn), np.arange(len(src)), src)


def deess(x, sr, lo=4000.0, hi=8200.0):
    """齿音/沙哑抑制：只压 4~8k 这一段的爆点，按能量包络动态给衰减，别一刀切。"""
    import importlib.util as iu
    sp = iu.spec_from_file_location('mx2', os.path.join(HERE, '..', '音色', '道音色融合.py'))
    m2 = iu.module_from_spec(sp); sp.loader.exec_module(m2)
    b1, a1 = m2._biquad(x, sr, 'highpass', lo, 0.0, 0.7071)
    band = m2._lfilter(b1, a1, x)
    band = _lowpass(band, sr, hi)          # 上沿用 FIR 低通（biquad 里没有 lowpass 分支）
    # 包络：15ms 滑动平均
    w = max(1, int(0.015 * sr))
    env = np.convolve(np.abs(band), np.ones(w) / w, 'same')
    ref = float(np.percentile(env, 90)) + 1e-9
    r = np.clip(env / ref, 0.0, 2.0)
    g = 1.0 / (1.0 + 2.4 * r)                 # 爆点最多压到 -8 dB 左右
    gw = max(1, int(0.010 * sr))
    g = np.convolve(g, np.ones(gw) / gw, 'same')
    return x - band + band * g


def f0_of(x, sr):
    seg = x[int(0.1 * sr):int(0.1 * sr) + 4096]
    ac = np.correlate(seg - seg.mean(), seg - seg.mean(), 'full')[len(seg) - 1:]
    lo, hi = int(sr / 700), int(sr / 60)
    return sr / (lo + int(np.argmax(ac[lo:hi])))


def apply_contour(x, sr, f0_curve, base):
    """按目标 f0 曲线变速（连续，不做切段），再把时长拉回原长。
    2026-11-25：这里原来是裸 np.interp，rate 到 1.40 时等于硬抽点，
    4~8k 直接折叠回来，成品听着沙哑。现在压缩段先低通再插值。"""
    n = len(x)
    t = np.arange(n) / sr
    target = np.interp(t, np.linspace(0, t[-1], len(f0_curve)), f0_curve)
    rate = np.clip(target / base, 0.72, 1.40)
    pos = np.cumsum(rate)
    pos = pos - pos[0]
    span = pos[-1]
    src = x
    k = n / max(span, 1e-9)          # 输出点数 / 输入跨度
    if k < 0.98:
        src = _lowpass(src, sr, 0.45 * sr * k)
    y = np.interp(np.linspace(0, span, n), pos, src)
    return y


async def synth(text, voice, rate, path):
    for _ in range(3):
        try:
            await edge_tts.Communicate(text, voice, rate='%+d%%' % rate).save(path)
            if os.path.getsize(path) > 2000:
                return
        except Exception:
            await asyncio.sleep(1.0)
    raise RuntimeError('TTS 失败：%s' % text)


def main():
    label = sys.argv[1] if len(sys.argv) > 1 else '低语'
    tlf = sys.argv[2] if len(sys.argv) > 2 else os.path.join(OUT, '代唱_v25_时间轴.json')
    tag = sys.argv[3] if len(sys.argv) > 3 else ''
    voice, shift, vibsemi = VOICES[label]
    items = json.load(open(tlf, encoding='utf-8'))
    lines = []
    for it in items:
        if not lines or lines[-1][0] != it['line']:
            lines.append([it['line'], []])
        lines[-1][1].append(it)

    total = max(it['t'] + it['dur'] for it in items) + 1.0
    buf = np.zeros(int(total * SR), dtype=np.float64)
    d = os.path.join(OUT, '_tts_line')
    os.makedirs(d, exist_ok=True)
    for li, (text, its) in enumerate(lines):
        vc = its[0].get('voice', label) if isinstance(its[0], dict) else label
        vv = VOICES.get(vc, VOICES[label])
        vname, vshift, vvib = vv[0], vv[1], vv[2]
        path = os.path.join(d, '%s_%02d_%s.mp3' % (label, li, vc))
        t0 = its[0]['t']; t1 = its[-1]['t'] + its[-1]['dur']
        want = int((t1 - t0) * SR)
        if not os.path.exists(path) or os.path.getsize(path) < 2000:
            asyncio.run(synth(text, vname, -8, path))
        x, sr = sf.read(path, dtype='float32')
        if x.ndim > 1:
            x = x.mean(axis=1)
        x = x.astype(np.float64)
        if sr != SR:
            x = resample_aa(x, int(len(x) * SR / sr), sr)
        # 自适应语速：先用 -8% 量一遍，按需要改成一次语速，把 WSOLA 残余拉伸压到 <10%
        ratio = len(x) / max(1, want)
        if abs(ratio - 1) > 0.06:
            new_rate = int(np.clip(round((1.0 / ratio - 1.0) * 100) - 2, -50, 50))
            path2 = path.replace('.mp3', '_r.mp3')
            asyncio.run(synth(text, vname, new_rate, path2))
            x, sr = sf.read(path2, dtype='float32')
            if x.ndim > 1:
                x = x.mean(axis=1)
            x = x.astype(np.float64)
            if sr != SR:
                x = resample_aa(x, int(len(x) * SR / sr), sr)
        x = wsola(x, want / max(1, len(x)))
        x = x[:want] if len(x) >= want else np.pad(x, (0, want - len(x)))
        # 连续音高曲线：以「本句中位音」为 0，只做句内相对起伏（不整体升降调）
        # 绝对降调会把声源硬拉到不属于它的音区，谐波被重采样抹掉（低语 14.1dB 就是这么掉的）
        base = f0_of(x, SR)
        mid0 = float(np.median([it['midi'] for it in its]))
        pts_t, pts_f = [], []
        for it in its:
            rel = (it['midi'] - mid0) / 12.0
            f = base * 2 ** rel
            pts_t.append(it['t'] - t0)
            pts_f.append(f)
        f0_curve = np.interp(np.linspace(0, t1 - t0, 256), pts_t, pts_f)
        x = apply_contour(x, SR, f0_curve, base)
        # 轻颤（4.8Hz / ±0.6 半音），相位连续
        tt = np.arange(len(x)) / SR
        wob = np.cumsum(1 + (2 ** (vvib / 12) - 1) * np.sin(2 * np.pi * 4.8 * tt))
        wob = wob / wob[-1] * (len(x) - 1)
        x = np.interp(wob, np.arange(len(x)), x)
        st = int(t0 * SR); en = min(len(buf), st + len(x))
        buf[st:en] += x[:en - st]

    # 暖 EQ + 轻微饱和（补谐波、抬 HNR）+ 峰值归一
    import importlib.util as iu
    sp = iu.spec_from_file_location('mx', os.path.join(HERE, '..', '音色', '道音色融合.py'))
    mx = iu.module_from_spec(sp); sp.loader.exec_module(mx)
    # 软饱和：只抬谐波不削波，等价于磁带/话放的那点非线性
    # 2026-11-25：驱动量从 1.25 收到 0.50。原来那个量在人声峰值处生出
    # 一堆三、五次谐波，听感就是"毛、沙"，HNR 反而被它拖低
    buf = np.tanh(buf * 0.50) / np.tanh(0.50)
    for kind, f, g, q in [('highpass', 80.0, 0.0, 0.7071), ('lowshelf', 180.0, 1.4, 0.60),
                          ('lowshelf', 320.0, 0.8, 0.70), ('peaking', 900.0, -1.2, 0.80),
                          ('highshelf', 5000.0, -1.0, 0.7071)]:
        b, a = mx._biquad(buf, SR, kind, f, g, q)
        buf = mx._lfilter(b, a, buf)
    # 去齿音：4~8k 爆点动态压制（沙哑的另一半根源）
    buf = deess(buf, SR)
    buf = buf / (np.max(np.abs(buf)) + 1e-9) * 0.88
    out = os.path.join(OUT, '%s_%s.wav' % ('整曲人声' + ('_' + tag if tag else ''), label))
    sf.write(out, buf, SR)
    print('写入 %s | %d 句 | %.1fs | peak %.2f'
          % (out, len(lines), len(buf) / SR, float(np.max(np.abs(buf)))))
    # 出厂闸门：判据不过就不算成品（H1 谐噪比 <15dB 等）
    import importlib.util as iu2
    sp3 = iu2.spec_from_file_location('q', os.path.join(HERE, '..', '音色', '音色质量判据.py'))
    q = iu2.module_from_spec(sp3); sp3.loader.exec_module(q)
    if q.judge(out) > 0:
        os.replace(out, out.replace('.wav', '_待修.wav'))
        print('   ↑ 判据未全过，改 _待修，不出片')
    return 0


if __name__ == '__main__':
    sys.exit(main())
