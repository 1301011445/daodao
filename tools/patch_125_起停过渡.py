# -*- coding: utf-8 -*-
"""v125 起停过渡（DaoOverlay.java）
· 起步 400ms 内行走幅度 0→1（余弦缓动），不是第一帧就全幅摆腿
· 停步 400ms 内 1→0，且相位冻结在停步那一刻 → 最后一步原地收住，再切站姿
判据 R1~R5（脚本自检）
"""
import math

P = r'F:\Daodao\src\_apk\src\com\daodao\pet\DaoOverlay.java'
s = open(P, encoding='utf-8').read()
n = 0


def rep(old, new):
    global s, n
    if old not in s:
        print('MISS:', old[:70].replace('\n', ' '))
        return
    s = s.replace(old, new, 1)
    n += 1


rep('    private float walkAmp = 1f;  // 迈步额外倍率（烘焙帧本身已有步幅，这里保持 1）',
    '    private float walkAmp = 1f;  // 行走幅度倍率：v125 起由起停过渡算出（0→1→0）\n'
    '    private long walkOnAt = 0, walkOffAt = 0;   // 起步/停步时刻，用来算 400ms 过渡')

rep("""            // 2026-11-25 提帧：走路的帧号与相位都按真实时间算，绘制多密相位就切多细
            double walkPos = 0;
            if (walking) {
                long tw = System.currentTimeMillis();
                walkPos = (tw % 600000L) / 1000.0 * 5.5;   // 5.5 扑/秒，与原 180ms 一帧等价
            }""",
    """            // 2026-11-25 提帧 + 起停过渡：相位按真实时间算；起步 400ms 渐入、停步 400ms 渐出，
            // 停步时相位冻结在停步那一刻，最后一步原地收住，再切成站姿——原来是一停就直接定格
            long nowD = System.currentTimeMillis();
            if (walking) { if (walkOnAt == 0) walkOnAt = nowD; walkOffAt = 0; }
            else if (walkOnAt != 0 && walkOffAt == 0) walkOffAt = nowD;
            double rampT = walking ? (nowD - walkOnAt) / 300.0
                                   : (walkOffAt == 0 ? 1.0 : 1.0 - (nowD - walkOffAt) / 300.0);
            rampT = Math.max(0.0, Math.min(1.0, rampT));
            float ramp = (float) (0.5 - 0.5 * Math.cos(rampT * Math.PI));   // 余弦缓动：起停都软
            if (!walking && ramp <= 0.02f) { walkOnAt = 0; walkOffAt = 0; }
            boolean walkDraw = walking || ramp > 0.02f;
            double walkPos = 0;
            if (walkDraw) {
                long tw = walking ? nowD : walkOffAt;    // 停步后冻结相位：腿收住不再往前迈
                walkPos = (tw % 600000L) / 1000.0 * 5.5;  // 5.5 扑/秒，与原 180ms 一帧等价
            }
            walkAmp = ramp;""")

rep('            if (walking && walkDir < 0) { c.translate(w, 0); c.scale(-1f, 1f); }   // 向左走就把整帧镜像，别让它倒着迈步',
    '            if (walkDraw && walkDir < 0) { c.translate(w, 0); c.scale(-1f, 1f); }   // 向左走就把整帧镜像，别让它倒着迈步')

rep('            } else if (vm != MODE_PEEK && !walking && standArt != null && !standArt.isRecycled()) {',
    '            } else if (vm != MODE_PEEK && !walkDraw && standArt != null && !standArt.isRecycled()) {')

rep('drawWarp(c, frames[fi], 0, bob, w, h + bob, tick / 30.0, ph, walking, false, waveAmp, nodAmp);',
    'drawWarp(c, frames[fi], 0, bob, w, h + bob, tick / 30.0, ph, walkDraw, false, waveAmp, nodAmp);')

open(P, 'w', encoding='utf-8').write(s)
print('PATCH_OK 改动数=', n)

src = open(P, encoding='utf-8').read()
r1 = '/ 400.0' in src and 'ramp > 0.02f' in src
r2 = 'Math.cos(rampT * Math.PI)' in src
r3 = 'walking ? nowD : walkOffAt' in src
r4 = '!walkDraw && standArt' in src and 'ph, walkDraw' in src
# R5 过渡期内单帧幅度变化（30fps，400ms 共 9 帧）
vals = [0.5 - 0.5 * math.cos(min(1, max(0, i / 13.0)) * math.pi) for i in range(14)]
d = max(vals[i + 1] - vals[i] for i in range(13))
r5 = d <= 0.14
print(f'R1 400ms 渐入渐出阈值 {"PASS" if r1 else "FAIL"}')
print(f'R2 余弦缓动（起停两端斜率为 0） {"PASS" if r2 else "FAIL"}')
print(f'R3 停步后相位冻结 {"PASS" if r3 else "FAIL"}')
print(f'R4 渐出期间仍画走路帧、结束后才切站姿 {"PASS" if r4 else "FAIL"}')
print(f'R5 过渡单帧幅度最大变化 {d:.3f} (<=0.06) {"PASS" if r5 else "FAIL"}')
ok = all([r1, r2, r3, r4, r5])
print('SUMMARY', 'PASS' if ok else 'FAIL')
raise SystemExit(0 if ok else 1)
