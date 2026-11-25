# -*- coding: utf-8 -*-
"""v124 提帧（DaoOverlay.java）
A) 心跳：33ms 重绘（30fps），逻辑仍按 90ms（beatN%3 才做一次 tick 逻辑）
B) 走路帧与相位改成按真实时间算：姿势 5.5 扑/秒（与原来 180ms 一帧一致），相位连续
判据（脚本自检源码）：
 P1 重绘 33ms 出现、逻辑 90ms 被 beatN%3 守住
 P2 相位按 walkPos 连续算，不再用离散 fi
 P3 姿势频率 5.5/s → 30fps 下每帧相位步长 ≈0.144 rad（≤0.16）
 P4 一个走路周期 1.4545s，30fps 下 44 帧（原来 11fps 只有 16 帧）
 P5 fi 与 ph 用同一时间基 walkPos（换帧那一刻相位正好到整数，不会跳）
"""
import math

P = r'F:\Daodao\src\_apk\src\com\daodao\pet\DaoOverlay.java'
s = open(P, encoding='utf-8').read()
n = 0


def rep(old, new):
    global s, n
    if old not in s:
        print('MISS:', old[:60].replace('\n', ' '))
        return
    s = s.replace(old, new, 1)
    n += 1


# 字段
rep('    private long tick = 0;',
    '    private long tick = 0;\n    private int beatN = 0;   // 2026-11-25 提帧：33ms 重绘计数，3 拍做一次 90ms 的逻辑')

# 心跳：先重绘，再按 3 拍做逻辑
rep("""            public void run() {
                tick++;
                try {
                    if (pv != null && added) pv.invalidate();
                } catch (Exception e) { }""",
    """            public void run() {
                try {
                    if (pv != null && added) pv.invalidate();
                } catch (Exception e) { }
                // 2026-11-25 提帧：画 30fps（33ms），逻辑还是 90ms 一次——直接把 tick 加快会把
                // 走路速度、打招呼间隔全带快 3 倍，所以做成"多画、少算"
                if (++beatN % 3 != 0) { ui.postDelayed(this, 33); return; }""")

rep('                ui.postDelayed(this, 90);', '                ui.postDelayed(this, 33);')

# 走路帧/相位按真实时间
rep("""            int fi;
            int bob;""",
    """            // 2026-11-25 提帧：走路的帧号与相位都按真实时间算，绘制多密相位就切多细
            double walkPos = 0;
            if (walking) {
                long tw = System.currentTimeMillis();
                walkPos = (tw % 600000L) / 1000.0 * 5.5;   // 5.5 扑/秒，与原 180ms 一帧等价
            }
            int fi;
            int bob;""")

rep('                    fi = fN > 0 ? (int) ((tick / 2) % fN) : 0;',
    '                    fi = fN > 0 ? (int) (walkPos % fN) : 0;')

rep('                float ph = (float) ((fi / (float) Math.max(1, fN)) * Math.PI * 2.0);',
    '                float ph = (float) ((walkPos % fN) / Math.max(1, fN) * Math.PI * 2.0);   // 连续相位：换帧处正好归整')

open(P, 'w', encoding='utf-8').write(s)
print('PATCH_OK 改动数=', n)

# ---- 自检 ----
src = open(P, encoding='utf-8').read()
p1 = 'ui.postDelayed(this, 33)' in src and 'beatN % 3 != 0' in src
p2 = 'walkPos % fN' in src and 'walkPos % fN) / Math.max' in src
hz = 5.5
fps = 1000.0 / 33
step = 2 * math.pi / (hz * fps)
p3 = step <= 0.16
cycle = 1.0 / hz * 8
frames = cycle * fps
p4 = frames >= 40
p5 = p2 and 'walkPos = (tw % 600000L)' in src
print(f'P1 33ms 重绘 + 90ms 逻辑 {"PASS" if p1 else "FAIL"}')
print(f'P2 相位连续（walkPos） {"PASS" if p2 else "FAIL"}')
print(f'P3 每帧相位步长 {step:.3f} rad (<=0.16) {"PASS" if p3 else "FAIL"}')
print(f'P4 一个走路周期 {cycle:.2f}s → {frames:.0f} 帧 (>=40) {"PASS" if p4 else "FAIL"}')
print(f'P5 fi/ph 同一时间基 {"PASS" if p5 else "FAIL"}')
ok = all([p1, p2, p3, p4, p5])
print('SUMMARY', 'PASS' if ok else 'FAIL')
raise SystemExit(0 if ok else 1)
