# -*- coding: utf-8 -*-
"""把成品 wav 压成手机能自己放的小体积音频（IMA ADPCM 4:1）。
为什么不用 mp3：本机没有 ffmpeg/lame，装编码器又要动系统盘；
IMA ADPCM 纯 stdlib 就能编，安卓/WebAudio 端自己解码即可。

文件格式（自定，简单到不会写错）：
  头 12 字节：magic 'DAO1' + 采样率(uint32) + 帧数(uint32)
  每帧 1028 字节 = 头 4 字节（predictor int16, stepIndex uint8, 保留 uint8）
                + 2048 个 sample 的 nibble（1024 字节）
  每帧独立重置差分器：解码端只需要记住上一帧的 predictor/index。

用法：
  python adpcm.py enc  in.wav out.adp      # 编码并报 SNR
  python adpcm.py dec  in.adp  out.wav     # 解码（自检用）
  python adpcm.py snr  a.wav   b.wav       # 两段 wav 比 SNR
"""
import sys
import wave
import struct
import array
import math

FRAME = 2048
FRAME_BYTES = 4 + FRAME // 2   # 4 字节帧头 + 每样本半字节
MAGIC = b"DAO1"

# IMA ADPCM 标准步长表
STEPS = [
    7, 8, 9, 10, 11, 12, 13, 14, 16, 17, 19, 21, 23, 25, 28, 31,
    34, 37, 41, 45, 50, 55, 60, 66, 73, 80, 88, 97, 107, 118, 130, 143,
    157, 173, 190, 209, 230, 253, 279, 307, 337, 371, 408, 449, 494, 544,
    598, 658, 724, 796, 876, 963, 1060, 1166, 1282, 1411, 1552, 1707,
    1878, 2066, 2272, 2499, 2749, 3024, 3327, 3660, 4026, 4428, 4871,
    5358, 5894, 6484, 7132, 7845, 8630, 9493, 10442, 11487, 12635,
    13899, 15289, 16818, 18500, 20350, 22385, 24623, 27086, 29794, 32767]
INDEX = [-1, -1, -1, -1, 2, 4, 6, 8, -1, -1, -1, -1, 2, 4, 6, 8]


def encode_frame(pcm, pred, idx):
    """返回 (1024 字节 nibble 数据, 新 pred, 新 idx)"""
    out = bytearray()
    for i in range(0, len(pcm), 2):
        nib = bytearray()
        for k in range(2):
            if i + k < len(pcm):
                s = pcm[i + k]
                step = STEPS[idx]
                diff = s - pred
                code = 0
                if diff < 0:
                    code |= 8
                    diff = -diff
                tmp = step
                if diff >= tmp:
                    code |= 4; diff -= tmp
                tmp >>= 1
                if diff >= tmp:
                    code |= 2; diff -= tmp
                tmp >>= 1
                if diff >= tmp:
                    code |= 1
                # 还原
                step2 = STEPS[idx]
                delta = step2 >> 3
                if code & 4: delta += step2
                if code & 2: delta += step2 >> 1
                if code & 1: delta += step2 >> 2
                if code & 8: pred -= delta
                else: pred += delta
                pred = max(-32768, min(32767, pred))
                idx = max(0, min(88, idx + INDEX[code & 7]))
                nib.append(code & 0xF)
            else:
                nib.append(0)
        out.append((nib[0] << 4) | nib[1])
    return out, pred, idx


def decode_frame(data, pred, idx):
    pcm = array.array('h')
    for b in data:
        for code in ((b >> 4) & 0xF, b & 0xF):
            step = STEPS[idx]
            delta = step >> 3
            if code & 4: delta += step
            if code & 2: delta += step >> 1
            if code & 1: delta += step >> 2
            if code & 8: pred -= delta
            else: pred += delta
            pred = max(-32768, min(32767, pred))
            idx = max(0, min(88, idx + INDEX[code & 7]))
            pcm.append(pred)
    return pcm, pred, idx


def read_wav(path):
    w = wave.open(path, 'rb')
    nch, sw, sr, n = w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()
    data = w.readframes(n)
    w.close()
    pcm = array.array('h')
    pcm.frombytes(data)
    if nch > 1:
        # 取第一条通道
        pcm = array.array('h', pcm[0::nch])
    return pcm, sr


def snr(a, b):
    n = min(len(a), len(b))
    sig = sum(float(a[i]) ** 2 for i in range(n))
    err = sum(float(a[i] - b[i]) ** 2 for i in range(n))
    if err <= 0: return 99.0
    if sig <= 0: return -99.0
    return 10.0 * math.log10(sig / err)


def cmd_enc(inp, outp):
    pcm, sr = read_wav(inp)
    frames = []
    pred, idx = 0, 0
    recon = array.array('h')
    for st in range(0, len(pcm), FRAME):
        chunk = pcm[st:st + FRAME]
        # 每帧用它自己第一样本做 predictor，误差最小
        pred = chunk[0] if len(chunk) else 0
        idx = 0
        data, pred2, idx2 = encode_frame(chunk, pred, idx)
        frames.append(struct.pack('<hBB', chunk[0] if len(chunk) else 0, 0, 0) + data)
        d, _, _ = decode_frame(data, chunk[0] if len(chunk) else 0, 0)
        recon.extend(d)
    with open(outp, 'wb') as f:
        f.write(MAGIC + struct.pack('<II', sr, len(frames)))
        for fr in frames:
            f.write(fr)
    print("编码完成 %s -> %s | %d Hz | %.2f 秒 | %d 帧 | 输入 %d 字节 输出 %d 字节（%.2f:1）"
          % (inp, outp, sr, len(pcm) / float(sr), len(frames), len(pcm) * 2,
             len(frames) * FRAME_BYTES, (len(pcm) * 2) / float(len(frames) * FRAME_BYTES)))
    print("SNR %.1f dB" % snr(pcm, recon))
    return snr(pcm, recon)


def cmd_dec(inp, outp):
    with open(inp, 'rb') as f:
        blob = f.read()
    assert blob[:4] == MAGIC, "不是丁丁的 adp 文件"
    sr, nf = struct.unpack('<II', blob[4:12])
    pos = 12
    pcm = array.array('h')
    for _ in range(nf):
        pred, idx, _r = struct.unpack('<hBB', blob[pos:pos + 4])
        end = min(pos + FRAME_BYTES, len(blob))      # 末帧可能不满一整帧
        d, _, _ = decode_frame(blob[pos + 4:end], pred, idx)
        pcm.extend(d)
        pos += FRAME_BYTES
    w = wave.open(outp, 'wb'); w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
    w.writeframes(pcm.tobytes()); w.close()
    print("解码完成 %s -> %s | %d Hz | %.2f 秒" % (inp, outp, sr, len(pcm) / float(sr)))


def cmd_snr(a, b):
    pa, _ = read_wav(a); pb, _ = read_wav(b)
    print("SNR %.1f dB（%d vs %d 样本）" % (snr(pa, pb), len(pa), len(pb)))


if __name__ == '__main__':
    if len(sys.argv) < 4:
        print(__doc__); sys.exit(2)
    {'enc': cmd_enc, 'dec': cmd_dec, 'snr': cmd_snr}[sys.argv[1]](sys.argv[2], sys.argv[3])
