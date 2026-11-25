package com.daodao.pet;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.content.SharedPreferences;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.graphics.RadialGradient;
import android.graphics.Rect;
import android.graphics.RectF;
import android.graphics.Shader;
import android.os.Build;
import android.os.Handler;
import android.os.IBinder;
import android.os.Looper;
import android.util.DisplayMetrics;
import android.view.Gravity;
import android.view.MotionEvent;
import android.view.View;
import android.view.WindowManager;
import android.widget.Toast;

/**
 * 手机端「在桌面上」浮窗。
 *
 * 2026-11-22 新加：电脑端 0.110 已经有四种状态（满身 / 贴边偷看 / 小圆球 / 收起），
 * 手机这边用系统浮层（TYPE_APPLICATION_OVERLAY）做同一套东西。
 *
 * 四种状态：
 *   0 满身   —— 整个立绘浮在屏幕上，可拖，点一下打开道
 *   1 贴边   —— 窗口中心压在屏幕边上，系统替我们切掉一半，就是"扒着边框偷看"
 *   2 小圆球 —— 一颗带表情的小球，点一下变回满身
 *   3 收起   —— 只留通知栏那条，点通知里的按钮唤回
 *
 * 两条自动规矩（不改用户手动选的状态）：
 *   打开「道」本体时浮窗自己藏起来，退回桌面/别的应用再出来；
 *   屏幕熄灭时撤掉，亮屏再挂上。
 */
public class DaoOverlay extends Service {

    public static final int MODE_FULL = 0;
    public static final int MODE_PEEK = 1;
    public static final int MODE_BALL = 2;
    public static final int MODE_HIDE = 3;

    public static final int SIDE_LEFT = 1;
    public static final int SIDE_RIGHT = 2;

    public static final String SP = "daodao_overlay";
    private static final String CH = "dao_overlay";
    private static final int NID = 2001;

    static final String A_START = "com.daodao.pet.OV_START";
    static final String A_MODE = "com.daodao.pet.OV_MODE";
    static final String A_SIDE = "com.daodao.pet.OV_SIDE";
    static final String A_STOP = "com.daodao.pet.OV_STOP";
    static final String A_ART = "com.daodao.pet.OV_ART";   // 换形象（通知按钮 / 长按桌宠）

    // 悬浮窗也能换形象（2026-11-24 夜：以前只有 walk8.png 一套，桌面上永远是同一个少女）
    // 顺序跟 dao.html 的 _ks 完全一致，两端「第几个形象」说得上是同一个
    static final int[] ARTS = { 12, 13, 6, 7, 8, 11, 0, 1, 2, 3, 4, 5, 9, 10 };
    // 2026-11-25：悬浮窗的四个小动作，主界面「换动作」也按这几个派
    static final int ACT_WAVE = 0, ACT_NOD = 1, ACT_HOP = 2, ACT_SQUAT = 3;
    // 只有这个形象有真八帧走路素材，其它 13 个用立绘 + 网格变形代步
    static final int ART_WALK = 6;

    private WindowManager wm;
    private SharedPreferences sp;
    private PetView pv;
    private WindowManager.LayoutParams lp;
    private Handler ui = new Handler(Looper.getMainLooper());

    private int mode = MODE_PEEK;
    private int side = SIDE_RIGHT;
    private int art = ART_WALK;        // 当前桌面形象（face 文件序号），默认还是那个有八帧素材的少女
    private int sw = 0, sh = 0;
    private boolean added = false;
    private boolean screenOn = true;

    private long tick = 0;
    private int beatN = 0;   // 2026-11-25 提帧：33ms 重绘计数，3 拍做一次 90ms 的逻辑
    private Runnable beat;

    private BroadcastReceiver screenRx;

    // ---------------- 给桥 / 页面用的静态口子 ----------------

    public static boolean canDraw(Context c) {
        try {
            if (Build.VERSION.SDK_INT >= 23) return android.provider.Settings.canDrawOverlays(c);
            return true;
        } catch (Exception e) {
            return false;
        }
    }

    /** 1|模式|边  —— 正在浮着 / 0 表示没开 */
    public static String state(Context c) {
        try {
            SharedPreferences p = c.getSharedPreferences(SP, Context.MODE_PRIVATE);
            String on = p.getBoolean("on", false) ? "1" : "0";
            String m = String.valueOf(p.getInt("mode", MODE_PEEK));
            String s = String.valueOf(p.getInt("side", SIDE_RIGHT));
            return on + "|" + m + "|" + s;
        } catch (Exception e) {
            return "0|1|2";
        }
    }

    public static void askPermission(Context c) {
        try {
            if (Build.VERSION.SDK_INT >= 23) {
                Intent i = new Intent(android.provider.Settings.ACTION_MANAGE_OVERLAY_PERMISSION,
                        android.net.Uri.parse("package:" + c.getPackageName()));
                i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                c.startActivity(i);
            }
        } catch (Exception e) { }
    }

    public static void start(Context c, int m) {
        try {
            Intent i = new Intent(c, DaoOverlay.class);
            i.setAction(A_START);
            i.putExtra("mode", m);
            if (Build.VERSION.SDK_INT >= 26) c.startForegroundService(i);
            else c.startService(i);
        } catch (Exception e) { }
    }

    public static void setMode(Context c, int m) {
        try {
            Intent i = new Intent(c, DaoOverlay.class);
            i.setAction(A_MODE);
            i.putExtra("mode", m);
            if (Build.VERSION.SDK_INT >= 26) c.startForegroundService(i);
            else c.startService(i);
        } catch (Exception e) { }
    }

    public static void flipSide(Context c) {
        try {
            Intent i = new Intent(c, DaoOverlay.class);
            i.setAction(A_SIDE);
            if (Build.VERSION.SDK_INT >= 26) c.startForegroundService(i);
            else c.startService(i);
        } catch (Exception e) { }
    }

    public static void stop(Context c) {
        try {
            Intent i = new Intent(c, DaoOverlay.class);
            i.setAction(A_STOP);
            if (Build.VERSION.SDK_INT >= 26) c.startForegroundService(i);
            else c.startService(i);
        } catch (Exception e) { }
    }

    // ---------------- 生命周期 ----------------

    @Override
    public void onCreate() {
        super.onCreate();
        wm = (WindowManager) getSystemService(WINDOW_SERVICE);
        sp = getSharedPreferences(SP, MODE_PRIVATE);
        mode = sp.getInt("mode", MODE_PEEK);
        side = sp.getInt("side", SIDE_RIGHT);
        art = sp.getInt("art", ART_WALK);
        measure();

        screenRx = new BroadcastReceiver() {
            @Override
            public void onReceive(Context context, Intent intent) {
                try {
                    String a = intent == null ? "" : intent.getAction();
                    if (Intent.ACTION_SCREEN_OFF.equals(a)) {
                        screenOn = false;
                        hideView();
                    } else if (Intent.ACTION_SCREEN_ON.equals(a)) {
                        screenOn = true;
                        showView(false);
                    }
                } catch (Exception e) { }
            }
        };
        try {
            IntentFilter f = new IntentFilter();
            f.addAction(Intent.ACTION_SCREEN_ON);
            f.addAction(Intent.ACTION_SCREEN_OFF);
            registerReceiver(screenRx, f);
        } catch (Exception e) { }
    }

    @Override
    public int onStartCommand(Intent it, int flags, int startId) {
        String a = (it == null || it.getAction() == null) ? A_START : it.getAction();
        int m = (it == null) ? -1 : it.getIntExtra("mode", -1);

        if (A_STOP.equals(a)) {
            // 用 startForegroundService 叫起来的服务，5 秒内必须先 startForeground，否则系统直接判崩
            startForegroundSafe();
            stopAll();
            return START_NOT_STICKY;
        }
        if (A_SIDE.equals(a)) {
            side = (side == SIDE_LEFT) ? SIDE_RIGHT : SIDE_LEFT;
            sp.edit().putInt("side", side).apply();
        }
        if (A_ART.equals(a)) cycleArt();
        if (m >= 0) {
            mode = m;
            sp.edit().putInt("mode", mode).apply();
        }
        sp.edit().putBoolean("on", true).putBoolean("want", true).apply();

        startForegroundSafe();
        if (mode == MODE_HIDE) hideView();
        else if (screenOn) showView(false);
        else hideView();

        startBeat();
        return START_STICKY;
    }

    @Override
    public void onConfigurationChanged(android.content.res.Configuration nc) {
        super.onConfigurationChanged(nc);
        measure();
        if (pv != null) pv.reloadSheet();
        if (added) {
            int oldMode = mode;
            mode = oldMode;
            layout(oldMode, false);
        }
    }

    @Override
    public void onDestroy() {
        stopBeat();
        removeView();                      // 只拆窗口，不再发通知（服务都要没了，别再留一条挂着）
        try { if (screenRx != null) unregisterReceiver(screenRx); } catch (Exception e) { }
        try { sp.edit().putBoolean("on", false).apply(); } catch (Exception e) { }
        super.onDestroy();
    }

    @Override
    public IBinder onBind(Intent i) { return null; }

