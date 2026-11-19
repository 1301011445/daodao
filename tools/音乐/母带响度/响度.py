# -*- coding: utf-8 -*-
"""第 19 类实测：给本曲量 LUFS / 样本峰值 / 近似真峰值(TP) / 波峰因数，并出母带版。
判据见 乐谱学习_第19类_母带与响度.md

实现说明（不装库，纯标准库）：
- LUFS：按 ITU-R BS.1770 的 K 加权（两级双二阶）→ 400ms 块 / 100ms 跳 → 双门限（绝对 −70、
  相对 −10 dB）取积分值。系数是 **48kHz 版本**，本曲 44.1kHz 直接套用，误差约 0.1–0.2 dB，
  这是本机没有重采样与系数表时的取舍，写在文档"没做的"里。
- 真峰值：不做 4 倍过采样，只在峰值附近样本做三次插值估计，属**近似**，不是 dBTP 的权威值。
"""
import sys, math, os, struct, wave

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, '..', '打工人歌', 'out', '把好日子扛在肩上.wav')
OUT = os.path.join(HERE, 'out', '把好日子扛在肩上_母带版.wav')

# ── K 加权（BS.1770-4, 48kHz 系数）
B1 = [1.53512485958697, -2.69169618940638, 1.19839281085285]
A1 = [1.0, -1.69065929318241, 0.73248077421585]
B2 = [1.0, -2.0, 1.0]
A2 = [1.0, -1.99004745483398, 0.99007225036621]

def biquad(x, b, a):
    y = [0.0] * len(x)
    x1 = x2 = y1 = y2 = 0.0
    b0, b1, b2 = b
    a1, a2 = a[1], a[2]
    for i, s in enumerate(x):
        out = b0 * s + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2
        x2, x1 = x1, s
        y2, y1 = y1, out
        y[i] = out
    return y

def read_wav(path):
    w = wave.open(path, 'rb')
    n, sr, ch = w.getnframes(), w.getframerate(), w.getnchannels()
    raw = w.readframes(n); w.close()
    s = struct.unpack('<%dh' % (n * ch), raw)
    if ch > 1:
        s = [sum(s[i * ch:(i + 1) * ch]) / ch for i in range(n)]   # 先按单声道处理
    return s, sr, ch

def lufs_integrated(samples, sr):
    x = [v / 32768.0 for v in samples]
    y = biquad(biquad(x, B1, A1), B2, A2)
    blk = int(0.4 * sr); hop = int(0.1 * sr)
    blocks = []
    for a in range(0, len(y) - blk, hop):
        seg = y[a:a + blk]
        ms = sum(v * v for v in seg) / blk
        if ms > 0:
            blocks.append(-0.691 + 10 * math.log10(ms))     # 各块 LUFS（单声道权重 1.0）
    if not blocks:
        return None, 0
    abs_gated = [b for b in blocks if b > -70]
    if not abs_gated:
        return None, 0
    rel = -0.691 + 10 * math.log10(sum(10 ** ((b + 0.691) / 10.0) for b in abs_gated) / len(abs_gated))
    gate = rel - 10
    used = [b for b in abs_gated if b > gate]
    ms_mean = sum(10 ** ((b + 0.691) / 10.0) for b in used) / len(used)
    return -0.691 + 10 * math.log10(ms_mean), len(used)

def peaks(samples):
    n = len(samples)
    pk = max(abs(v) for v in samples) / 32768.0
    db = 20 * math.log10(pk) if pk > 0 else -120
    # 三次插值估计真峰值（只看接近峰值的采样，省时间）
    thr = pk * 0.8 * 32768.0
    best = pk
    for i in range(1, n - 2):
        if abs(samples[i]) >= thr or abs(samples[i + 1]) >= thr:
            p0, p1, p2, p3 = (samples[i - 1] / 32768.0, samples[i] / 32768.0,
                              samples[i + 1] / 32768.0, samples[i + 2] / 32768.0)
            for t in (0.25, 0.5, 0.75):
                v = 0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t
                           + (-p0 + 3 * p1 - 3 * p2 + p3) * t * t * t)
                best = max(best, abs(v))
    return db, (20 * math.log10(best) if best > 0 else -120)

def crest(samples, sr):
    x = [v / 32768.0 for v in samples]
    pk = max(abs(v) for v in x)
    rms = math.sqrt(sum(v * v for v in x) / len(x))
    return 20 * math.log10(pk / rms)

