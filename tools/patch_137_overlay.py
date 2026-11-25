# -*- coding: utf-8 -*-
import io,re
J=r"F:\Daodao\src\_apk\src\com\daodao\pet\DaoOverlay.java"
B=r"F:\Daodao\src\_apk\src\com\daodao\pet\DaoBridge.java"
t=io.open(J,encoding="utf-8",errors="ignore").read()
orig=t
def rep(old,new,label):
    global t
    if old not in t:
        print("FAIL",label); return False
    t=t.replace(old,new,1); print("OK",label); return True

# 1) 尺寸
rep('''    private int petH() {
        int h = (int) (sh * 0.075f);
        int cap = dp(66);''','''    private int petH() {
        // 2026-11-26 用户：悬浮窗太小、看不出模样。7.5% 屏高 / 66dp 顶 → 15% / 150dp 顶，下限 52dp → 100dp。
        // 1080×2400 上约 360px 高、180px 宽，胳膊腿和脸都能看清；再大会挡图标。
        int h = (int) (sh * 0.15f);
        int cap = dp(150);''',"petH")
rep('        if (h < dp(52)) h = dp(52);','        if (h < dp(100)) h = dp(100);',"petH-min")

# 2) 服务级静态引用 + 会走会飞的状态
rep('''    private int art = ART_WALK;        // 当前桌面形象（face 文件序号），默认还是那个有八帧素材的少女''',
'''    private int art = ART_WALK;        // 当前桌面形象（face 文件序号），默认还是那个有八帧素材的少女
    // 2026-11-26：App 里点「换形象」也要让桌面上这只立刻跟着换
    private static DaoOverlay sSvc;
    // 2026-11-26 悬浮窗会走会飞：攒不够 1dp 的位移，别因为取整原地抖
    private float driftAccX = 0f;
    private float flyBaseY = Float.NaN;''',"fields")

# 3) onCreate 记引用
rep('''        art = sp.getInt("art", ART_WALK);
        measure();''','''        art = sp.getInt("art", ART_WALK);
        sSvc = this;
        measure();''',"onCreate")
rep('''        try { sp.edit().putBoolean("on", false).apply(); } catch (Exception e) { }
        super.onDestroy();''','''        try { sp.edit().putBoolean("on", false).apply(); } catch (Exception e) { }
        if (sSvc == this) sSvc = null;
        super.onDestroy();''',"onDestroy")

# 4) 静态 setArt（App 调用）
rep('''    /** 2026-11-25 外部切换坐骑：0 无 / 1 祥云 / 2 木马。手机主界面「坐骑」按钮走这里。 */''',
'''    /** 2026-11-26：App 里换形象，桌面上的悬浮窗立刻跟着换；没起悬浮窗就先记进偏好，下次起来直接是它。 */
    public static void setArt(int k) {
        DaoOverlay s = sSvc;
        if (s == null) return;
        try {
            s.art = k;
            s.sp.edit().putInt("art", k).apply();
            if (s.pv != null) s.pv.setArt(k);
            s.refreshNotif();
        } catch (Throwable e) { }
    }

    /** 2026-11-25 外部切换坐骑：0 无 / 1 祥云 / 2 木马。手机主界面「坐骑」按钮走这里。 */''',"setArt")

# 5) 会走会飞
rep('''        // 2026-11-25 用户：走路不是移动。以前这里把整个悬浮窗按 2dp/拍往横里推
        // （≈22dp/秒，走 3~5 秒就是横穿小半屏），看着就是"点它一下它就跑掉了"。
        // 现在窗口原地不动，只播迈步动画（walk8 帧 + 骨盆与分腿位移），人站在原地迈腿。
        if (now > walkUntilAt) {''',
'''        // 2026-11-26 用户：又要会走、会飞，但不能像以前那样一碰就跑。
        // 规则：每拍最多 0.42dp（≈12.6dp/秒），一次走 3~5 秒也就 40~60dp；
        // 骑云/鹤/剑的三只算腾空，另叠一层 ±9dp 的上下飘，看着是在飞。
        if (!isAirMount()) flyBaseY = Float.NaN;
        int w = lp.width, h = lp.height;
        if (isAirMount()) {
            if (Float.isNaN(flyBaseY)) flyBaseY = lp.y;
            int bobY = (int) (Math.sin(now / 620.0) * dp(9));
            int ny = (int) flyBaseY + bobY;
            if (ny < dp(4)) ny = dp(4);
            if (ny > sh - h - dp(4)) ny = sh - h - dp(4);
            if (ny != lp.y) {
                lp.y = ny;
                try { wm.updateViewLayout(pv, lp); } catch (Throwable e) { }
            }
        }
        driftAccX += 0.42f * walkDir;
        if (Math.abs(driftAccX) >= 1f) {
            int d = (int) driftAccX;
            driftAccX -= d;
            int nx = lp.x + d;
            if (nx < dp(2) || nx > sw - w - dp(2)) { walkDir = -walkDir; driftAccX = 0f; }
            else {
                lp.x = nx;
                try { wm.updateViewLayout(pv, lp); } catch (Throwable e) { }
            }
        }
        if (now > walkUntilAt) {''',"drift")
rep('''            walkNextAt = now + 3500 + (long) (Math.random() * 3500);
            if (pv != null) pv.walking = false;
        }
    }''','''            walkNextAt = now + 3500 + (long) (Math.random() * 3500);
            if (pv != null) pv.walking = false;
            flyBaseY = Float.NaN;
            try { sp.edit().putInt("x0", lp.x).putInt("y0", lp.y).apply(); } catch (Throwable e) { }
        }
    }

    /** 骑在云 / 飞剑 / 纸鹤上算腾空，要上下飘；木马小鹿是踩在地上的。 */
    private boolean isAirMount() {
        try { return pv != null && (pv.mount == 1 || pv.mount == 3 || pv.mount == 5); }
        catch (Throwable e) { return false; }
    }''',"walkEnd")

io.open(J,"w",encoding="utf-8").write(t)

b=io.open(B,encoding="utf-8",errors="ignore").read()
bo=b
def repb(old,new,label):
    global b
    if old not in b:
        print("FAIL",label); return False
    b=b.replace(old,new,1); print("OK",label); return True
repb('''    @JavascriptInterface
    public void setMountAuto(boolean auto) {''','''    @JavascriptInterface
    public void setArt(int k) {
        try { DaoOverlay.setArt(k); } catch (Throwable e) { }
    }

    @JavascriptInterface
    public void setMountAuto(boolean auto) {''',"bridge.setArt")
io.open(B,"w",encoding="utf-8").write(b)
print("java done, changed:", t!=orig, b!=bo)
