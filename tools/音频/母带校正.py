# -*- coding: utf-8 -*-
"""母带校正（2026-11-20 建）

为什么要有它：编配层次.render 只按峰值归一（PEAK_DBFS=-1.0），曲子内部电平一变，
成品 LUFS 就会飘（实测漂到 -14.4）。人耳感知的是响度不是峰值，所以要按 LUFS 收口。

规则（与 响度体检.py 同一口径，直接复用它算的 BS.1770 值）：
  1) 目标 -16.0 LUFS；若当前偏响，按差值整体降增益；
  2) 降完峰值必须仍 <= -1.0 dBFS（本来只会更低，不会更高）；
  3) 不往响里推（宁可略低，不靠削峰换响度），避免破坏峰均比与动态。

用法：
  python 母带校正.py <wav> [<wav> ...]      # 原地校正
  python 母带校正.py --check <wav>          # 只看差值，不改文件
"""
import importlib.util, io, math, os, sys, json

HERE = os.path.dirname(os.path.abspath(__file__))
TARGET_LUFS = -16.0
PEAK_LIMIT = -1.0


def _load(mod_name, filename):
    spec = importlib.util.spec_from_file_location(mod_name, os.path.join(HERE, filename))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def measure(path, loud):
    fs, data = loud.read_wav(path)
    kw = loud.np.column_stack([loud.k_weight(data[:, c], fs) for c in range(data.shape[1])])
    lufs, blocks = loud.integrated_lufs(kw, fs)
    tpdb, _, mode = loud.true_peak_db(data)
    spdb = 20 * math.log10(max(float(loud.np.max(loud.np.abs(data))), 1e-12))
    return dict(fs=fs, data=data, lufs=lufs, tpdb=tpdb, spdb=spdb, blocks=blocks, mode=mode)


def write_wav(path, fs, data, loud):
    import wave
    clip = loud.np.clip(data, -1.0, 1.0)
    pcm = (clip * 32767.0).astype('<i2').tobytes()
    w = wave.open(path, 'wb')
    w.setnchannels(data.shape[1]); w.setsampwidth(2); w.setframerate(fs)
    w.writeframes(pcm); w.close()


def correct(path, loud, check_only=False):
    m = measure(path, loud)
    if m['lufs'] is None:
        return dict(file=os.path.basename(path), error='静音/测不出 LUFS')
    need = TARGET_LUFS - m['lufs']                       # 负值=要降
    head = PEAK_LIMIT - m['spdb']                        # 峰值还剩多少余量
    gain = min(need, head) if need < 0 else min(0.0, head)   # 只降不升
    before = dict(lufs=round(m['lufs'], 2), dbtp=round(m['tpdb'], 2), peak=round(m['spdb'], 2))
    if not check_only and abs(gain) > 0.02:
        write_wav(path, m['fs'], m['data'] * (10 ** (gain / 20.0)), loud)
        m2 = measure(path, loud)
        after = dict(lufs=round(m2['lufs'], 2), dbtp=round(m2['tpdb'], 2), peak=round(m2['spdb'], 2),
                     crest=round(m2['spdb'] - m2['lufs'], 2))
    else:
        after = before
    return dict(file=os.path.basename(path), gain_db=round(gain, 2),
                before=before, after=after,
                ok=(abs(after['lufs'] - TARGET_LUFS) <= 1.0) and after['dbtp'] <= PEAK_LIMIT)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    check_only = '--check' in sys.argv
    if not args:
        print('用法：python 母带校正.py [--check] <wav> [...]'); return 1
    loud = _load('loud', '响度体检.py')
    rows = []
    for p in args:
        try:
            rows.append(correct(p, loud, check_only))
        except Exception as e:
            rows.append(dict(file=os.path.basename(p), error=str(e)))
    for r in rows:
        if 'error' in r:
            print('%-26s ERROR %s' % (r['file'][:26], r['error'])); continue
        print('%-26s 增益 %+5.2f dB | %s -> %s | %s'
              % (r['file'][:26], r['gain_db'], r['before'], r['after'],
                 'PASS' if r['ok'] else 'FAIL'))
    out = os.path.join(HERE, '母带校正.json')
    io.open(out, 'w', encoding='utf-8').write(json.dumps(
        dict(target_lufs=TARGET_LUFS, peak_limit=PEAK_LIMIT, rows=rows), ensure_ascii=False, indent=2))
    print('已写', out)
    return 0 if all(r.get('ok') for r in rows) else 1


if __name__ == '__main__':
    sys.exit(main())
