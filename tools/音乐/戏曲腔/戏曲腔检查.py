# -*- coding: utf-8 -*-
"""第32类 戏曲腔/唱腔声学判据检查（2026-11-20 建）

来源：
  1) Sundberg, J. (1994) Acoustic and psychoacoustic aspects of vocal vibrato, STL-QPSR
     https://www.speech.kth.se/qpsr/1994/1994_35_2-3_045-068.pdf
     结论：颤音速率 5–7 次/秒；深度 <±1 半音（<100 cents）；<5Hz 显拖沓、>8Hz 显神经质
  2) PMC8995401（颈部振动传感器测颤音）
     https://pmc.ncbi.nlm.nih.gov/articles/PMC8995401/pdf/nihms-1749158.pdf
     结论：f0 调制度 6–8%；强度调制 23–38%，速率 5–10Hz
  3) SciELO 嗓音训练（VoceVista 实测）
     https://scielo.br/j/rcefac/a/HTHm7J8dhbBJ7gMc6XMSNZP/
     结论：正常范围 Rate 5–7Hz、Extent ≤100 cents、起颤 onset 越低越好（实测 49–52ms）

判据（全部可脚本判）：
  P1 颤音速率 5.0–7.0 Hz
  P2 颤音深度（单侧幅度）25–100 cents
  P3 起颤时间 ≤120 ms
  P4 咬字起音（到 90% 峰值）≤80 ms（戏曲字头要快）
  P5 奇次泛音：3f + 5f 能量相对基频 ≥ -10 dB（戏腔那口尖亮）

方法说明（为什么这么量）：
  - 瞬时频率用帧长 512 / 补零到 32768 的谱峰 + 抛物线插值：22050Hz 采样下分辨率 0.67Hz，
    在 660Hz 上约 1.8 音分，够量 25–100 音分的颤音；解析信号法在多泛音信号上会失效，弃用。
  - 泛音幅度不用单点取值（f0 估偏 1% 时 3f 就偏 20Hz，会读低 15dB），改成目标频率 ±3% 内取峰。
"""
import importlib.util, io, json, math, os, struct, sys, wave
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ARR = os.path.join(HERE, '..', '编配对比', '编配层次.py')


