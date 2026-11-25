# -*- coding: utf-8 -*-
"""v132：坐骑会动 + 说话对口型 + 放歌跳舞（手机悬浮窗）
判据 H1~H8
"""
O = r'F:\Daodao\src\_apk\src\com\daodao\pet\DaoOverlay.java'
B = r'F:\Daodao\src\_apk\src\com\daodao\pet\DaoBridge.java'
s = open(O, encoding='utf-8').read()
b = open(B, encoding='utf-8').read()
done = []


def rep(src, old, new, tag):
    if old not in src:
        raise SystemExit('MISS ' + tag)
    done.append(tag)
    return src.replace(old, new, 1)


# ---- 1. 静态状态位 ----
s = rep(s, '''    private static PetView sLive;   // 当前挂着的悬浮窗，供「换动作」这类外部调用''',
        '''    private static PetView sLive;   // 当前挂着的悬浮窗，供「换动作」这类外部调用

    // v132：说话 / 放歌状态。Bridge 一出声就置位，PetView 拿它驱动口型和舞步
    private static volatile long talkUntil = 0L;
    private static volatile long danceUntil = 0L;

    public static void setTalking(boolean on) {
        talkUntil = on ? System.currentTimeMillis() + 90000L : System.currentTimeMillis();
        PetView v = sLive;
        if (v != null) v.postInvalidate();
    }

    public static void setDancing(boolean on) {
        danceUntil = on ? System.currentTimeMillis() + 90000L : System.currentTimeMillis();
        PetView v = sLive;
        if (v != null) v.postInvalidate();
    }''', '静态状态位')

# ---- 2. 跳舞：整只（含坐骑）一起摆 ----
s = rep(s, '''            // 脚下一点软阴影：不然人是"飘"在白底上的，落地感差
            Paint sh = new Paint(Paint.ANTI_ALIAS_FLAG);''',
        '''            // v132：放歌就跳舞 —— 以脚跟为轴左右摆、上下弹；坐骑跟着一起颠
            long dnNow = System.currentTimeMillis();
            boolean dancing = dnNow < danceUntil;
            if (dancing) {
                double dt = (dnNow % 600000L) / 1000.0;
                c.save();
                c.rotate((float) Math.sin(dt * 5.0) * 4.5f, w * 0.5f, h * 0.99f);
                c.translate((float) Math.sin(dt * 5.0) * w * 0.018f, -(float) Math.abs(Math.sin(dt * 5.0)) * h * 0.035f);
            }
            // 脚下一点软阴影：不然人是"飘"在白底上的，落地感差
            Paint sh = new Paint(Paint.ANTI_ALIAS_FLAG);''', '跳舞包络')

