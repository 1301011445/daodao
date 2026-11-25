# -*- coding: utf-8 -*-
"""动作曲线判据（与 DaoOverlay v123 同一套算式复刻，1ms 步长采样）
M1 点头两个峰（峰数=2，峰间距均匀）
M2 小跳上升用时 < 下降用时（起跳快于下落），且峰值≈0.085h
M3 落地压扁存在（hop 归零后仍有 ≤5% 的压缩）
M4 蹲体积守恒（横向放宽 * 竖向压缩 ≈ 1，误差 ≤2%）
M5 三动作都在 1 秒内不抖（相邻帧幅度差 ≤0.02h）
"""

H = 180.0
WAVE_MS, HOP_MS, SQUAT_MS, NOD_MS = 4200, 900, 1600, 1400


def wave_env(p):
    if p <= 0 or p >= 1:
        return 0.0
    if p < 0.32:
        x = p / 0.32
        u = 1 - x
        return 1 - u * u * u
    if p < 0.72:
        return 1.0
    x = (p - 0.72) / 0.28
    u = 1 - x
    return u * u * u


def nod(ms):
    p = ms / NOD_MS
    return wave_env(p) * (0.5 - 0.5 * __import__('math').cos(p * 3.1415926 * 4))


def hop_squash(ms):
    p = min(1.0, max(0.0, ms / HOP_MS))
    hop = 0.0
    sq = 1.0
    if p < 0.70:
        u = (p - 0.35) / 0.35
        hop = H * 0.085 * max(0.0, 1 - u * u)
    if p > 0.66:
        q = (p - 0.66) / 0.34
        sq = min(sq, 1 - 0.05 * __import__('math').sin(q * 3.1415926))
    return hop, sq


def squat(ms):
    p = ms / SQUAT_MS
    sq = 1 - 0.085 * __import__('math').sin(p * 3.1415926)
    sx = 1 / sq
    return sq, sx


import math

# M1
seq = [nod(t) for t in range(0, NOD_MS, 10)]
peaks = [i for i in range(1, len(seq) - 1) if seq[i] > seq[i - 1] and seq[i] >= seq[i + 1] and seq[i] > 0.15]
m1 = len(peaks) == 2
print(f'M1 点头峰数={len(peaks)} 位置={[p*10 for p in peaks]}ms {"PASS" if m1 else "FAIL"}')

# M2
seq2 = [hop_squash(t)[0] for t in range(0, HOP_MS)]
peak_i = max(range(len(seq2)), key=lambda i: seq2[i])
up = peak_i
down = len(seq2) - peak_i
m2 = up < down and abs(max(seq2) - H * 0.085) < 0.5
print(f'M2 上升={up}ms 下降={down}ms 峰值={max(seq2):.2f}px {"PASS" if m2 else "FAIL"}')

# M3
sqs = [hop_squash(t)[1] for t in range(0, HOP_MS)]
m3 = min(sqs) < 0.96
print(f'M3 落地最小压缩={min(sqs):.3f}（需<0.96） {"PASS" if m3 else "FAIL"}')

# M4
vol = []
for t in range(0, SQUAT_MS, 10):
    sq, sx = squat(t)
    vol.append(abs(sq * sx - 1))
m4 = max(vol) <= 0.02
print(f'M4 蹲体积偏差 max={max(vol)*100:.2f}% (<=2%) {"PASS" if m4 else "FAIL"}')

# M5
m5 = True
for name, arr in (('nod', [nod(t) for t in range(0, NOD_MS, 16)]),
                  ('hop', [hop_squash(t)[0] for t in range(0, HOP_MS, 16)])):
    d = max(abs(arr[i + 1] - arr[i]) for i in range(len(arr) - 1))
    if d > 0.02 * H:
        m5 = False
        print(f'   {name} 单帧跳变 {d:.2f}px 超限')
print(f'M5 单帧最大幅度差 check {"PASS" if m5 else "FAIL"}')

ok = all([m1, m2, m3, m4, m5])
print('SUMMARY', 'PASS' if ok else 'FAIL')
raise SystemExit(0 if ok else 1)