def _load(mod_name, path):
    spec = importlib.util.spec_from_file_location(mod_name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def synth(arr, pitch=76, ch=5, amp=0.8):
    out = os.path.join(HERE, '_vibe_tmp.wav')
    arr.render([dict(t=0, dur=1920, pitch=pitch, ch=ch, amp=amp)], out)
    w = wave.open(out, 'rb'); n = w.getnframes()
    s = np.array(struct.unpack('<%dh' % n, w.readframes(n)), dtype=float) / 32767.0
    sr = w.getframerate(); w.close()
    return s, sr


def track_f0(x, sr, fmin=200, fmax=1200):
    fsize, hop, nfft = 512, 128, 32768
    win = np.hanning(fsize)
    fr = np.fft.rfftfreq(nfft, 1.0 / sr)
    band = (fr >= fmin) & (fr <= fmax)
    bw = np.where(band)[0]
    t, f = [], []
    peak_env = np.max(np.abs(x)) if len(x) else 1.0
    for st in range(0, len(x) - fsize, hop):
        seg = x[st:st + fsize]
        if np.sqrt(np.mean(seg ** 2)) < 0.25 * peak_env:
            continue
        mag = np.abs(np.fft.rfft(seg * win, nfft))[bw]
        k = int(np.argmax(mag))
        if 0 < k < len(mag) - 1:
            y0, y1, y2 = mag[k - 1], mag[k], mag[k + 1]
            d = 0.5 * (y0 - y2) / (y0 - 2 * y1 + y2 + 1e-12)
        else:
            d = 0.0
        t.append(st / float(sr))
        f.append(fr[bw[k]] + d * (fr[1] - fr[0]))
    return np.array(t), np.array(f)


def analyze(x, sr):
    # 起音：1ms 窗包络到 90% 峰值
    w1 = int(sr * 0.001)
    env = np.array([np.mean(np.abs(x[i:i + w1])) for i in range(0, len(x) - w1, w1)])
    pk = env.max()
    attack_ms = float(np.argmax(env >= pk * 0.9)) * 1.0

    t, f = track_f0(x, sr)
    f0 = float(np.median(f))
    cents = 1200.0 * np.log2(f / f0)
    # 只取稳定段（跳过前 200ms 的上滑入腔），不做趋势滤波——
    # 中值/滑动平均会把 6.4Hz 的颤音本身滤掉（实测会把 25 音分压成 9 音分），这是踩过的坑
    keep = t >= 0.2
    dev = cents[keep] - np.median(cents[keep])
    t_keep = t[keep]

    # 颤音速率与深度
    sig = dev - dev.mean()
    sp = np.abs(np.fft.rfft(sig * np.hanning(len(sig))))
    frm = np.fft.rfftfreq(len(sig), (t[1] - t[0]))
    band = (frm >= 2.0) & (frm <= 14.0)
    rate = float(frm[band][int(np.argmax(sp[band]))]) if band.sum() > 1 else 0.0
    depth = float((np.percentile(dev, 97) - np.percentile(dev, 3)) / 2.0)

    # 起颤：在 cents 轨迹上带通 4–9Hz，取滑动 RMS 包络，首次到最终幅度 60% 的时刻
    sig_all = cents - np.median(cents)
    sp_all = np.fft.rfft(sig_all)
    fr_all = np.fft.rfftfreq(len(sig_all), (t[1] - t[0]))
    sp_all[~((fr_all >= 4.0) & (fr_all <= 9.0))] = 0
    bp = np.fft.irfft(sp_all, len(sig_all))
    w = 48                      # 2 个颤音周期（6.4Hz ≈ 156ms/周期），窗内 RMS 才稳定
    half = w // 2
    amp = np.array([np.sqrt(np.mean(bp[i - half:i + half] ** 2)) for i in range(half, len(bp) - half)])
    final_amp = float(np.median(amp[-40:]))
    over = np.where(amp >= final_amp * 0.6)[0]
    # 取窗「前沿」而不是窗中心作为起颤时刻（保守估，不会把起颤报早）
    onset_ms = float(over[0] * (t[1] - t[0]) * 1000.0) if len(over) else 9999.0

    # 奇次泛音：中段 8192 点，±3% 窗口取峰
    mid = len(x) // 2
    seg = x[mid - 4096: mid + 4096]
    mag = np.abs(np.fft.rfft(seg * np.hanning(len(seg)), 65536))
    fr2 = np.fft.rfftfreq(65536, 1.0 / sr)

    def peak_at(hz):
        m = (fr2 >= hz * 0.97) & (fr2 <= hz * 1.03)
        return float(mag[m].max()) if m.any() else 1e-12

    a1, a3, a5 = peak_at(f0), peak_at(3 * f0), peak_at(5 * f0)
    odd_db = 20 * math.log10(max(a3 + a5, 1e-12) / max(a1, 1e-12))

    return dict(f0=round(f0, 1), attack_ms=round(attack_ms, 1),
                vibrato_rate_hz=round(rate, 2), vibrato_depth_cents=round(depth, 1),
                vibrato_onset_ms=round(onset_ms, 1), odd_harm_db=round(odd_db, 1))


def judge(m):
    return [
        ('P1 颤音速率 5.0–7.0 Hz', 5.0 <= m['vibrato_rate_hz'] <= 7.0, m['vibrato_rate_hz']),
        ('P2 颤音深度 25–100 cents', 25.0 <= m['vibrato_depth_cents'] <= 100.0, m['vibrato_depth_cents']),
        ('P3 起颤 ≤120 ms', m['vibrato_onset_ms'] <= 120.0, m['vibrato_onset_ms']),
        ('P4 咬字起音 ≤80 ms', m['attack_ms'] <= 80.0, m['attack_ms']),
        ('P5 奇次泛音 ≥-10 dB', m['odd_harm_db'] >= -10.0, m['odd_harm_db']),
    ]


def main():
    arr = _load('arr', ARR)
    x, sr = synth(arr)
    m = analyze(x, sr)
    print('══ 第32类 戏曲腔声学判据（ch=5，pitch=76，sr=%d）══' % sr)
    for k, v in m.items():
        print('  %-20s %s' % (k, v))
    ok = True
    for name, passed, val in judge(m):
        print('%s %-26s 实测 %s' % ('PASS' if passed else 'FAIL', name, val))
        ok = ok and passed
    print('汇总：%s' % ('全过' if ok else '有 FAIL，先改渲染参数再出片'))
    io.open(os.path.join(HERE, '戏曲腔检查.json'), 'w', encoding='utf-8').write(
        json.dumps(dict(measure=m, checks=[(n, bool(p), v) for n, p, v in judge(m)]),
                   ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