# ---- 3. 坐骑动起来 ----
s = rep(s, '''            if (mb != null && !mb.isRecycled()) {
                int mi = Math.max(1, Math.min(MOUNT_MHW.length, mount)) - 1;
                float mh = h * MOUNT_MHW[mi];
                float mw = mh * mb.getWidth() / Math.max(1, mb.getHeight());
                if (mw > w * 0.98f) { mw = w * 0.98f; mh = mw * mb.getHeight() / Math.max(1, mb.getWidth()); }
                RectF mr = new RectF(w * 0.5f - mw * 0.5f, h + bob - mh, w * 0.5f + mw * 0.5f, h + bob);
                c.drawBitmap(mb, null, mr, p);
                rise = mh * MOUNT_FR[mi];   // 踩到它背上：祥云高、木马鞍、飞剑刃面、小鹿背、纸鹤脊
            }''',
        '''            float mdx = 0f, mdy = 0f;
            if (mb != null && !mb.isRecycled()) {
                int mi = Math.max(1, Math.min(MOUNT_MHW.length, mount)) - 1;
                float mh = h * MOUNT_MHW[mi];
                float mw = mh * mb.getWidth() / Math.max(1, mb.getHeight());
                if (mw > w * 0.98f) { mw = w * 0.98f; mh = mw * mb.getHeight() / Math.max(1, mb.getWidth()); }
                // v132：坐骑也会动 —— 云飘、马跑、剑腾、鹿颠、鹤扇翅
                double mt = (System.currentTimeMillis() % 600000L) / 1000.0;
                float mrot = 0f, msc = 1f;
                if (mi == 0) { mdx = (float) Math.sin(mt * 0.85) * 0.030f * w; mdy = (float) Math.sin(mt * 1.25) * 0.012f * h; }
                else if (mi == 1) { mdy = (float) Math.sin(mt * 6.2) * 0.008f * h; mrot = (float) Math.sin(mt * 6.2) * 1.6f; }
                else if (mi == 2) { mdy = (float) Math.sin(mt * 2.3) * 0.022f * h; mrot = (float) Math.sin(mt * 2.3) * 3.2f; }
                else if (mi == 3) { mdy = (float) Math.sin(mt * 4.0) * 0.011f * h; mrot = (float) Math.sin(mt * 4.0) * 1.3f; }
                else { mdy = (float) Math.sin(mt * 2.8) * 0.020f * h; msc = 1f + 0.035f * (float) Math.sin(mt * 2.8); }
                float bw2 = mw * msc, bh2 = mh * (2f - msc);   // 扇翅：横向张开、纵向略收
                c.save();
                c.rotate(mrot, w * 0.5f + mdx, h + bob - mh * MOUNT_FR[mi]);
                RectF mr = new RectF(w * 0.5f + mdx - bw2 * 0.5f, h + bob + mdy - bh2,
                                     w * 0.5f + mdx + bw2 * 0.5f, h + bob + mdy);
                c.drawBitmap(mb, null, mr, p);
                c.restore();
                rise = mh * MOUNT_FR[mi];   // 踩到它背上：祥云高、木马鞍、飞剑刃面、小鹿背、纸鹤脊
            }''', '坐骑动画')

# ---- 4. 人跟坐骑同频 ----
s = rep(s, '''            if (rise > 0f) c.translate(0, -rise / ms);''',
        '''            if (rise > 0f) c.translate(0, -rise / ms);
            if (mdx != 0f || mdy != 0f) c.translate(mdx, mdy);   // 云飘/马颠时人得跟着一起动，不然脱开''', '人随坐骑')

# ---- 5. 跳舞收尾 ----
s = rep(s, '''            } else {
                c.drawBitmap(sheet, src, dst, p);
            }
            c.restore();
        }''',
        '''            } else {
                c.drawBitmap(sheet, src, dst, p);
            }
            c.restore();
            if (dancing) c.restore();
        }''', '跳舞收尾')

# ---- 6. 口型：嘴那一段跟着语音开合 ----
s = rep(s, '''                    float dy = -0.007f * h * breath * (float) Math.exp(-Math.pow((ny - 0.44) / 0.20, 2));''',
        '''                    float dy = -0.007f * h * breath * (float) Math.exp(-Math.pow((ny - 0.44) / 0.20, 2));
                    // v132 口型：嘴所在那条带（约 0.20~0.29 身高）随语音开合，约 6Hz，像真的在说
                    if (System.currentTimeMillis() < talkUntil) {
                        float jaw = (float) Math.exp(-Math.pow((ny - 0.245) / 0.048, 2));
                        dy += 0.013f * h * jaw * (0.5f - 0.5f * (float) Math.cos(t * 38.0));
                    }''', '口型')

