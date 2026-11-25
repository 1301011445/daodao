# -*- coding: utf-8 -*-
"""v129 人物与坐骑匹配：每只坐骑单独定"高度占比 + 脚踩比例"，骑上时人物缩到 0.74
判据 M1~M5
"""
P = r'F:\Daodao\src\_apk\src\com\daodao\pet\DaoOverlay.java'
s = open(P, encoding='utf-8').read()
ok = []


def rep(old, new, tag):
    global s
    if old not in s:
        print('MISS', tag)
        return False
    s = s.replace(old, new, 1)
    ok.append(tag)
    return True


# 1) 配置表：跟着 MOUNT_FILES 一一对应
rep('''    private final String[] MOUNT_FILES = {''',
    '''    // v129 人物与坐骑匹配：每只坐骑单独给「高度占视窗的比例」和「脚踩到它多高」
    // 数值来自 tools\\形象\\坐骑配比_v129g.py 的实测与预览（_配比预览6.png）
    private final float[] MOUNT_MHW = {0.28f, 0.40f, 0.24f, 0.34f, 0.40f};  // 坐骑高 / 视窗高
    private final float[] MOUNT_FR = {0.86f, 0.60f, 0.45f, 0.58f, 0.38f};   // 脚踩高度 / 坐骑高（从底算）
    private final float MOUNT_CS = 0.74f;                                   // 骑上时人物缩放，留出头顶空间
    private final String[] MOUNT_FILES = {''',
    '配比表')

# 2) 绘制：坐骑按自己的比例，人物按 0.74 缩，脚落在坐骑背线
rep('''            if (mb != null && !mb.isRecycled()) {
                float mw = w * 0.98f;
                float mh = mw * mb.getHeight() / Math.max(1, mb.getWidth());
                RectF mr = new RectF(w * 0.5f - mw * 0.5f, h + bob - mh, w * 0.5f + mw * 0.5f, h + bob);
                c.drawBitmap(mb, null, mr, p);
                rise = mh * 0.52f;   // 抬到鞍位：脚踩在坐骑背上，不是整个人沉进云里
            }
            c.save();''',
    '''            if (mb != null && !mb.isRecycled()) {
                int mi = Math.max(1, Math.min(MOUNT_MHW.length, mount)) - 1;
                float mh = h * MOUNT_MHW[mi];
                float mw = mh * mb.getWidth() / Math.max(1, mb.getHeight());
                if (mw > w * 0.98f) { mw = w * 0.98f; mh = mw * mb.getHeight() / Math.max(1, mb.getWidth()); }
                RectF mr = new RectF(w * 0.5f - mw * 0.5f, h + bob - mh, w * 0.5f + mw * 0.5f, h + bob);
                c.drawBitmap(mb, null, mr, p);
                rise = mh * MOUNT_FR[mi];   // 踩到它背上：祥云高、木马鞍、飞剑刃面、小鹿背、纸鹤脊
            }
            c.save();''',
    '按表绘制')

# 3) 人物：骑上时整体缩到 0.74，并把抬升换算回缩放坐标
rep('''            if (rise > 0f) c.translate(0, -rise);''',
    '''            float ms = (mb != null && !mb.isRecycled()) ? MOUNT_CS : 1f;
            if (ms < 1f) {
                // 以底边中点为锚点缩小：脚的位置不动，头自动让出空间（原来头会被抬出画布）
                c.translate(w * 0.5f * (1f - ms), h * (1f - ms));
                c.scale(ms, ms);
            }
            if (rise > 0f) c.translate(0, -rise / ms);''',
    '人物缩放')
open(P, 'w', encoding='utf-8').write(s)
print('PATCH_OK', len(ok))

j = open(P, encoding='utf-8').read()
checks = [
    ('M1 五只各有高度比', 'MOUNT_MHW = {0.28f, 0.40f, 0.24f, 0.34f, 0.40f}' in j),
    ('M2 五只各有脚踩比', 'MOUNT_FR = {0.86f, 0.60f, 0.45f, 0.58f, 0.38f}' in j),
    ('M3 绘制按自己的比例', 'float mh = h * MOUNT_MHW[mi];' in j),
    ('M4 骑上人物缩 0.74 且描点不动', 'MOUNT_CS' in j and 'h * (1f - ms)' in j),
    ('M5 抬升换算回缩放坐标', 'c.translate(0, -rise / ms);' in j),
]
for n, v in checks:
    print(n, 'PASS' if v else 'FAIL')
print('SUMMARY', 'PASS' if all(v for _, v in checks) else 'FAIL')
raise SystemExit(0 if all(v for _, v in checks) else 1)
