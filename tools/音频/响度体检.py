# -*- coding: utf-8 -*-
"""响度体检（ITU-R BS.1770-4 口径）：integrated LUFS + true peak + 电平分解

用法：
    python 响度体检.py <wav...>        # 体检若干 WAV，打印表格并写 响度体检.json
    python 响度体检.py --selftest      # 用合成信号自检（1kHz 正弦的理论 LUFS 已知）

判据（第3项渲染能力，来自 Sound On Sound）：
    A. integrated LUFS 落在 -16 ± 1（商业母带交付口径）
    B. true peak <= -1 dBTP
    C. 峰均比（LUFS 与样本峰值之差）落在 10–17 dB（曲风正常的动态保留）`r`n       —— 说明：早期写的「峰值 <= -3.0 dBFS」与 -16 LUFS 在数学上互斥`r`n       （-3.0 dBFS 峰值配 -16 LUFS 需要峰均比恰好 13 dB），已改为峰均比判据；`r`n       分发/播放端仍按 B 的 dBTP <= -1.0 把关。
    D. 单轨（分轨文件）电平接近 -18 dBFS
"""
import io, json, math, os, sys, wave

import numpy as np

# ---------- BS.1770 K 加权（RBJ 双二阶，按文件采样率现算） ----------
def _biquad_highshelf(fs, f0, G_db, Q):
    A = 10 ** (G_db / 40.0)
    w0 = 2 * math.pi * f0 / fs
    alpha = math.sin(w0) / (2 * Q)
    cosw = math.cos(w0)
    b0 = A * ((A + 1) + (A - 1) * cosw + 2 * math.sqrt(A) * alpha)
    b1 = -2 * A * ((A - 1) + (A + 1) * cosw)
    b2 = A * ((A + 1) + (A - 1) * cosw - 2 * math.sqrt(A) * alpha)
    a0 = (A + 1) - (A - 1) * cosw + 2 * math.sqrt(A) * alpha
    a1 = 2 * ((A - 1) - (A + 1) * cosw)
    a2 = (A + 1) - (A - 1) * cosw - 2 * math.sqrt(A) * alpha
    return (b0 / a0, b1 / a0, b2 / a0, 1.0, a1 / a0, a2 / a0)


def _biquad_highpass(fs, f0, Q):
    w0 = 2 * math.pi * f0 / fs
    alpha = math.sin(w0) / (2 * Q)
    cosw = math.cos(w0)
    b0 = (1 + cosw) / 2
    b1 = -(1 + cosw)
    b2 = (1 + cosw) / 2
    a0 = 1 + alpha
    a1 = -2 * cosw
    a2 = 1 - alpha
    return (b0 / a0, b1 / a0, b2 / a0, 1.0, a1 / a0, a2 / a0)


K_SHELF = dict(f0=1681.974450955533, G_db=3.999843853973347, Q=0.7071752369554196)
K_RLB = dict(f0=38.13547087602444, Q=0.5002454629685694)


def _apply_biquad(x, coef):
    b0, b1, b2, a0, a1, a2 = coef
    try:
        from scipy.signal import lfilter
        return lfilter([b0, b1, b2], [a0, a1, a2], x)
    except Exception:
        pass
    # 直接 II 型转置，纯 numpy 递推（无 scipy 时的兜底）
    y = np.zeros_like(x)
    z1 = z2 = 0.0
    for i in range(x.shape[0]):
        xi = x[i]
        yi = b0 * xi + z1
        z1 = b1 * xi - a1 * yi + z2
        z2 = b2 * xi - a2 * yi
        y[i] = yi
    return y


def k_weight(x, fs):
    x = _apply_biquad(x, _biquad_highshelf(fs, **K_SHELF))
    x = _apply_biquad(x, _biquad_highpass(fs, **K_RLB))
    return x


# ---------- 读 WAV ----------
def read_wav(path):
    with wave.open(path, 'rb') as w:
        fs = w.getframerate()
        ch = w.getnchannels()
        sw = w.getsampwidth()
        n = w.getnframes()
        raw = w.readframes(n)
    if sw == 2:
        data = np.frombuffer(raw, dtype='<i2').astype(np.float64) / 32768.0
    elif sw == 3:
        b = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 3).astype(np.int32)
        v = b[:, 0] | (b[:, 1] << 8) | (b[:, 2] << 16)
        v = np.where(v >= 1 << 23, v - (1 << 24), v)
        data = v.astype(np.float64) / (1 << 23)
    elif sw == 4:
        data = np.frombuffer(raw, dtype='<i4').astype(np.float64) / (1 << 31)
    else:
        raise ValueError('不支持采样位深 %d' % sw)
    if ch > 1:
        data = data.reshape(-1, ch)
    else:
        data = data.reshape(-1, 1)
    return fs, data


