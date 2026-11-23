# -*- coding: utf-8 -*-
"""播一个 mp3/wav（兼容旧的 play.ps1 调用）。
本机 miniaudio 解不了 mp3，主路径用 soundfile；播完打印 PLAYED。"""
import sys
import numpy as np
import sounddevice as sd


def main():
    if len(sys.argv) < 2:
        sys.exit(1)
    p = sys.argv[1]
    try:
        import soundfile as sf
        x, sr = sf.read(p, dtype="float32", always_2d=False)
    except Exception:
        import miniaudio
        d = miniaudio.decode_file(p, output_format=miniaudio.SampleFormat.FLOAT32)
        x = np.frombuffer(d.samples, dtype=np.float32).copy().reshape(-1, d.nchannels)
        sr = d.sample_rate
    sd.play(np.clip(x, -1, 1), sr)
    sd.wait()
    print("PLAYED")


if __name__ == "__main__":
    main()