    // ---------------- 浮窗管理 ----------------

    private int dp(float v) {
        return (int) (v * getResources().getDisplayMetrics().density + 0.5f);
    }

    private void measure() {
        try {
            DisplayMetrics dm = new DisplayMetrics();
            wm.getDefaultDisplay().getRealMetrics(dm);
            sw = dm.widthPixels;
            sh = dm.heightPixels;
        } catch (Exception e) { }
        if (sw <= 0) sw = 1080;
        if (sh <= 0) sh = 1920;
    }

    /** 满身/贴边共用的立绘尺寸：高约屏幕 7.5%（上一版 16% 还是太大，挡图标）
     *  1080×2400 / density 2.75 实测：180px 高、90px 宽，跟桌面图标差不多大 */
    private int petH() {
        int h = (int) (sh * 0.075f);
        int cap = dp(66);
        if (h > cap) h = cap;
        if (h < dp(52)) h = dp(52);
        return h;
    }

    private int ballSize() {
        return dp(42);
    }

    private void layout(int m, boolean resetPos) {
        if (pv == null) return;
        if (lp == null) {
            lp = new WindowManager.LayoutParams();
            if (Build.VERSION.SDK_INT >= 26) {
                lp.type = WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY;
            } else {
                lp.type = WindowManager.LayoutParams.TYPE_PHONE;
            }
            lp.gravity = Gravity.TOP | Gravity.LEFT;
        }
        int w, h;
        if (m == MODE_BALL) {
            int s = ballSize();
            w = s; h = s;
        } else {
            h = petH();
            w = h / 2;
        }
        lp.width = w;
        lp.height = h;
        lp.format = android.graphics.PixelFormat.TRANSLUCENT;
        lp.flags = WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE
                | WindowManager.LayoutParams.FLAG_NOT_TOUCH_MODAL
                | WindowManager.LayoutParams.FLAG_LAYOUT_NO_LIMITS
                | WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN;

        int kx, ky;
        if (m == MODE_PEEK) {
            kx = side == SIDE_LEFT ? -w / 2 : sw - w / 2;
            ky = resetPos ? (int) (sh * 0.38f) : sp.getInt("y1", (int) (sh * 0.38f));
            peekT0 = 0;          // 刚贴边先老老实实藏着，过一会儿再探头
            peekLastX = Integer.MIN_VALUE;
        } else if (m == MODE_BALL) {
            kx = resetPos ? (sw - w - dp(6)) : sp.getInt("x2", sw - w - dp(6));
            ky = resetPos ? (int) (sh * 0.42f) : sp.getInt("y2", (int) (sh * 0.42f));
            if (kx < 0) kx = 0;
            if (kx > sw - w) kx = sw - w;
        } else {
            kx = resetPos ? (sw - w - dp(10)) : sp.getInt("x0", sw - w - dp(10));
            ky = resetPos ? (int) (sh * 0.60f) : sp.getInt("y0", (int) (sh * 0.60f));
            if (kx < 0) kx = 0;
            if (kx > sw - w) kx = sw - w;
        }
        if (ky < 0) ky = 0;
        if (ky > sh - h) ky = sh - h;
        lp.x = kx; lp.y = ky;

        if (pv != null) pv.setMode(m);
        if (added) {
            try { wm.updateViewLayout(pv, lp); } catch (Exception e) { }
        }
    }

    private void showView(boolean resetPos) {
        if (mode == MODE_HIDE) return;
        if (sp.getInt("app", 0) == 1) return;     // 「道」本体在前台时不挡着
        if (pv == null) {
            pv = new PetView();
        }
        layout(mode, resetPos);
        if (!added) {
            try {
                wm.addView(pv, lp);
                added = true;
                // 2026-11-25：浮窗刚挂到桌面上的那一下，先抬手打个招呼再站定
                try { pv.greet(true); } catch (Exception e) { }
            } catch (Exception e) {
                added = false;
                toast("浮窗没挂上去：" + (e == null ? "" : e.getMessage()));
            }
        }
        refreshNotif();
    }

    private void hideView() {
        removeView();
        refreshNotif();
    }

    private void removeView() {
        if (pv != null && added) {
            try { wm.removeView(pv); } catch (Exception e) { }
        }
        added = false;
    }

    private void stopAll() {
        removeView();
        stopBeat();
        try { stopForeground(true); } catch (Exception e) { }
        try { sp.edit().putBoolean("on", false).putBoolean("want", false).putInt("app", 0).apply(); } catch (Exception e) { }
        stopSelf();
    }

    private void setModeInternal(int m) {
        mode = m;
        sp.edit().putInt("mode", m).putBoolean("on", true).putBoolean("want", true).apply();
        if (m == MODE_HIDE) {
            hideView();
        } else {
            showView(false);
            if (!added && screenOn) showView(false);
        }
        refreshNotif();
    }

    private void toast(final String s) {
        ui.post(new Runnable() {
            public void run() {
                try { Toast.makeText(DaoOverlay.this, s, Toast.LENGTH_SHORT).show(); } catch (Exception e) { }
            }
        });
    }

    // ---------------- 心跳：做动画 + 看前台 ----------------

    private void startBeat() {
        if (beat != null) return;
        beat = new Runnable() {
            public void run() {
                try {
                    if (pv != null && added) pv.invalidate();
                } catch (Exception e) { }
                // 2026-11-25 提帧：画 30fps（33ms），逻辑还是 90ms 一次——直接把 tick 加快会把
                // 走路速度、打招呼间隔全带快 3 倍，所以做成"多画、少算"
                if (++beatN % 3 != 0) { ui.postDelayed(this, 33); return; }
                // 每 10 拍（≈0.9 秒）查一次：本体在前台就藏，回桌面再出来
                if (tick % 10 == 0) {
                    try {
                        int app = sp.getInt("app", 0);
                        if (app == 1 && added) hideView();
                        else if (app == 0 && !added && screenOn && mode != MODE_HIDE) showView(false);
                    } catch (Exception e) { }
                }
                // 每 600 拍（≈54 秒）想打招呼就自己冒一句（内部限 20 分钟一次、只白天）
                if (tick % 600 == 0 && pv != null && added && mode == MODE_FULL) {
                    try { pv.greet(false); } catch (Exception e) { }
                }
                // 贴边时慢慢探头、再缩回去（学乔巴：先只露半身，隔一阵扒着边往外探一下）
                if (mode == MODE_PEEK && added && lp != null && pv != null) {
                    try { peekDrift(); } catch (Exception e) { }
                }
                // 满身站在桌面上时会自己走两步，不是钉在原地
                if (mode == MODE_FULL && added && lp != null && pv != null) {
                    try { walkDrift(); } catch (Exception e) { }
                    try { pv.idleWaveIfDue(); } catch (Exception e) { }
                    try { pv.idleActIfDue(); } catch (Exception e) { }
                }
                ui.postDelayed(this, 33);
            }
        };
        ui.post(beat);
    }

    private void stopBeat() {
        if (beat != null) ui.removeCallbacks(beat);
        beat = null;
    }

    // ---------------- 贴边探头 ----------------
    // 原来靠画布左右平移做"探头"，2.9 秒来回一趟，像在原地抖。
    // 现在改成整窗慢慢挪：一半藏在边外 6.5 秒 → 1.5 秒挪出来 → 停 3.6 秒 → 1.3 秒缩回去。
    // 图像不动地方，只把窗口推出去，看着像人扒着边框往外探身（乔巴那几张就是这个动作）。
    private long peekT0 = 0;
    private int peekLastX = Integer.MIN_VALUE;
    private long touchAt = 0;
    private long lastTapAt = 0;   // v128 双击判定：500ms 内第二下才算双击

    // 自己会走：站着待一会儿，然后沿着当前高度走 2~4 秒，走到边就掉头
    private boolean walking = false;
    private int walkDir = 0;
    private long walkUntilAt = 0;
    private long walkNextAt = 0;

    private void walkDrift() {
        long now = System.currentTimeMillis();
        // v128：原来只挡 2 秒，戳完一放手两三秒内又自己开走，走出屏幕；改成 8 秒
        if (now - touchAt < 8000) {
            if (walking) { walking = false; if (pv != null) pv.walking = false; }
            walkNextAt = now + 6000;
            return;
        }
        if (!walking) {
            if (walkNextAt == 0) walkNextAt = now + 3000 + (long) (Math.random() * 4000);
            if (now < walkNextAt) return;
            walking = true;
            walkDir = Math.random() < 0.5 ? -1 : 1;   // 只决定朝左还是朝右迈，不再挪窗口
            walkUntilAt = now + 3000 + (long) (Math.random() * 2200);
            if (pv != null) pv.walking = true;
        }
        // 2026-11-25 用户：走路不是移动。以前这里把整个悬浮窗按 2dp/拍往横里推
        // （≈22dp/秒，走 3~5 秒就是横穿小半屏），看着就是"点它一下它就跑掉了"。
        // 现在窗口原地不动，只播迈步动画（walk8 帧 + 骨盆与分腿位移），人站在原地迈腿。
        if (now > walkUntilAt) {
            walking = false;
            walkNextAt = now + 3500 + (long) (Math.random() * 3500);
            if (pv != null) pv.walking = false;
        }
    }