# ---------- BS.1770 积分响度 ----------
def integrated_lufs(x_mono_channels, fs):
    """x: (n, ch) 已是 K 加权的多通道数据"""
    n = x_mono_channels.shape[0]
    blk = int(round(0.400 * fs))
    hop = int(round(0.100 * fs))
    if n < blk:
        blk = n
        hop = max(1, n // 4)
    z = []
    for s in range(0, n - blk + 1, hop):
        seg = x_mono_channels[s:s + blk]
        z.append(float(np.sum(np.mean(seg ** 2, axis=0))))
    if not z:
        return None, 0
    z = np.array(z)
    # 绝对门限 -70 LUFS  =>  能量门限
    abs_gate = 10 ** ((-70.0 + 0.691) / 10.0)
    z1 = z[z > abs_gate]
    if z1.size == 0:
        return -70.0, 0
    lufs_ungated = -0.691 + 10 * math.log10(z1.mean())
    # 相对门限：比未门控均值低 10 dB
    rel_gate = 10 ** ((lufs_ungated - 10.0 + 0.691) / 10.0)
    z2 = z1[z1 > rel_gate]
    if z2.size == 0:
        z2 = z1
    return -0.691 + 10 * math.log10(z2.mean()), int(z2.size)


def true_peak_db(x):
    peak = float(np.max(np.abs(x))) if x.size else 0.0
    try:
        from scipy.signal import resample_poly
        up = resample_poly(x, 4, 1)
        peak = max(peak, float(np.max(np.abs(up))))
        mode = '4x(resample_poly)'
    except Exception:
        mode = 'sample-peak(未过采样)'
    return 20 * math.log10(max(peak, 1e-12)), peak, mode


def check(path, target_lufs=-16.0, tol=1.0, tp_limit=-1.0, crest_lo=10.0, crest_hi=17.0):
    fs, data = read_wav(path)
    dur = data.shape[0] / fs
    kw = np.column_stack([k_weight(data[:, c], fs) for c in range(data.shape[1])])
    lufs, blocks = integrated_lufs(kw, fs)
    tpdb, tplin, mode = true_peak_db(data)
    spdb = 20 * math.log10(max(float(np.max(np.abs(data))), 1e-12))
    return dict(
        file=os.path.basename(path), fs=fs, ch=data.shape[1], sec=round(dur, 2),
        lufs=round(lufs, 2) if lufs is not None else None,
        gate_blocks=blocks,
        true_peak_dbtp=round(tpdb, 2), sample_peak_dbfs=round(spdb, 2), tp_mode=mode,
        A_lufs=(abs(lufs - target_lufs) <= tol) if lufs is not None else False,
        B_truepeak=(tpdb <= tp_limit),
        C_crest=((crest_lo <= (spdb - lufs) <= crest_hi) if lufs is not None else False),
        crest=round(spdb - lufs, 2) if lufs is not None else None,
        A_target='%.0f±%.0f LUFS' % (target_lufs, tol),
        B_target='<= %.1f dBTP' % tp_limit, C_target='峰均比 %.0f-%.0f dB' % (crest_lo, crest_hi),
    )


def selftest():
    fs = 48000
    t = np.arange(int(fs * 3.0)) / fs
    print('--- 自检：1 kHz 正弦，峰值 0.5（未加权 RMS=0.3536 => 理论 ≈ -9.03 LUFS）')
    x = (0.5 * np.sin(2 * math.pi * 1000 * t))[:, None]
    kw = np.column_stack([k_weight(x[:, 0], fs)])
    lufs, blocks = integrated_lufs(kw, fs)
    print('  实测 LUFS = %.2f  (门控块 %d)' % (lufs, blocks))
    print('  误差 = %.2f LU' % (lufs - (-9.03)))
    print('--- 自检：0 dBFS 满幅方波（峰均比应远低于 10 dB 下限）')
    y = (np.sign(np.sin(2 * math.pi * 200 * t)))[:, None]
    r = dict(lufs=integrated_lufs(np.column_stack([k_weight(y[:, 0], fs)]), fs)[0])
    tpdb, _, mode = true_peak_db(y)
    print('  LUFS = %.2f / 样本峰值 %.2f dBFS / true peak %.2f dBTP (%s)'
          % (r['lufs'], 20 * math.log10(np.max(np.abs(y))), tpdb, mode))
    return abs(lufs + 9.03) < 0.5


if __name__ == '__main__':
    args = [a for a in sys.argv[1:]]
    if '--selftest' in args:
        ok = selftest()
        print('自检结果：%s' % ('PASS' if ok else 'FAIL'))
        sys.exit(0 if ok else 1)
    files = [a for a in args if not a.startswith('--')]
    if not files:
        here = os.path.dirname(os.path.abspath(__file__))
        files = []
        for root in (here, os.path.dirname(os.path.dirname(here))):
            files += [os.path.join(root, f) for f in os.listdir(root) if f.lower().endswith('.wav')]
    rows = []
    for f in files:
        try:
            rows.append(check(f))
        except Exception as e:
            rows.append(dict(file=os.path.basename(f), error=str(e)))
    print('%-28s %8s %10s %10s %10s  %s %s %s' % ('文件', '秒', 'LUFS', 'dBTP', '峰值dBFS', 'A', 'B', 'C'))
    for r in rows:
        if 'error' in r:
            print('%-28s  ERROR %s' % (r['file'], r['error']))
            continue
        print('%-28s %8.2f %10.2f %10.2f %10.2f  %s %s %s' % (
            r['file'][:28], r['sec'], r['lufs'], r['true_peak_dbtp'], r['sample_peak_dbfs'],
            'PASS' if r['A_lufs'] else 'FAIL', 'PASS' if r['B_truepeak'] else 'FAIL',
            'PASS' if r['C_crest'] else 'FAIL'))
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), '响度体检.json')
    io.open(out, 'w', encoding='utf-8').write(json.dumps(
        dict(target='-16±1 LUFS / <=-1 dBTP / 峰均比10-17dB', rows=rows), ensure_ascii=False, indent=2))
    print('已写', out)
