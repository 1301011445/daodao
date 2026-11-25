# -*- coding: utf-8 -*-
"""v131 骑姿：有骑姿立绘的形象，骑上时直接画骑姿（跨坐、臀落鞍位），不再用站姿缩放糊
判据 G1~G5
"""
P = r'F:\Daodao\src\_apk\src\com\daodao\pet\DaoOverlay.java'
s = open(P, encoding='utf-8').read()
done = []


def rep(old, new, tag):
    global s
    if old not in s:
        print('MISS', tag)
        return False
    s = s.replace(old, new, 1)
    done.append(tag)
    return True


# 1) 配比表换成"骑姿版"（数值来自 _骑姿预览4.png）
rep('    private final float[] MOUNT_MHW = {0.28f, 0.40f, 0.24f, 0.34f, 0.40f};  // 坐骑高 / 视窗高\n'
    '    private final float[] MOUNT_FR = {0.86f, 0.60f, 0.45f, 0.58f, 0.38f};   // 脚踩高度 / 坐骑高（从底算）',
    '    private final float[] MOUNT_MHW = {0.32f, 0.52f, 0.34f, 0.50f, 0.46f};  // 坐骑高 / 视窗高（骑姿版）\n'
    '    private final float[] MOUNT_FR = {0.88f, 0.64f, 0.62f, 0.62f, 0.44f};   // 鞍面高度 / 坐骑高（从底算）\n'
    '    // v131 骑姿：臀部（坐骨线）落在鞍面；数值 = 坐骨线在骑姿图里占的高度比例\n'
    '    private final float RIDE_SEAT = 0.604f;\n'
    '    private final float RIDE_H = 0.62f;   // 骑姿人物高 / 视窗高', '配比表')

# 2) 加载三张骑姿
rep('''            for (int i = 0; i < MOUNT_FILES.length; i++) {
                mounts[i] = loadOpt(MOUNT_FILES[i]);
                if (mounts[i] != null && !mounts[i].isRecycled()) matteInPlace(mounts[i]);
            }''',
    '''            for (int i = 0; i < MOUNT_FILES.length; i++) {
                mounts[i] = loadOpt(MOUNT_FILES[i]);
                if (mounts[i] != null && !mounts[i].isRecycled()) matteInPlace(mounts[i]);
            }
            // v131：骑姿立绘（只有这三只形象有，别的仍用站姿）
            rideArt0 = loadOpt("ride_0.png");
            rideArt8 = loadOpt("ride_8.png");
            rideArt10 = loadOpt("ride_10.png");
            for (Bitmap rb : new Bitmap[]{ rideArt0, rideArt8, rideArt10 })
                if (rb != null && !rb.isRecycled()) matteInPlace(rb);''', '加载骑姿')

# 3) 字段
rep('    private Bitmap[] mounts = new Bitmap[MOUNT_FILES.length];',
    '    private Bitmap[] mounts = new Bitmap[MOUNT_FILES.length];\n'
    '    private Bitmap rideArt0, rideArt8, rideArt10;   // 骑姿立绘（橘猫少年 / 银发剑客 / 古风少女）', '字段')

# 4) onDraw 分支
rep('''            if (vm == MODE_BALL) { drawBall(c, w, h); return; }''',
    '''            if (vm == MODE_BALL) { drawBall(c, w, h); return; }

            // v131 骑乘：这只形象有骑姿立绘，就直接画"跨坐"的样子，不再拿站姿缩放去凑
            Bitmap rb = rideFor(art);
            if (mount > 0 && rb != null && !rb.isRecycled()
                    && mounts[mount] != null && !mounts[mount].isRecycled()) {
                drawRide(c, w, h, rb, mounts[mount]);
                return;
            }''', 'onDraw 分支')

# 5) 两个小方法（放在 setArt 之前）
rep('''        void setArt(int k) {''',
    '''        Bitmap rideFor(int k) {
            if (k == 0) return rideArt0;
            if (k == 8) return rideArt8;
            if (k == 10) return rideArt10;
            return null;
        }

        /** v131 骑姿绘制：坐骑按自己的高度比 → 鞍面定位 → 臀部（坐骨线）压上去 */
        void drawRide(Canvas c, int w, int h, Bitmap art, Bitmap mb) {
            int mi = Math.max(1, Math.min(MOUNT_MHW.length, mount)) - 1;
            float mh = h * MOUNT_MHW[mi];
            float mw = mh * mb.getWidth() / Math.max(1, mb.getHeight());
            if (mw > w * 0.98f) {
                mw = w * 0.98f;
                mh = mw * mb.getHeight() / Math.max(1, mb.getWidth());
            }
            Paint sp = new Paint(Paint.ANTI_ALIAS_FLAG);
            sp.setColor(0x22000000);
            c.drawOval(new RectF(w * 0.24f, h - h * 0.03f, w * 0.76f, h + h * 0.005f), sp);
            RectF mr = new RectF(w * 0.5f - mw * 0.5f, h - mh, w * 0.5f + mw * 0.5f, h);
            c.drawBitmap(mb, null, mr, p);

            float saddleY = h - mh * MOUNT_FR[mi];
            float rh = h * RIDE_H;
            float rw = rh * art.getWidth() / Math.max(1, art.getHeight());
            if (rw > w * 0.92f) {
                rw = w * 0.92f;
                rh = rw * art.getHeight() / Math.max(1, art.getWidth());
            }
            float top = saddleY - rh * RIDE_SEAT;
            RectF rr = new RectF(w * 0.5f - rw * 0.5f, top, w * 0.5f + rw * 0.5f, top + rh);
            c.drawBitmap(art, null, rr, p);
        }

        void setArt(int k) {''', '方法')

open(P, 'w', encoding='utf-8').write(s)
print('PATCH_OK', len(done))

j = open(P, encoding='utf-8').read()
c = [('G1 骑姿高宽比进表', 'MOUNT_MHW = {0.32f, 0.52f, 0.34f, 0.50f, 0.46f}' in j),
     ('G2 三张骑姿真实加载', 'rideArt0 = loadOpt("ride_0.png")' in j),
     ('G3 有骑姿优先走骑姿', 'Bitmap rb = rideFor(art);' in j and 'drawRide(c, w, h, rb, mounts[mount]);' in j),
     ('G4 臀落鞍位（坐骨线）', 'saddleY - rh * RIDE_SEAT' in j),
     ('G5 没骑姿的形象仍走旧路', 'rideFor(int k)' in j)]
for n, v in c:
    print(n, 'PASS' if v else 'FAIL')
print('SUMMARY', 'PASS' if all(v for _, v in c) else 'FAIL')
raise SystemExit(0 if all(v for _, v in c) else 1)