    private void peekDrift() {
        // v129：手碰过 20 秒内不探头（原来 2.5 秒，戳完一会儿又从边上缩回去，看着像自己溜走）
        if (System.currentTimeMillis() - touchAt < 20000) return;
        if (peekT0 == 0) peekT0 = System.currentTimeMillis();
        long cyc = 13000L;
        long p = (System.currentTimeMillis() - peekT0) % cyc;
        int w = lp.width;
        // 2026-11-22 夜：换「半身探头 + 手扒边框」的姿态后，窗口不再半隐——人本身已经是半身构图，
        // 再藏一半就只剩四分之一。现在整窗贴边，只在 ±6% 身宽里轻轻探进探出。
        int baseX = side == SIDE_LEFT ? 0 : sw - w;
        int outX = baseX + (side == SIDE_LEFT ? (int) (w * 0.06f) : -(int) (w * 0.06f));
        float f;
        if (p < cyc * 0.50f) f = 0f;
        else if (p < cyc * 0.62f) { float u = (p - cyc * 0.50f) / (cyc * 0.12f); f = u * u * (3 - 2 * u); }
        else if (p < cyc * 0.90f) f = 1f;
        else { float u = (p - cyc * 0.90f) / (cyc * 0.10f); float s = u * u * (3 - 2 * u); f = 1f - s; }
        int x = baseX + (int) ((outX - baseX) * f);
        if (x != peekLastX) {
            peekLastX = x;
            lp.x = x;
            try { wm.updateViewLayout(pv, lp); } catch (Exception e) { }
        }
    }

    // ---------------- 通知 ----------------

    /** 换形象：按 ARTS 的顺序往下轮一个，转一圈回到开头。通知按钮和长按桌宠都走这里 */
    private void cycleArt() {
        try {
            int at = 0;
            for (int i = 0; i < ARTS.length; i++) if (ARTS[i] == art) at = i;
            art = ARTS[(at + 1) % ARTS.length];
            sp.edit().putInt("art", art).apply();
            if (pv != null) pv.setArt(art);
            refreshNotif();
        } catch (Exception e) { }
    }

    private String modeText() {
        switch (mode) {
            case MODE_FULL: return "满身站在桌面上";
            case MODE_PEEK: return (side == SIDE_LEFT ? "扒着左边" : "扒着右边") + "偷看";
            case MODE_BALL: return "缩成一颗小球";
            default: return "收起了，点通知唤回";
        }
    }

    private PendingIntent servicePi(String action, int m, int req) {
        Intent i = new Intent(this, DaoOverlay.class);
        i.setAction(action);
        if (m >= 0) i.putExtra("mode", m);
        int fl = PendingIntent.FLAG_UPDATE_CURRENT;
        if (Build.VERSION.SDK_INT >= 23) fl |= PendingIntent.FLAG_IMMUTABLE;
        return PendingIntent.getService(this, req, i, fl);
    }

