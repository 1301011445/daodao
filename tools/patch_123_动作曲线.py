# -*- coding: utf-8 -*-
"""v123 动作曲线优化补丁（DaoOverlay.java）
A) 小跳：sin 改成抛物线（起得急、顶点短停、落得快），并在落地段加一压
B) 点头：1.4 秒里真点两下（0→1→0→1→0 双臂），不再是单次起伏
C) 蹲一下：竖向压 8.5% 的同时横向放宽 4.7%，体积守恒，看着是"屈膝"不是"缩小"
"""
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


# A) 小跳抛物线 + 落地压
rep("""            if (nowMs < hopUntil) {
                float pr = 1f - (hopUntil - nowMs) / 900f;
                hop = (float) Math.sin(pr * Math.PI) * h * 0.085f;
            }""",
    """            if (nowMs < hopUntil) {
                float pr = 1f - (hopUntil - nowMs) / 900f;
                float px = Math.max(0f, Math.min(1f, pr));
                // 抛物线：0→0.35 迅速离地（起跳加速度大），0.35→0.70 落回（重力加速），
                // 比原来对称 sin 更像真跳——原来上下一样慢，看着像被人提着放下去
                if (px < 0.70f) {
                    float u = (px - 0.35f) / 0.35f;
                    hop = h * 0.085f * Math.max(0f, 1f - u * u);
                }
                // 落地那 0.3 秒压一下，给"落地有重量"的反馈
                if (px > 0.66f) {
                    float q = (px - 0.66f) / 0.34f;
                    squash = Math.min(squash, 1f - 0.05f * (float) Math.sin(q * Math.PI));
                }
            }""")

# B) 点头两次
rep("""                float prog2 = 1f - (nodUntil - nowMs) / 1400f;
                nodAmp = waveEnv(prog2);""",
    """                float prog2 = 1f - (nodUntil - nowMs) / 1400f;
                // 真点头是两下：包络里套 2 个周期的余弦，0→1→0→1→0，峰在 1/4、3/4 处
                nodAmp = waveEnv(prog2) * (0.5f - 0.5f * (float) Math.cos(prog2 * Math.PI * 4f));""")

# C) 蹲：横向放宽做体积守恒（放在 squash 算完之后、绘制之前）
rep("""            if (walking && walkDir < 0) { c.translate(w, 0); c.scale(-1f, 1f); }   // 向左走就把整帧镜像，别让它倒着迈步""",
    """            if (squash < 1f) {   // 蹲：压扁的同时横向放宽，体积守恒 → 看着是屈膝，不是整体缩小
                float sx2 = 1f + (1f - squash) * 0.55f;
                c.translate(w * 0.5f, 0);
                c.scale(sx2, 1f);
                c.translate(-w * 0.5f, 0);
            }
            if (walking && walkDir < 0) { c.translate(w, 0); c.scale(-1f, 1f); }   // 向左走就把整帧镜像，别让它倒着迈步""")

open(P, 'w', encoding='utf-8').write(s)
print('PATCH_OK 改动数=', n)