# ---- 7. 骑乘路径也要动 + 也要说话点头 ----
s = rep(s, '''            Paint sp = new Paint(Paint.ANTI_ALIAS_FLAG);
            sp.setColor(0x22000000);
            c.drawOval(new RectF(w * 0.24f, h - h * 0.03f, w * 0.76f, h + h * 0.005f), sp);
            RectF mr = new RectF(w * 0.5f - mw * 0.5f, h - mh, w * 0.5f + mw * 0.5f, h);
            c.drawBitmap(mb, null, mr, p);''',
        '''            double mt = (System.currentTimeMillis() % 600000L) / 1000.0;
            float mdx = 0f, mdy = 0f, mrot = 0f;
            if (mi == 0) { mdx = (float) Math.sin(mt * 0.85) * 0.030f * w; mdy = (float) Math.sin(mt * 1.25) * 0.012f * h; }
            else if (mi == 1) { mdy = (float) Math.sin(mt * 6.2) * 0.008f * h; mrot = (float) Math.sin(mt * 6.2) * 1.6f; }
            else if (mi == 2) { mdy = (float) Math.sin(mt * 2.3) * 0.022f * h; mrot = (float) Math.sin(mt * 2.3) * 3.2f; }
            else if (mi == 3) { mdy = (float) Math.sin(mt * 4.0) * 0.011f * h; mrot = (float) Math.sin(mt * 4.0) * 1.3f; }
            else { mdy = (float) Math.sin(mt * 2.8) * 0.020f * h; }
            long dn2 = System.currentTimeMillis();
            boolean dancing2 = dn2 < danceUntil;
            c.save();
            if (dancing2) {
                c.rotate((float) Math.sin(mt * 5.0) * 4.5f, w * 0.5f, h * 0.99f);
                c.translate((float) Math.sin(mt * 5.0) * w * 0.018f, -(float) Math.abs(Math.sin(mt * 5.0)) * h * 0.035f);
            }
            Paint sp = new Paint(Paint.ANTI_ALIAS_FLAG);
            sp.setColor(0x22000000);
            c.drawOval(new RectF(w * 0.24f, h - h * 0.03f, w * 0.76f, h + h * 0.005f), sp);
            c.save();
            c.rotate(mrot, w * 0.5f + mdx, h - mh * MOUNT_FR[mi]);
            RectF mr = new RectF(w * 0.5f + mdx - mw * 0.5f, h + mdy - mh, w * 0.5f + mdx + mw * 0.5f, h + mdy);
            c.drawBitmap(mb, null, mr, p);
            c.restore();''', '骑乘坐骑动画')

s = rep(s, '''            float top = saddleY - rh * sr;''',
        '''            float top = saddleY - rh * sr + mdy;
            // 说话时上身轻轻点头，像在应声说话（骑乘图是整张立绘，做不了逐字口型，用这点动感代）
            if (System.currentTimeMillis() < talkUntil) top += (float) Math.sin(mt * 9.0) * 0.006f * h;''', '骑乘说话点头')

s = rep(s, '''            RectF rr = new RectF(w * 0.5f - rw * 0.5f, top, w * 0.5f + rw * 0.5f, top + rh);
            c.drawBitmap(rideImg, null, rr, p);
        }''',
        '''            RectF rr = new RectF(w * 0.5f + mdx - rw * 0.5f, top, w * 0.5f + mdx + rw * 0.5f, top + rh);
            c.drawBitmap(rideImg, null, rr, p);
            c.restore();
        }''', '骑乘收尾')

# ---- 8. Bridge：出声/放歌打点 ----
b = rep(b, '''    @JavascriptInterface
    public void speak(final String text) {''',
        '''    /** v132：说话期间让悬浮窗对口型（估算时长，到点自动收） */
    private void markTalk(int ms) {
        try { DaoOverlay.setTalking(true); } catch (Throwable e) { }
        try {
            ui.postDelayed(new Runnable() {
                public void run() { try { DaoOverlay.setTalking(false); } catch (Throwable e) { } }
            }, Math.max(1500, ms));
        } catch (Throwable e) { }
    }

    private void markDance(int secs) {
        try { DaoOverlay.setDancing(true); } catch (Throwable e) { }
        try {
            ui.postDelayed(new Runnable() {
                public void run() { try { DaoOverlay.setDancing(false); } catch (Throwable e) { } }
            }, (long) Math.max(1500, (secs + 1) * 1000));
        } catch (Throwable e) { }
    }

    @JavascriptInterface
    public void speak(final String text) {''', 'markTalk 定义')

b = rep(b, '''        initTts();
        stopAudio();''',
        '''        initTts();
        stopAudio();
        markTalk(t.length() * 210);''', 'speak 打点')

open(O, 'w', encoding='utf-8').write(s)
open(B, 'w', encoding='utf-8').write(b)
print('PATCH_OK', len(done))