    private PendingIntent appPi() {
        Intent i = new Intent(this, DaoActivity.class);
        i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_SINGLE_TOP);
        int fl = PendingIntent.FLAG_UPDATE_CURRENT;
        if (Build.VERSION.SDK_INT >= 23) fl |= PendingIntent.FLAG_IMMUTABLE;
        return PendingIntent.getActivity(this, 11, i, fl);
    }

    private Notification buildNotif() {
        Notification.Builder b;
        if (Build.VERSION.SDK_INT >= 26) {
            NotificationManager nm = (NotificationManager) getSystemService(NOTIFICATION_SERVICE);
            try {
                NotificationChannel ch = new NotificationChannel(CH, "道 在桌面上", NotificationManager.IMPORTANCE_LOW);
                ch.setShowBadge(false);
                ch.setSound(null, null);
                nm.createNotificationChannel(ch);
            } catch (Exception e) { }
            b = new Notification.Builder(this, CH);
        } else {
            b = new Notification.Builder(this);
        }
        b.setSmallIcon(R.mipmap.ic_launcher)
                .setContentTitle("道 · 在手机桌面上")
                .setContentText(modeText())
                .setOngoing(true)
                .setShowWhen(false)
                .setContentIntent(appPi());
        try {
            b.addAction(0, "满身", servicePi(A_MODE, MODE_FULL, 21));
            b.addAction(0, "贴边", servicePi(A_MODE, MODE_PEEK, 22));
            b.addAction(0, "换形象", servicePi(A_ART, -1, 25));
            b.addAction(0, "球", servicePi(A_MODE, MODE_BALL, 23));
            b.addAction(0, "收起", servicePi(A_STOP, -1, 24));
        } catch (Exception e) { }
        return b.build();
    }

    private void startForegroundSafe() {
        try {
            startForeground(NID, buildNotif());
        } catch (Exception e) { }
    }

    private void refreshNotif() {
        try {
            NotificationManager nm = (NotificationManager) getSystemService(NOTIFICATION_SERVICE);
            nm.notify(NID, buildNotif());
        } catch (Exception e) { }
    }

    // ---------------- 画 ----------------
    private static PetView sLive;   // 当前挂着的悬浮窗，供「换动作」这类外部调用

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
    }
    /** 2026-11-25 外部切换坐骑：0 无 / 1 祥云 / 2 木马。手机主界面「坐骑」按钮走这里。 */
    public static void setMount(int k) {
        if (sLive != null) sLive.setMountArt(k);
    }

    /** v130 外部把坐骑交回给道自己决定（主界面长按「坐骑」按钮走这里）。 */
    public static void setMountAuto(boolean auto) {
        if (sLive != null) sLive.setMountAuto(auto);
    }

    /** 外部（手机主界面「换动作」按钮）让桌面上的那只动一下。 */
    static boolean sendAction(int k) {
        PetView v = sLive;
        if (v == null) return false;
        v.playAction(k);
        return true;
    }


    private class PetView extends View {
        private Bitmap sheet;
        private Bitmap ballArt;      // 球头像专用图（assets/ball.png），有就用它，比从八帧里裁更清楚
        private Bitmap ballHappy, ballSleep, ballSur;   // 三种表情：开心 / 困 / 惊讶
        private Bitmap peekArt;      // 贴边探头的半身姿态（assets/peek.png）
        private Bitmap standArt;     // 正面站姿（assets/stand_<序号>.png）：站着时面向你，不是侧脸
        private Bitmap[] frames;     // 八帧拆开存，供网格变形逐帧用
        private float walkAmp = 1f;  // 行走幅度倍率：v125 起由起停过渡算出（0→1→0）
    private long walkOnAt = 0, walkOffAt = 0;   // 起步/停步时刻，用来算 300ms 过渡
    // 2026-11-25 坐骑：0 无坐骑 / 1 祥云 / 2 木马
    private int mount = 0;   // 0 无坐骑，1~N 对应 MOUNT_FILES 里的图
    private boolean mountAuto = true;   // 自主：每次启动自己决定骑不骑；用户点一下就接管
    // v129 人物与坐骑匹配：每只坐骑单独给「高度占视窗的比例」和「脚踩到它多高」
    // 数值来自 tools\形象\坐骑配比_v129g.py 的实测与预览（_配比预览6.png）
    private final float[] MOUNT_MHW = {0.32f, 0.52f, 0.34f, 0.50f, 0.46f};  // 坐骑高 / 视窗高（骑姿版）
    private final float[] MOUNT_FR = {0.88f, 0.64f, 0.62f, 0.62f, 0.44f};   // 鞍面高度 / 坐骑高（从底算）
    // v131 骑姿：臀部（坐骨线）落在鞍面；数值 = 坐骨线在骑姿图里占的高度比例（逐只量出来的）
    private final float[] RIDE_SEAT = {0.606f, 0.668f, 0.680f, 0.665f, 0.680f, 0.652f, 0.680f,
                                       0.579f, 0.600f, 0.667f, 0.680f, 0.608f, 0.597f, 0.680f};
    private final float RIDE_H = 0.62f;   // 骑姿人物高 / 视窗高
    private final String[] RIDE_FILES = {
            "ride_0.png", "ride_1.png", "ride_2.png", "ride_3.png", "ride_4.png", "ride_5.png", "ride_6.png",
            "ride_7.png", "ride_8.png", "ride_9.png", "ride_10.png", "ride_11.png", "ride_12.png", "ride_13.png"};
    private final float MOUNT_CS = 0.74f;                                   // 骑上时人物缩放，留出头顶空间
    private final String[] MOUNT_FILES = {
            "mount_cloud.png",   // 1 祥云
            "mount_horse.png",   // 2 小木马
            "mount_sword.png",   // 3 飞剑
            "mount_deer.png",    // 4 小鹿
            "mount_crane.png"    // 5 纸鹤
    };
    private Bitmap[] mounts = new Bitmap[MOUNT_FILES.length];
    private Bitmap[] rides = new Bitmap[14];   // 14 张骑姿立绘，下标 = 形象序号
        private Bitmap waveArt;                    // v134 挥手动作立绘
        private long happyUntil = 0;
        // 2026-11-23：打招呼/被戳时抬手挥一挥（网格驱动，不是换图）。只对满身站姿生效，走路和贴边不抢戏。
        private long waveUntil = 0;
        private static final long WAVE_MS = 4200;
        private long nodUntil = 0;           // 应声点头 1.4 秒，只在开口那一下
        private long nextIdleWave = 0;       // 自己每隔 8~15 分钟抬手挥一次，白天才挥
        // 2026-11-25：原来只会走路和挥手，戳它也没别的反应，所以看着「不会做动作」。
        // 加四个网格动作（挥手 / 点头 / 小跳 / 蹲一下），自己按拍子演，也能被「换动作」叫起来。
        private long hopUntil = 0;
        private long squatUntil = 0;
        private long nextActAt = 0;
        private int lastAct = -1;

        private int fw = 192, fh = 384;
        private int fN = 8;
        private Paint p = new Paint(Paint.FILTER_BITMAP_FLAG | Paint.ANTI_ALIAS_FLAG);
        private Paint bp = new Paint(Paint.ANTI_ALIAS_FLAG);
        private int vm = MODE_FULL;
        boolean walking = false;   // 由外层 walkDrift 控制：真在移动时才播走路帧
        // 2026-11-22：桌面图标也打招呼。10 分钟内不重复，白天才开口，晚上只轻轻应一下
        private long lastGreet = 0;
        private String[] greetLines = { "道在这儿呢。", "来啦。", "我在这儿，你说。", "嗯，我在。" };

        PetView() {
            super(DaoOverlay.this);
            setLayerType(View.LAYER_TYPE_HARDWARE, null);
            sLive = this;
            reloadSheet();
        }

        void reloadSheet() {
            // 2026-11-24 夜：形象按「序号」各有一套八帧表（walk8_<序号>.png）；
            // 少女那套是真手绘八帧（walk8.png），其它 13 个是从立绘按骨链位移烘出来的，
            // 腿会左右交替、脚下有起伏，比"整张立绘斜着切"像走路。缺表就退回少女那套。
            sheet = null;
            if (art != ART_WALK) {
                try {
                    BitmapFactory.Options o0 = new BitmapFactory.Options();
                    o0.inScaled = false;
                    sheet = BitmapFactory.decodeStream(
                            getContext().getAssets().open("walk8_" + art + ".png"), null, o0);
                } catch (Exception e) {
                    sheet = null;
                }
            }
            if (sheet == null) {
                try {
                    BitmapFactory.Options o = new BitmapFactory.Options();
                    o.inScaled = false;
                    sheet = BitmapFactory.decodeStream(getContext().getAssets().open("walk8.png"), null, o);
                } catch (Exception e) {
                    sheet = null;
                }
            }
            if (sheet != null && sheet.getHeight() > 0) {
                fh = sheet.getHeight();
                fN = 8;
                fw = sheet.getWidth() / fN;
                if (fw <= 0) { fw = fh / 2; fN = 1; }
            }
            if (sheet != null && !sheet.isRecycled()) matteInPlace(sheet);
            try {
                BitmapFactory.Options bo = new BitmapFactory.Options();
                bo.inScaled = false;
                ballArt = BitmapFactory.decodeStream(getContext().getAssets().open("ball.png"), null, bo);
            } catch (Exception e) {
                ballArt = null;   // 没这张图就退回"从八帧里裁头像"
            }
            ballHappy = loadOpt("ball_happy.png");
            ballSleep = loadOpt("ball_sleep.png");
            ballSur = loadOpt("ball_sur.png");
            peekArt = loadOpt("peek.png");
            if (peekArt != null && !peekArt.isRecycled()) matteInPlace(peekArt);
            // 2026-11-25：原来站着时停在八帧的第 0 帧，那是个侧身迈步的姿势，看着像永远在走路。
            // 现在单独加载正面站姿，站着就面向你。
            standArt = loadOpt("stand_" + art + ".png");
            // v134：挥手专用动作立绘（14 只各一张，抬右手招手），挥手时直接换这张
            waveArt = loadOpt("wave_" + art + ".png");
            if (standArt != null && !standArt.isRecycled()) matteInPlace(standArt);
            if (waveArt != null && !waveArt.isRecycled()) matteInPlace(waveArt);
            // 2026-11-25 坐骑素材：五只都是透明底，进来先过一遍 matte，免得边上带白
            for (int i = 0; i < MOUNT_FILES.length; i++) {
                mounts[i] = loadOpt(MOUNT_FILES[i]);
                if (mounts[i] != null && !mounts[i].isRecycled()) matteInPlace(mounts[i]);
            }
            // v131：骑姿立绘（只有这三只形象有，别的仍用站姿）
            rides = new Bitmap[RIDE_FILES.length];
            for (int i = 0; i < RIDE_FILES.length; i++) {
                rides[i] = loadOpt(RIDE_FILES[i]);
                if (rides[i] != null && !rides[i].isRecycled()) matteInPlace(rides[i]);
            }
            try {
                android.content.SharedPreferences spd = getContext().getSharedPreferences("dao", 0);
                mountAuto = spd.getBoolean("mountAuto", true);
                mount = spd.getInt("mount", 0);
                if (mountAuto) {
                    // 自主决定：六成概率骑一只，四成不骑（它自己也该有不骑的时候）
                    mount = (Math.random() < 0.6)
                            ? 1 + (int) (Math.random() * Math.max(1, mounts.length - 1)) : 0;
                }
            } catch (Throwable e) { mount = 0; mountAuto = true; }
            // 2026-11-22 夜：形象不再「一张图定住」，改成按骨骼权重做网格变形。
            // 先把八帧拆成独立位图，变形时直接取当前帧，省掉每帧 createBitmap。
            try {
                if (sheet != null && fN > 0 && fw > 0) {
                    frames = new Bitmap[fN];
                    for (int i = 0; i < fN; i++) {
                        frames[i] = Bitmap.createBitmap(sheet, i * fw, 0, fw, fh);
                    }
                }
            } catch (Throwable e) {
                frames = null;
            }
            invalidate();
        }

        /**
         * 2026-11-22：walk8.png 的白底是半透明白（alpha 139~197），挂在桌面上就是一块白板。
         * 只清「从四边连通过来」的近白像素——人物身上的白裙/白鞋与边缘不连通，不会被挖掉。
         */
        void keyWhite() {
            try {
                int w = sheet.getWidth(), h = sheet.getHeight();
                int[] px = new int[w * h];
                sheet.getPixels(px, 0, w, 0, 0, w, h);
                boolean[] seen = new boolean[w * h];
                int[] q = new int[w * h];
                int head = 0, tail = 0;
                for (int x = 0; x < w; x++) {
                    tail = pushIfWhite(px, seen, q, tail, x, w);
                    tail = pushIfWhite(px, seen, q, tail, x, (h - 1) * w);
                }
                for (int y = 0; y < h; y++) {
                    tail = pushIfWhite(px, seen, q, tail, 0, y * w + 0);
                    tail = pushIfWhite(px, seen, q, tail, w - 1, y * w + w - 1);
                }
                while (head < tail) {
                    int idx = q[head++];
                    px[idx] = 0x00000000;
                    int x = idx % w, y = idx / w;
                    if (x > 0) tail = pushIfWhite(px, seen, q, tail, x - 1, idx - 1);
                    if (x < w - 1) tail = pushIfWhite(px, seen, q, tail, x + 1, idx + 1);
                    if (y > 0) tail = pushIfWhite(px, seen, q, tail, x, idx - w);
                    if (y < h - 1) tail = pushIfWhite(px, seen, q, tail, x, idx + w);
                }
                deFringe(px, w, h, seen);      // 紧贴人物的那圈白混色，不清掉就是白边
                sheet.setPixels(px, 0, w, 0, 0, w, h);
            } catch (Exception e) { }
        }

        int pushIfWhite(int[] px, boolean[] seen, int[] q, int tail, int x, int idx) {
            if (idx < 0 || idx >= px.length || seen[idx]) return tail;
            if (!nearWhite(px[idx])) return tail;
            seen[idx] = true;
            q[tail] = idx;
            return tail + 1;
        }

        /** 白底素材统一处理：泛洪清底 + 边缘去白。
         *  立绘/站姿/探头这几张都不是透明底，边缘那圈是「白+人物色」的混色，
         *  只把纯白挖掉，剩下的混色圈挂在深色桌面上就是一道白边。 */
        void matteInPlace(Bitmap b) {
            try {
                int w = b.getWidth(), h = b.getHeight();
                int[] px = new int[w * h];
                b.getPixels(px, 0, w, 0, 0, w, h);
                boolean[] bg = new boolean[w * h];
                int[] q = new int[w * h];
                int head = 0, tail = 0;
                for (int x = 0; x < w; x++) {
                    tail = pushIfWhite(px, bg, q, tail, x, x);
                    tail = pushIfWhite(px, bg, q, tail, x, (h - 1) * w + x);
                }
                for (int y = 0; y < h; y++) {
                    tail = pushIfWhite(px, bg, q, tail, y, y * w);
                    tail = pushIfWhite(px, bg, q, tail, y, y * w + w - 1);
                }
                while (head < tail) {
                    int idx = q[head++];
                    px[idx] = 0;
                    int x = idx % w, y = idx / w;
                    if (x > 0) tail = pushIfWhite(px, bg, q, tail, x - 1, idx - 1);
                    if (x < w - 1) tail = pushIfWhite(px, bg, q, tail, x + 1, idx + 1);
                    if (y > 0) tail = pushIfWhite(px, bg, q, tail, x, idx - w);
                    if (y < h - 1) tail = pushIfWhite(px, bg, q, tail, x, idx + w);
                }
                deFringe(px, w, h, bg);
                // 素材自带的「半透明近白」混色：这类像素四边 alpha 早就是 0，
                // 泛洪从第一步就够不着，所以只挖纯白是清不掉白边的。按亮度定遮罩。
                for (int i = 0; i < px.length; i++) {
                    int c = px[i];
                    int a = c >>> 24;
                    if (a <= 6 || a >= 250) continue;
                    int r = (c >> 16) & 0xFF, g = (c >> 8) & 0xFF, bl = c & 0xFF;
                    int lum = Math.min(r, Math.min(g, bl));
                    if (lum < 215) continue;                       // 只打近白，浅色衣服不动
                    float k = (255 - lum) / 40f;
                    if (k > 1f) k = 1f;
                    px[i] = ((int) (a * k) << 24) | (c & 0x00FFFFFF);
                }
                b.setPixels(px, 0, w, 0, 0, w, h);
            } catch (Exception e) { }
        }

        /** 沿已清掉的底色向内走两圈：这几圈像素是背景白和人物色的混色，
         *  按白度估半透明 alpha，再按 alpha 把混进去的白扣掉，边上就干净了。 */
        void deFringe(int[] px, int w, int h, boolean[] bg) {
            for (int pass = 0; pass < 2; pass++) {
                int[] cp = px.clone();
                for (int y = 0; y < h; y++) {
                    for (int x = 0; x < w; x++) {
                        int idx = y * w + x;
                        if (bg[idx]) continue;
                        boolean nb = (x > 0 && bg[idx - 1]) || (x < w - 1 && bg[idx + 1])
                                || (y > 0 && bg[idx - w]) || (y < h - 1 && bg[idx + w]);
                        if (!nb) continue;
                        int c = cp[idx];
                        int a = c >>> 24;
                        if (a < 40) continue;
                        int r = (c >> 16) & 0xFF, g = (c >> 8) & 0xFF, bl = c & 0xFF;
                        int lum = Math.min(r, Math.min(g, bl));
                        int mx = Math.max(r, Math.max(g, bl));
                        if (mx - lum > 28 || lum < 140) continue;      // 只处理接近白的混色
                        float s = (255 - lum) / 78f;
                        if (s > 1f) s = 1f;
                        if (s < 0.04f) s = 0.04f;
                        float inv = s < 0.10f ? 0.10f : s;
                        int rr = (int) Math.max(0, Math.min(255, (r - 255f * (1f - s)) / inv));
                        int gg = (int) Math.max(0, Math.min(255, (g - 255f * (1f - s)) / inv));
                        int bb = (int) Math.max(0, Math.min(255, (bl - 255f * (1f - s)) / inv));
                        px[idx] = ((int) (a * s) << 24) | (rr << 16) | (gg << 8) | bb;
                        bg[idx] = true;                              // 已处理 → 往外再扩一圈
                    }
                }
            }
        }

        boolean nearWhite(int c) {
            int a = (c >>> 24);
            if (a < 60) return false;                      // 已经透明，别扩散
            int r = (c >> 16) & 0xFF, g = (c >> 8) & 0xFF, b = c & 0xFF;
            if (r < 225 || g < 225 || b < 225) return false;
            int mx = Math.max(r, Math.max(g, b)), mn = Math.min(r, Math.min(g, b));
            return (mx - mn) <= 14;                        // 近中性白，彩色的浅色别当背景
        }

        /** 头像方框：第 0 帧的脸（实测脸在 x88-137 / y49-95，连头发取 0.52 边长的方块，居中偏右） */
        private Rect headRect() {
            int side = (int) (fw * 0.52f);
            int x0 = (int) (fw * 0.26f);
            int y0 = (int) (fh * 0.045f);
            int x1 = Math.min(fw, x0 + side);
            int y1 = Math.min(fh, y0 + side);
            return new Rect(x0, y0, x1, y1);
        }

        Bitmap loadOpt(String name) {
            try {
                BitmapFactory.Options o = new BitmapFactory.Options();
                o.inScaled = false;
                return BitmapFactory.decodeStream(getContext().getAssets().open(name), null, o);
            } catch (Exception e) {
                return null;
            }
        }

        /**
         * 2026-11-24 夜：桌面上换形象。
         * 只有 ART_WALK 那个少女有真八帧走路素材（walk8.png）；其它 13 个的立绘是
         * 192×384 画布、底对齐、水平居中（跟八帧同比例），所以满身/贴边都能直接挂上去，
         * 走路用 drawWarp 的迈步变形代一下——腿不会真交替，但人确实在挪、下身会摆。
         */
        Bitmap rideFor(int k) {
            return (k >= 0 && k < rides.length) ? rides[k] : null;
        }

        /** v131 骑姿绘制：坐骑按自己的高度比 → 鞍面定位 → 臀部（坐骨线）压上去 */
        void drawRide(Canvas c, int w, int h, Bitmap rideImg, Bitmap mb) {
            int mi = Math.max(0, Math.min(MOUNT_MHW.length - 1, mount - 1));
            float mh = h * MOUNT_MHW[mi];
            float mw = mh * mb.getWidth() / Math.max(1, mb.getHeight());
            if (mw > w * 0.98f) {
                mw = w * 0.98f;
                mh = mw * mb.getHeight() / Math.max(1, mb.getWidth());
            }
            double mt = (System.currentTimeMillis() % 600000L) / 1000.0;
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
            c.restore();

            float saddleY = h - mh * MOUNT_FR[mi];
            float rh = h * RIDE_H;
            float rw = rh * rideImg.getWidth() / Math.max(1, rideImg.getHeight());
            if (rw > w * 0.92f) {
                rw = w * 0.92f;
                rh = rw * rideImg.getHeight() / Math.max(1, rideImg.getWidth());
            }
            float si = Math.max(0, Math.min(RIDE_SEAT.length - 1, DaoOverlay.this.art));
            float sr = RIDE_SEAT[(int) si];
            float top = saddleY - rh * sr + mdy;
            // 说话时上身轻轻点头，像在应声说话（骑乘图是整张立绘，做不了逐字口型，用这点动感代）
            if (System.currentTimeMillis() < talkUntil) top += (float) Math.sin(mt * 9.0) * 0.006f * h;
            RectF rr = new RectF(w * 0.5f + mdx - rw * 0.5f, top, w * 0.5f + mdx + rw * 0.5f, top + rh);
            c.drawBitmap(rideImg, null, rr, p);
            c.restore();
        }

        void setArt(int k) {
            art = k;
            reloadSheet();
            invalidate();
        }

        void setMode(int m) {
            vm = m;
            invalidate();
        }

        @Override
        protected void onDraw(Canvas c) {
            super.onDraw(c);
            int w = getWidth(), h = getHeight();
            if (vm == MODE_BALL) { drawBall(c, w, h); return; }

            // v131 骑乘：这只形象有骑姿立绘，就直接画"跨坐"的样子，不再拿站姿缩放去凑
            Bitmap rb = rideFor(art);
            if (mount > 0 && rb != null && !rb.isRecycled()
                    && mounts[mount - 1] != null && !mounts[mount - 1].isRecycled()) {
                drawRide(c, w, h, rb, mounts[mount - 1]);
                return;
            }

            if (sheet == null || sheet.isRecycled()) {
                Paint q = new Paint();
                q.setColor(0xFF9FBCE8);
                c.drawRoundRect(new RectF(2, 2, w - 2, h - 2), 12, 12, q);
                return;
            }
            // 2026-11-22：满身时 8 帧慢走（3 拍一帧 ≈2.8fps）。贴边时不再原地踏步——
            // 那种"人不动腿在动"最假，改成定格站姿，动的是窗口本身的探出/缩回。
            // 2026-11-25 提帧 + 起停过渡：相位按真实时间算；起步 400ms 渐入、停步 400ms 渐出，
            // 停步时相位冻结在停步那一刻，最后一步原地收住，再切成站姿——原来是一停就直接定格
            long nowD = System.currentTimeMillis();
            if (walking) { if (walkOnAt == 0) walkOnAt = nowD; walkOffAt = 0; }
            else if (walkOnAt != 0 && walkOffAt == 0) walkOffAt = nowD;
            double rampT = walking ? (nowD - walkOnAt) / 400.0
                                   : (walkOffAt == 0 ? 1.0 : 1.0 - (nowD - walkOffAt) / 400.0);
            rampT = Math.max(0.0, Math.min(1.0, rampT));
            float ramp = (float) (0.5 - 0.5 * Math.cos(rampT * Math.PI));   // 余弦缓动：起停都软
            if (!walking && ramp <= 0.02f) { walkOnAt = 0; walkOffAt = 0; }
            boolean walkDraw = walking || ramp > 0.02f;
            double walkPos = 0;
            if (walkDraw) {
                long tw = walking ? nowD : walkOffAt;    // 停步后冻结相位：腿收住不再往前迈
                walkPos = (tw % 600000L) / 1000.0 * 5.5;  // 5.5 扑/秒，与原 180ms 一帧等价
            }
            walkAmp = ramp;
            int fi;
            int bob;
            if (vm == MODE_PEEK) {
                fi = 0;
                bob = (int) (Math.sin(tick / 22.0) * (h * 0.0015f));   // 只剩一点点呼吸的起伏
            } else {
                // 走的时候播 8 帧走路，站着就定格第 0 帧；窗口真的在移动，腿才动
                if (walking) {
                    // 一拍 180ms → 5.5fps。原来 270ms 才换一帧（3.7fps），配 22dp/秒的步速，
                    // 腿看着像在原地小碎步，跟脚的位移对不上
                    fi = fN > 0 ? (int) (walkPos % fN) : 0;
                    bob = (int) (Math.sin(tick / 4.0) * (h * 0.006f));
                } else {
                    fi = 0;
                    bob = (int) (Math.sin(tick / 9.0) * (h * 0.004f));
                }
            }
            float lean = 0;
            Rect src = new Rect(fi * fw, 0, fi * fw + fw, fh);
            Rect dst = new Rect(0, bob, w, h + bob);
            // v132：放歌就跳舞 —— 以脚跟为轴左右摆、上下弹；坐骑跟着一起颠
            long dnNow = System.currentTimeMillis();
            boolean dancing = dnNow < danceUntil;
            if (dancing) {
                double dt = (dnNow % 600000L) / 1000.0;
                c.save();
                c.rotate((float) Math.sin(dt * 5.0) * 4.5f, w * 0.5f, h * 0.99f);
                c.translate((float) Math.sin(dt * 5.0) * w * 0.018f, -(float) Math.abs(Math.sin(dt * 5.0)) * h * 0.035f);
            }
            // 脚下一点软阴影：不然人是"飘"在白底上的，落地感差
            Paint sh = new Paint(Paint.ANTI_ALIAS_FLAG);
            sh.setColor(0x22000000);
            c.drawOval(new RectF(w * 0.24f, h + bob - h * 0.03f, w * 0.76f, h + bob + h * 0.005f), sh);
            // 2026-11-25 坐骑：先把它画在脚下，人物再叠上去（不镜像、不跟着蹲，坐骑是地面上的东西）
            float rise = 0f;
            Bitmap mb = (mount >= 1 && mount <= mounts.length ? mounts[mount - 1] : null);  // v131 修：原来下标越界，纸鹤永远画不出来
            float mdx = 0f, mdy = 0f;
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
            }
            c.save();
            float ms = (mb != null && !mb.isRecycled()) ? MOUNT_CS : 1f;
            if (ms < 1f) {
                // 以底边中点为锚点缩小：脚的位置不动，头自动让出空间（原来头会被抬出画布）
                c.translate(w * 0.5f * (1f - ms), h * (1f - ms));
                c.scale(ms, ms);
            }
            if (rise > 0f) c.translate(0, -rise / ms);
            if (mdx != 0f || mdy != 0f) c.translate(mdx, mdy);   // 云飘/马颠时人得跟着一起动，不然脱开
            // 挥手只给满身站姿：走路时腿在动、贴边时手搭在框上，这两种都不该再挥手
            float waveAmp = 0f;
            long nowMs = System.currentTimeMillis();
            if ((vm == MODE_FULL || vm == MODE_PEEK) && !walking && nowMs < waveUntil && waveUntil - nowMs <= WAVE_MS) {
                float prog = 1f - (waveUntil - nowMs) / (float) WAVE_MS;
                waveAmp = waveEnv(prog);                      // 快起、停一会、慢落（不是对称正弦）
            }
            // 应声点头：1.4 秒里点两下，幅度随起随落衰减，只动头不动身
            float nodAmp = 0f;
            if (vm == MODE_FULL && nowMs < nodUntil) {
                float prog2 = 1f - (nodUntil - nowMs) / 1400f;
                // 真点头是两下：包络里套 2 个周期的余弦，0→1→0→1→0，峰在 1/4、3/4 处
                nodAmp = waveEnv(prog2) * (0.5f - 0.5f * (float) Math.cos(prog2 * Math.PI * 4f));
            }
            // 小跳 / 蹲一下：整只抬起来或压下去，脚底始终贴着原来的地平线
            float hop = 0f, squash = 1f;
            if (nowMs < hopUntil) {
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
            }
            if (nowMs < squatUntil) {
                float pr = 1f - (squatUntil - nowMs) / 1600f;
                squash = 1f - 0.085f * (float) Math.sin(pr * Math.PI);
            }
            if (squash < 1f) {   // 蹲：压扁的同时横向放宽，体积守恒 → 看着是屈膝，不是整体缩小
                float sx2 = 1f / squash;   // 严格体积守恒：宽 = 1/高
                c.translate(w * 0.5f, 0);
                c.scale(sx2, 1f);
                c.translate(-w * 0.5f, 0);
            }
            if (walkDraw && walkDir < 0) { c.translate(w, 0); c.scale(-1f, 1f); }   // 向左走就把整帧镜像，别让它倒着迈步
            if (vm == MODE_PEEK && side == SIDE_RIGHT) { c.translate(w, 0); c.scale(-1f, 1f); }   // 在右边扒边，手要朝右
            if (vm == MODE_PEEK) { c.rotate((float) Math.sin(tick / 38.0) * 1.2f, w / 2f, h * 0.98f); }  // 探头时轻轻晃，不是一张死图
            c.translate(lean, 0);
            if (vm == MODE_PEEK && art == ART_WALK && peekArt != null && !peekArt.isRecycled()) {
                drawWarp(c, peekArt, 0, bob, w, h + bob, tick / 30.0, 0f, false, true, waveAmp, 0f);   // 贴边：半身探头 + 慢晃 + 呼吸 + 左右看
            } else if (vm != MODE_PEEK && !walkDraw && waveAmp > 0f
                    && waveArt != null && !waveArt.isRecycled()) {
                // v134：挥手换成真动作立绘（抬右手那张），只叠轻摆；网格硬掰看不出手在抬
                int dyW = (int) (h * (1f - squash));
                drawWarp(c, waveArt, 0, bob - (int) hop + dyW, w, (int) (h * squash) + bob,
                        tick / 30.0, 0f, false, false, 0f, nodAmp);
            } else if (vm != MODE_PEEK && !walkDraw && standArt != null && !standArt.isRecycled()) {
                int dyAct = (int) (h * (1f - squash));
                drawWarp(c, standArt, 0, bob - (int) hop + dyAct, w, (int) (h * squash) + bob,
                        tick / 30.0, 0f, false, false, waveAmp, nodAmp);
            } else if (frames != null && fi >= 0 && fi < frames.length) {
                float ph = (float) ((walkPos % fN) / Math.max(1, fN) * Math.PI * 2.0);   // 连续相位：换帧处正好归整
                drawWarp(c, frames[fi], 0, bob, w, h + bob, tick / 30.0, ph, walkDraw, false, waveAmp, nodAmp);
            } else {
                c.drawBitmap(sheet, src, dst, p);
            }
            c.restore();
            if (dancing) c.restore();
        }

        /**
         * 2026-11-22 夜：立绘不再「贴一张图不动」，改成网格变形（相当于轻量骨骼）：
         *   腰部以下摆、发梢延迟跟随、胸腔随呼吸起伏、头部轻侧倾、走路时下身前后剪切。
         * 顶点按高度给权重，所以不会出现切图拼接的接缝。
         */
        void drawWarp(Canvas c, Bitmap bm, float left, float top, float w, float h, double t, float phase,
                      boolean walk, boolean peek, float wave, float nod) {
            if (bm == null || bm.isRecycled()) return;
            final int COLS = 8, ROWS = 12;
            float[] v = new float[(COLS + 1) * (ROWS + 1) * 2];
            float breath = (float) Math.sin(t * 1.05);
            float sway = (float) Math.sin(t * 0.52);
            float lag = (float) Math.sin(t * 0.52 - 0.8);
            float tilt = (float) Math.sin(t * 0.47 + 0.5);
            float step = walk ? (float) Math.sin(phase) : 0f;   // 与换帧同频：一轮 8 帧 = 一个步态周期
            float look = (float) Math.sin(t * 0.34);          // 靠墙站时左右看，约 18 秒一个来回
            float hand = (float) Math.max(0f, Math.sin(t * 1.1));  // 手轻轻抬一下，半拍抬起半拍放下
            int i = 0;
            for (int r = 0; r <= ROWS; r++) {
                float ny = r / (float) ROWS;
                float baseY = top + h * ny;
                for (int cc = 0; cc <= COLS; cc++) {
                    float nx = cc / (float) COLS;
                    float baseX = left + w * nx;
                    // 2026-11-25：原来 1.3% / 1.1% 身宽的下身摆动叠头发的延迟跟随，连起来就是「东倒西歪」。
                    // 站着不动时几乎不该晃，压到 0.5% / 0.45%，只留一点呼吸感。
                    float dx = 0.005f * w * sway * (float) Math.pow(ny, 1.7f)
                             + 0.0045f * w * lag * (float) Math.pow(ny, 2.3f);
                    float dy = -0.007f * h * breath * (float) Math.exp(-Math.pow((ny - 0.44) / 0.20, 2));
                    // v132 口型：嘴所在那条带（约 0.20~0.29 身高）随语音开合，约 6Hz，像真的在说
                    if (System.currentTimeMillis() < talkUntil) {
                        float jaw = (float) Math.exp(-Math.pow((ny - 0.245) / 0.048, 2));
                        dy += 0.013f * h * jaw * (0.5f - 0.5f * (float) Math.cos(t * 38.0));
                    }
                    if (ny < 0.30f) {
                        // 2026-11-23 修扭曲：侧倾系数 0.7*h 是按早期大立绘调的，缩到 180px 高以后
                        // 头顶会横移近 40px，头跟脖子像被撕开、脸也拉歪。改成按头宽（约 0.35w）给幅度，
                        // 上限 0.05w，小尺寸下只有轻微侧倾，头身不会再错位。
                        float headShift = tilt * (0.30f - ny) * (0.35f * w) * 0.18f;
                        float capX = 0.018f * w;
                        if (headShift > capX) headShift = capX;
                        if (headShift < -capX) headShift = -capX;
                        dx += headShift;
                    }
                    if (peek) {
                        // 靠墙站：别像钉在墙上。呼吸加重、上身随重心慢慢挪、头左右看、空着的手抬一抬
                        dy += -0.003f * h * breath;
                        dx += 0.006f * w * (float) Math.sin(t * 0.6) * ny * ny;
                        if (ny < 0.32f) dx += 0.009f * w * look * (0.32f - ny) / 0.32f;
                        if (nx < 0.26f && ny > 0.10f && ny < 0.42f) {
                            dx += 0.014f * w * hand * (1f - ny / 0.42f);
                            dy -= 0.010f * h * hand * (1f - nx / 0.26f);
                        }
                    }
                    if (walk && ny > 0.55f && ny <= 0.72f) {                        // 骨盆段：整块轻摆（不超过腰）
                        dx += 0.010f * w * walkAmp * step * (ny - 0.55f) / 0.17f;
                        dy += -Math.abs(step) * 0.006f * walkAmp * h * ny * ny;
                    }
                    if (walk && ny > 0.72f) {
                        // 2026-11-25 骨链第 1 步：膝以下按左右腿分开、反相迈步。
                        // 之前整条下半身共用一个 step，两只脚永远同起同落，看着像整块人左右挪。
                        // sideW 在中线平滑过渡（不是硬切 0.5），中线位移趋 0，裙摆不会被撕开；
                        // 抬脚只抬"往前迈的那条腿"（Math.max(0, leg)），所以左右脚是轮流落地。
                        float sideW = Math.max(-1f, Math.min(1f, (nx - 0.5f) / 0.22f));
                        float legStep = step * sideW;
                        float legK = (ny - 0.72f) / 0.28f;
                        dx += 0.006f * w * walkAmp * legStep * legK;
                        dy += -Math.max(0f, legStep) * 0.010f * h * walkAmp * legK;
                    }
                    if (wave > 0.01f) {
                        // 挥手：只抬画面右侧那条手臂。肩在 0.12~0.30 高度，前臂按 9.5 弧度/秒来回摆，
                        // 越靠手尖位移越大；上身跟着轻轻让一下，免得看着只有一只手在动。
                        if (nx > 0.66f && ny > 0.10f && ny < 0.46f) {
                            float wx = (nx - 0.66f) / 0.34f;
                            float wy = 1f - Math.abs(ny - 0.26f) / 0.20f;
                            if (wy > 0f) {
                                float s = (float) Math.sin(t * 9.5);
                                // 2026-11-23 修扭曲：挥手原来是 0.055w / 0.075h 的大位移，桌面大立绘时像抬手，
                                // 缩到 180px 高就变成整条手臂被抻长、手折到脸边。按像素封顶，小尺寸只抬一点。
                                float wxAmp = 0.055f * w * wave * wx * wx * s;
                                float wyAmp = 0.075f * h * wave * wx * wy;
                                float capXw = 0.022f * w;
                                float capYw = 0.030f * h;
                                if (wxAmp > capXw) wxAmp = capXw; else if (wxAmp < -capXw) wxAmp = -capXw;
                                if (wyAmp > capYw) wyAmp = capYw;
                                dx += wxAmp;
                                dy -= wyAmp;
                            }
                        }
                        if (ny < 0.55f) dx -= 0.008f * w * wave * (float) Math.sin(t * 4.7);
                    }
                    if (nod > 0.01f && ny < 0.32f) {
                        // 点头：绕脖子（ny≈0.30）转，越靠头顶位移越大；13 弧度/秒 ≈ 每秒两下
                        float wy2 = (0.32f - ny) / 0.32f;
                        dy += 0.012f * h * nod * wy2 * (float) Math.sin(t * 13.0);
                    }
                    v[i++] = baseX + dx;
                    v[i++] = baseY + dy;
                }
            }
            c.drawBitmapMesh(bm, COLS, ROWS, v, 0, null, 0, p);
        }

        void drawBall(Canvas c, int w, int h) {
            int cx = w / 2, cy = h / 2, r = Math.min(w, h) / 2 - 2;
            if (r < 6) r = 6;
            // 2026-11-22：球面改成「当天形象的头像」，不再是通用渐变笑脸。
            // 呼吸 3.1 秒一轮（±2%），每 ~4.5 秒眨一下（压扁 6%，一拍 ~90ms）
            float br = 1f + 0.02f * (float) Math.sin(tick * (Math.PI * 2 / 34.0));
            boolean blink = (tick % 50) < 1;
            c.save();
            c.translate(cx, cy);
            c.scale(br, br * (blink ? 0.94f : 1f));

            Paint base = new Paint(Paint.ANTI_ALIAS_FLAG);
            base.setColor(0xFFEFF5FF);
            c.drawCircle(0, 0, r, base);

            if (ballArt != null && !ballArt.isRecycled()) {
                // 专用头像：等比铺满圆，纵向往上抬一点，让眼睛落在圆的上三分之一
                // 表情：刚打过招呼→开心；深夜→困；其余正常
                Bitmap art = ballArt;
                long now = System.currentTimeMillis();
                int hh = java.util.Calendar.getInstance().get(java.util.Calendar.HOUR_OF_DAY);
                if (now < happyUntil && ballHappy != null) art = ballHappy;
                else if ((hh >= 23 || hh < 6) && ballSleep != null) art = ballSleep;
                android.graphics.Path clip2 = new android.graphics.Path();
                clip2.addCircle(0, 0, r, android.graphics.Path.Direction.CW);
                c.save();
                c.clipPath(clip2);
                float s2 = Math.max(r * 2f / art.getWidth(), r * 2f / art.getHeight());
                float dw = art.getWidth() * s2, dh = art.getHeight() * s2;
                float ox = -dw / 2f, oy = -dh / 2f - r * 0.06f;
                RectF dst2 = new RectF(ox, oy, ox + dw, oy + dh);
                c.drawBitmap(art, null, dst2, p);
                c.restore();
            } else if (sheet != null && !sheet.isRecycled()) {
                android.graphics.Path clip = new android.graphics.Path();
                clip.addCircle(0, 0, r, android.graphics.Path.Direction.CW);
                c.save();
                c.clipPath(clip);
                Rect head = headRect();
                float d = r * 2.12f;
                RectF dst = new RectF(-d / 2f, -d / 2f + r * 0.12f, d / 2f, d / 2f + r * 0.12f);
                c.drawBitmap(sheet, head, dst, p);
                c.restore();
            }

            Paint rim = new Paint(Paint.ANTI_ALIAS_FLAG);
            rim.setStyle(Paint.Style.STROKE);
            rim.setStrokeWidth(r * 0.05f + 1);
            rim.setColor(0x99AFC6EA);
            c.drawCircle(0, 0, r, rim);
            c.restore();
        }

        private float dRx, dRy;
        private int wx0, wy0;
        private long t0;
        private boolean moved;

        @Override
        public boolean onTouchEvent(MotionEvent e) {
            switch (e.getActionMasked()) {
                case MotionEvent.ACTION_DOWN:
                    dRx = e.getRawX(); dRy = e.getRawY();
                    wx0 = lp.x; wy0 = lp.y;
                    t0 = System.currentTimeMillis();
                    touchAt = t0;
                    moved = false;
                    // v128：手一碰就先站住，别让人边点边走
                    walking = false;
                    if (pv != null) pv.walking = false;
                    return true;
                case MotionEvent.ACTION_MOVE: {
                    float dx = e.getRawX() - dRx, dy = e.getRawY() - dRy;
                    // v128：阈值 6dp → 16dp。手指按在桌面上天然会抖 2~8dp，
                    // 原来那点抖动就被当成拖动，窗口跟着手指乱窜。
                    if (!moved && (Math.abs(dx) > dp(16) || Math.abs(dy) > dp(16))) moved = true;
                    if (moved) dragTo(wx0 + (int) dx, wy0 + (int) dy);
                    touchAt = System.currentTimeMillis();
                    return true;
                }
                case MotionEvent.ACTION_UP: {
                    long dt = System.currentTimeMillis() - t0;
                    long now = System.currentTimeMillis();
                    touchAt = now;
                    if (moved) {                // 真拖动：只落位，不演动作
                        lastTapAt = 0;
                        onDrop();
                    } else if (dt < 400) {      // 轻点
                        if (lastTapAt != 0 && now - lastTapAt < 500) {
                            lastTapAt = 0;
                            openApp();          // 双击：打开 App
                        } else {
                            lastTapAt = now;
                            onTap();            // 单击：站定应一声
                        }
                    } else {                    // 长按：也只应一声，换形象另走通知按钮
                        lastTapAt = 0;
                        onTap();
                    }
                    return true;
                }
                case MotionEvent.ACTION_CANCEL:
                    onDrop();
                    return true;
            }
            return super.onTouchEvent(e);
        }

        private void dragTo(int nx, int ny) {
            int w = lp.width, h = lp.height;
            if (mode == MODE_PEEK) {
                // 贴边时只让上下挪，横着的半边永远压在边上
                nx = side == SIDE_LEFT ? -w / 2 : sw - w / 2;
                if (ny < -h / 3) ny = -h / 3;
                if (ny > sh - h * 0.66f) ny = (int) (sh - h * 0.66f);
            } else {
                if (nx < -w / 4) nx = -w / 4;
                if (nx > sw - w * 0.75f) nx = (int) (sw - w * 0.75f);
                if (ny < 0) ny = 0;
                if (ny > sh - h) ny = sh - h;
            }
            lp.x = nx; lp.y = ny;
            try { wm.updateViewLayout(this, lp); } catch (Exception e) { }
        }

        private void onDrop() {
            int w = lp.width;
            if (mode == MODE_BALL) {
                // 松手吸到左右两边，跟常见的悬浮球一个脾气
                int mid = lp.x + w / 2;
                int nl = (mid < sw / 2) ? dp(4) : sw - w - dp(4);
                lp.x = nl;
                try { wm.updateViewLayout(this, lp); } catch (Exception e) { }
                sp.edit().putInt("x2", lp.x).putInt("y2", lp.y).apply();
            } else if (mode == MODE_PEEK) {
                sp.edit().putInt("y1", lp.y).apply();
                peekT0 = System.currentTimeMillis() + 1500;   // 手放开先隐一下再探头
                peekLastX = Integer.MIN_VALUE;
            } else if (mode == MODE_FULL) {
                sp.edit().putInt("x0", lp.x).putInt("y0", lp.y).apply();
            }
        }

        private void onTap() {
            // v128：单击只做「站定 + 应一声」，不再一戳就把 App 弹出来（那样看着像人凭空没了）。
            // 要开 App 改成双击。
            long now = System.currentTimeMillis();
            touchAt = now;
            walking = false;
            if (pv != null) pv.walking = false;
            if (vm == MODE_BALL || vm == MODE_PEEK) {
                setModeInternal(MODE_FULL);
            }
            greet(true);
        }

        // 2026-11-23 学来的：对称的 sin(πp) 起落一样慢，看起来机械。真实动作是
        // 「快起—保持—慢起快收」的不对称曲线（Material Decelerate 进、Accelerate 出）。
        // 抬手用 ease-out 三次曲线（0→1 冲得快、末尾收住），放下用 (1-x)^3（先缓，末了收得干脆）。
        float waveEnv(float p) {
            if (p <= 0f) return 0f;
            if (p >= 1f) return 0f;
            if (p < 0.32f) { float x = p / 0.32f, u = 1f - x; return 1f - u * u * u; }   // 起手：快
            if (p < 0.72f) return 1f;                                                     // 中间：稳住挥
            float x = (p - 0.72f) / 0.28f, u = 1f - x; return u * u * u;                    // 收手：先缓后快
        }

        // 2026-11-23：不是只有被戳才动。满身站着的时候，每隔 8~15 分钟自己抬手挥一下，
        // 只在白天（8~21 点）做，晚上不闹；不开口，只动手，避免一天说太多话。
        void idleWaveIfDue() {
            long now = System.currentTimeMillis();
            if (nextIdleWave == 0) {
                nextIdleWave = now + (long) ((8 + Math.random() * 7) * 60 * 1000);
                return;
            }
            if (now < nextIdleWave) return;
            nextIdleWave = now + (long) ((8 + Math.random() * 7) * 60 * 1000);
            int hh = java.util.Calendar.getInstance().get(java.util.Calendar.HOUR_OF_DAY);
            if (hh < 8 || hh > 21) return;
            waveUntil = now + WAVE_MS;
            postInvalidate();
        }

        /** 换坐骑：0 无 1 祥云 2 木马，记进 SharedPreferences，下次启动还在。 */
        void setMountArt(int k) {
            mountAuto = false;   // 用户手动选了，就不再自作主张
            mount = Math.max(0, Math.min(mounts.length - 1, k));
            try { getContext().getSharedPreferences("dao", 0).edit().putBoolean("mountAuto", false).apply(); } catch (Throwable e) { }
            try { getContext().getSharedPreferences("dao", 0).edit().putInt("mount", mount).apply(); } catch (Throwable e) { }
            invalidate();
        }

        /** v130：把坐骑交回给道自己决定（长按按钮）；true 时立刻重新随机一次 */
        void setMountAuto(boolean auto) {
            mountAuto = auto;
            try { getContext().getSharedPreferences("dao", 0).edit().putBoolean("mountAuto", auto).apply(); } catch (Throwable e) { }
            if (auto) {
                mount = (Math.random() < 0.6)
                        ? 1 + (int) (Math.random() * Math.max(1, mounts.length - 1)) : 0;
                try { getContext().getSharedPreferences("dao", 0).edit().putInt("mount", mount).apply(); } catch (Throwable e) { }
            }
            invalidate();
        }

        /** 演一个动作。0 挥手 1 点头 2 小跳 3 蹲一下；外面（手机「换动作」）也走这里。 */
        void playAction(int k) {
            long now = System.currentTimeMillis();
            lastAct = k;
            if (k == ACT_WAVE) waveUntil = now + WAVE_MS;
            else if (k == ACT_NOD) nodUntil = now + 1400;
            else if (k == ACT_HOP) hopUntil = now + 900;
            else if (k == ACT_SQUAT) squatUntil = now + 1600;
            postInvalidate();
        }

        /** 站着待着的时候，每隔十几二十秒自己演一个动作，别一直像个静物。 */
        void idleActIfDue() {
            long now = System.currentTimeMillis();
            if (walking) { nextActAt = now + 8000; return; }
            if (nextActAt == 0) { nextActAt = now + 7000; return; }
            if (now < nextActAt) return;
            nextActAt = now + (long) ((13 + Math.random() * 13) * 1000);
            int hh = java.util.Calendar.getInstance().get(java.util.Calendar.HOUR_OF_DAY);
            if (vm != MODE_FULL) return;
            if (hh < 7 || hh > 22) return;
            int k = (int) (Math.random() * 4);
            if (k == lastAct) k = (k + 1) % 4;      // 别连着演同一个
            playAction(k);
        }

        // 打招呼：戳它一定应一声；平时二十来分钟自己冒一句（只白天，晚上别吵）
        void greet(boolean forced) {
            long now = System.currentTimeMillis();
            int hh = java.util.Calendar.getInstance().get(java.util.Calendar.HOUR_OF_DAY);
            if (!forced) {
                if (hh < 8 || hh > 21) return;
                if (now - lastGreet < 20L * 60 * 1000) return;
            }
            if (now - lastGreet < 40L * 1000) return;
            lastGreet = now;
            happyUntil = now + 6000;   // 打招呼这 6 秒换成笑脸
            waveUntil = now + WAVE_MS; // 同时抬手挥 4 秒多，配合“来啦”这句
            nodUntil = now + 1400;     // 先应声点两下头，再把手抬起来
            String line = greetLines[(int) (Math.random() * greetLines.length)];
            try {
                Toast t = Toast.makeText(getContext(), line, Toast.LENGTH_SHORT);
                t.setGravity(Gravity.TOP | Gravity.END, (int) dp(18), (int) dp(96));
                t.show();
            } catch (Exception e) { }
            postInvalidate();
        }
    }

    private void openApp() {
        try {
            Intent i = new Intent(this, DaoActivity.class);
            i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_SINGLE_TOP);
            startActivity(i);
        } catch (Exception e) { }
    }
}
