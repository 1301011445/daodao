# -*- coding: utf-8 -*-
"""把试听 wav 转成人人能放的 mp3，并合成一条对比合集（每档 14 秒 + 1 秒间隔，音量对齐）。
用法： set PYTHONPATH=F:\\Daodao\\tools\\_py_libs  然后 python 转mp3.py
"""
import os, sys
import numpy as np
import soundfile as sf
import lameenc

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out')
LABELS = [('单依纯', '试听_单依纯.wav'), ('王菲', '试听_王菲.wav'),
          ('李健', '试听_李健.wav'), ('那英', '试听_那英.wav')]
SEG = 14.0          # 每档截 14 秒
GAP = 1.0           # 档间空 1 秒
TARGET = 20000      # 统一峰值（约 -4 dBFS，16 bit 上限 32767）


def load(p):
    x, sr = sf.read(p, dtype='float32')
    if x.ndim > 1:
        x = x.mean(axis=1)
    return x, sr


def trim(x, sr):
    # 掐掉首尾静音（-45 dBFS 以下算静音）
    e = np.abs(x)
    thr = 10 ** (-45 / 20.0)
    idx = np.where(e > thr)[0]
    if len(idx) == 0:
        return x
    return x[max(0, idx[0] - int(sr * 0.02)): idx[-1] + int(sr * 0.05)]


def encode(x, sr, path):
    x = np.clip(x, -1, 1)
    pcm = (x * 32767).astype(np.int16)
    enc = lameenc.Encoder()
    enc.set_bit_rate(192)
    enc.set_in_sample_rate(int(sr))
    enc.set_channels(1)
    enc.set_quality(2)
    data = enc.encode(pcm.tobytes()) + enc.flush()
    with open(path, 'wb') as f:
        f.write(data)


def main():
    segs, sr0 = [], None
    for label, fn in LABELS:
        p = os.path.join(OUT, fn)
        if not os.path.exists(p):
            print('缺文件', p); continue
        x, sr = load(p)
        sr0 = sr
        x = trim(x, sr)[: int(SEG * sr)]
        if len(x) < int(SEG * sr) * 0.6:
            print(label, '内容太短，照原长用')
        pk = float(np.abs(x).max()) or 1.0
        x = x / pk
        segs.append(x)
        encode(x * 0.5, sr, os.path.join(OUT, f'试听_{label}.mp3'))
        print('mp3 写出', label, round(len(x) / sr, 2), '秒')
    if not segs:
        return
    sr = sr0
    gap = np.zeros(int(GAP * sr), dtype=np.float32)
    # 每档前面再留 0.5 秒起头空白，方便听出"下一档开始了"
    lead = np.zeros(int(0.5 * sr), dtype=np.float32)
    allx = []
    for s in segs:
        allx += [lead, s, gap]
    comp = np.concatenate(allx).astype(np.float32)
    encode(comp, sr, os.path.join(OUT, '唱法对比_合集.mp3'))
    print('合集', round(len(comp) / sr, 2), '秒')


sys.path.insert(0, r'F:\Daodao\tools\_py_libs')
main()
