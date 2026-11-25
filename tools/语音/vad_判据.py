# -*- coding: utf-8 -*-
"""第5类（Whisper / sherpa-onnx / Vosk）判据：V5-1 ~ V5-7
真跑：python F:\Daodao\tools\语音\vad_判据.py
判的是"道"自己的 VAD（src\桌面分身\hear.py 的 VadGate）+ 唤醒能量门（pet.cs）。
"""
import io
import os
import re
import sys

ROOT = r'F:\Daodao'
sys.path.insert(0, os.path.join(ROOT, 'src', '桌面分身'))
import hear  # noqa: E402

BLK = hear.VAD_WIN


def run(seq, sil=hear.VAD_STOP_SIL, thresh=None, max_sec=6.0):
    """seq = [(rms, low_pct)]，返回 (收尾用时秒, 是否判成一句话, 说话起点秒)"""
    g = hear.VadGate(block=BLK, sil_sec=sil, thresh=thresh)
    stop_t = None
    for rms, low in seq:
        g.feed(rms, low)
        if g.should_stop(g.t):
            stop_t = g.t
            break
        if g.t >= max_sec:
            break
    return (None if stop_t is None else stop_t), g.spoke, g.onset_t


def seq_speech(speech_sec, tail_sec, rms=900, low=8.0):
    return [(rms, low)] * int(speech_sec / BLK) + [(float(hear.VAD_OFF_RMS) * 0.6, 2.0)] * int(tail_sec / BLK)


def main():
    res = []

    # V5-1 一句 0.6 秒说完 → 收尾延迟（静音 0.45 + 32ms 块）应 ≤ 0.55 秒
    t, spoke, onset = run(seq_speech(0.6, 1.2))
    lat = None if t is None else (t - 0.6)
    res.append(('V5-1 端点收尾延迟 ≤0.55s（实测 %.3fs）' % (lat if lat is not None else -1),
                lat is not None and lat <= 0.55 and spoke))

    # V5-2 只有 0.12 秒的咔哒（响，但没有后续）→ 不许判成一句话
    click = [(1500.0, 8.0)] * int(0.12 / BLK) + [(120.0, 2.0)] * int(1.0 / BLK)
    t2, spoke2, _ = run(click)
    res.append(('V5-2 0.12s 咔哒不算一句话', spoke2 is False and t2 is None))

    # V5-3 连续说 4 秒 → 不许提前断
    t3, spoke3, _ = run(seq_speech(4.0, 1.2), max_sec=6.0)
    res.append(('V5-3 说 4 秒不被提前截断', spoke3 and t3 is not None and t3 >= 4.4))

    # V5-4 底噪 200、频带占比 2.5% → 一直不说话，不许误触发
    noise = [(200.0, 2.5)] * int(3.0 / BLK)
    t4, spoke4, _ = run(noise)
    res.append(('V5-4 底噪抬到 200 不误触发', spoke4 is False and t4 is None))

    # V5-5 底噪 200 之后人说 0.8 秒 → 仍要认出来，且收尾 ≤0.55s
    seq5 = [(200.0, 2.5)] * int(1.0 / BLK) + [(800.0, 8.0)] * int(0.8 / BLK) + [(110.0, 2.0)] * int(1.2 / BLK)
    t5, spoke5, _ = run(seq5)
    lat5 = None if t5 is None else (t5 - 1.8)
    res.append(('V5-5 底噪 200 下人声仍认出（收尾 %.3fs）' % (lat5 if lat5 is not None else -1),
                spoke5 and lat5 is not None and lat5 <= 0.55))

    # V5-6 代码层：窗口/最短语音/收尾静音参数在 silero-sherpa 档位内
    hp = io.open(os.path.join(ROOT, 'src', '桌面分身', 'hear.py'), encoding='utf-8').read()
    ok6 = (hear.VAD_WIN <= 0.04 and 0.2 <= hear.VAD_MIN_SPEECH <= 0.3 and 0.4 <= hear.VAD_STOP_SIL <= 0.5
           and 'class VadGate' in hp and 'gate.feed(' in hp and 'gate.should_stop(' in hp)
    res.append(('V5-6 参数在档位内（窗 %.0fms/最短语音 %.0fs/收尾 %.2fs）' % (
        hear.VAD_WIN * 1000, hear.VAD_MIN_SPEECH, hear.VAD_STOP_SIL), ok6))

    # V5-7 唤醒能量门：pet.cs 已从死数 120 改成跟噪声底走
    pc = io.open(os.path.join(ROOT, 'src', '桌面分身', 'pet.cs'), encoding='utf-8').read()
    ok7 = ('wakeFloor' in pc and 'gate = wakeFloor * 1.7' in pc)
    res.append(('V5-7 唤醒门随噪声底自适应（pet.cs）', ok7))

    bad = 0
    for name, ok in res:
        print(('PASS ' if ok else 'FAIL ') + name)
        if not ok:
            bad += 1
    print('SUMMARY|%d/7|bad=%d' % (len(res) - bad, bad))
    return 0 if bad == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