def write_scaled(samples, gain, path):
    data = struct.pack('<%dh' % len(samples),
                       *[max(-32767, min(32767, int(v * gain))) for v in samples])
    w = wave.open(path, 'wb'); w.setnchannels(1); w.setsampwidth(2)
    w.setframerate(sr); w.writeframes(data); w.close()   # 2026-11-19 修：原来硬写 44100，源是 22050，导致 180 秒的母带被标成 90 秒

if __name__ == '__main__':
    os.makedirs(os.path.join(HERE, 'out'), exist_ok=True)
    # 2026-11-19 优化：支持任意曲目，参数 1=源 wav，参数 2=输出名（不给就用默认职场版）
    if len(sys.argv) > 1:
        SRC = sys.argv[1]
        nm = os.path.splitext(os.path.basename(SRC))[0]
        if len(sys.argv) > 2:
            nm = sys.argv[2]
        OUT = os.path.join(HERE, 'out', nm + '_母带版.wav')
    s, sr, ch = read_wav(SRC)
    sec = len(s) / float(sr)
    print('源文件：%.2f 秒，声道 %d（%s），采样率 %d'
          % (sec, ch, '单声道（没有立体声宽度）' if ch == 1 else '立体声', sr))
    lufs, nb = lufs_integrated(s, sr)
    spk, tp = peaks(s)
    cr = crest(s, sr)
    print('LUFS 积分 %.1f（用 %d 个门限内块；单声道权重 1.0）' % (lufs, nb))
    print('样本峰值 %.2f dBFS ｜ 真峰值估算 %.2f dBTP ｜ 波峰因数 %.1f dB' % (spk, tp, cr))
    print()
    print('目标（来源：Spotify/YouTube/TikTok）: −14 LUFS 积分 / ≤ −1 dBTP')
    print('  LUFS 偏差 %+.1f dB' % (lufs + 14))
    print('  真峰值余量 %.2f dB（要 ≥1.0）' % (-1 - tp))
    # 甲案（保守）：只保峰值，把真峰值压到 −1.5 dBFS
    headroom_db = -1.5 - tp
    gain = 10 ** (headroom_db / 20.0)
    write_scaled(s, gain, OUT)
    s2, sr2, _ = read_wav(OUT)
    l2, _n = lufs_integrated(s2, sr2)
    spk2, tp2 = peaks(s2)
    print()
    print('甲案（只保峰值）：增益 %+.2f dB → 真峰值 %.2f dBTP，LUFS %.1f（离 −14 还差 %+.1f dB）'
          % (headroom_db, tp2, l2, l2 + 14))
    print()

    # 乙案（推到 −14）：先加 +1.1 dB 增益，再用软膝限幅把超过 −1.5 dBFS 的极少数峰削圆
    need_db = -14.0 - lufs                     # 要让积分响度到 −14 需要的增益
    limit = 10 ** (-1.5 / 20.0)                # −1.5 dBFS 阈值
    g2 = 10 ** (need_db / 20.0)
    y = []
    for v in s:
        a = v / 32768.0 * g2
        if abs(a) > limit:
            a = math.copysign(limit * math.tanh(abs(a) / limit), a)
        y.append(a * 32768.0)
    out_b = os.path.join(HERE, 'out', os.path.splitext(os.path.basename(OUT))[0] + '_限幅.wav')
    write_scaled(y, 1.0, out_b)
    s3, sr3, _ = read_wav(out_b)
    l3, _n = lufs_integrated(s3, sr3)
    spk3, tp3 = peaks(s3)
    print('乙案（推到 −14）：增益 %+.2f dB + 软膝限幅（阈值 −1.5 dBFS）'
          % need_db)
    print('  结果：LUFS %.1f（偏差 %+.1f）｜ 真峰值 %.2f dBTP ｜ 样本峰 %.2f dBFS'
          % (l3, l3 + 14, tp3, spk3))
    ok_l = abs(l3 + 14) <= 1.0
    ok_p = tp3 <= -1.0
    print('  判据：LUFS 在 −14±1 %s ｜ 真峰值 ≤ −1 dBTP %s'
          % ('✓' if ok_l else '✗', '✓' if ok_p else '✗'))
    print()
    print('注：本文件采样率 22050 Hz，K 加权系数是 48 kHz 版本，实测值偏差约 0.3–0.8 dB；'
          '真峰值也是插值估算，非权威 dBTP。口径写进文档「没做的」，不当成精确值。')
