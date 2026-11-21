package com.daodao.pet;

import android.app.AlarmManager;
import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.os.Build;

/**
 * 手机端本地闹钟：记事本登记后，即使电脑关着、道没在跑，手机自己也会到点弹通知并响一声。
 * 走 AlarmManager + BroadcastReceiver，不依赖后台常驻进程。
 */
public class NoteAlarm {

    public static final String CH = "dao_note";
    public static final String EXTRA_TEXT = "note_text";
    public static final String EXTRA_ID = "note_id";

    static void ensureChannel(Context c) {
        try {
            if (Build.VERSION.SDK_INT < 26) return;
            NotificationManager nm = (NotificationManager) c.getSystemService(Context.NOTIFICATION_SERVICE);
            if (nm == null) return;
            if (nm.getNotificationChannel(CH) != null) return;
            NotificationChannel ch = new NotificationChannel(CH, "道的提醒", NotificationManager.IMPORTANCE_HIGH);
            ch.setDescription("记事本到点提醒");
            ch.enableVibration(true);
            ch.setShowBadge(true);
            nm.createNotificationChannel(ch);
        } catch (Exception e) { }
    }

    static PendingIntent pending(Context c, int id, String text) {
        Intent i = new Intent(c, NoteReceiver.class);
        i.setAction("com.daodao.pet.NOTE_TICK");
        i.putExtra(EXTRA_ID, id);
        i.putExtra(EXTRA_TEXT, text == null ? "" : text);
        int flags = PendingIntent.FLAG_UPDATE_CURRENT;
        if (Build.VERSION.SDK_INT >= 23) flags |= PendingIntent.FLAG_IMMUTABLE;
        return PendingIntent.getBroadcast(c, id, i, flags);
    }

    public static void schedule(Context c, int id, long whenMillis, String text) {
        try {
            ensureChannel(c);
            AlarmManager am = (AlarmManager) c.getSystemService(Context.ALARM_SERVICE);
            if (am == null) return;
            long now = System.currentTimeMillis();
            if (whenMillis <= now) whenMillis = now + 60L * 1000L;
            PendingIntent pi = pending(c, id, text);
            try {
                if (Build.VERSION.SDK_INT >= 23) am.setExactAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, whenMillis, pi);
                else if (Build.VERSION.SDK_INT >= 21) am.setExact(AlarmManager.RTC_WAKEUP, whenMillis, pi);
                else am.set(AlarmManager.RTC_WAKEUP, whenMillis, pi);
            } catch (SecurityException se) {
                // 系统没给「精确闹钟」权限时退一步，可能晚几分钟但一定响
                am.set(AlarmManager.RTC_WAKEUP, whenMillis, pi);
            }
        } catch (Exception e) { }
    }

    public static void cancel(Context c, int id) {
        try {
            AlarmManager am = (AlarmManager) c.getSystemService(Context.ALARM_SERVICE);
            if (am != null) am.cancel(pending(c, id, ""));
        } catch (Exception e) { }
    }

    public static boolean canNotify(Context c) {
        try {
            if (Build.VERSION.SDK_INT < 33) return true;
            return c.checkSelfPermission("android.permission.POST_NOTIFICATIONS") == PackageManager.PERMISSION_GRANTED;
        } catch (Exception e) { return true; }
    }

    public static void askPermission(Context c) {
        try {
            if (Build.VERSION.SDK_INT >= 33 && c instanceof android.app.Activity && !canNotify(c)) {
                ((android.app.Activity) c).requestPermissions(new String[] { "android.permission.POST_NOTIFICATIONS" }, 77);
            }
        } catch (Exception e) { }
    }

    public static boolean canExact(Context c) {
        try {
            if (Build.VERSION.SDK_INT < 31) return true;
            AlarmManager am = (AlarmManager) c.getSystemService(Context.ALARM_SERVICE);
            return am == null || am.canScheduleExactAlarms();
        } catch (Exception e) { return true; }
    }

    public static boolean openExactSettings(Context c) {
        try {
            if (Build.VERSION.SDK_INT < 31) return false;
            Intent i = new Intent(android.provider.Settings.ACTION_REQUEST_SCHEDULE_EXACT_ALARM);
            i.setData(android.net.Uri.parse("package:" + c.getPackageName()));
            i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
            c.startActivity(i);
            return true;
        } catch (Exception e) { return false; }
    }

    /** 闹钟响的时候由系统调用 */
    public static class NoteReceiver extends BroadcastReceiver {
        @Override
        public void onReceive(Context c, Intent i) {
            try {
                ensureChannel(c);
                String text = i == null ? "" : i.getStringExtra(EXTRA_TEXT);
                if (text == null || text.length() == 0) text = "到点了";
                int id = i == null ? 0 : i.getIntExtra(EXTRA_ID, 0);
                NotificationManager nm = (NotificationManager) c.getSystemService(Context.NOTIFICATION_SERVICE);
                if (nm == null) return;
                Notification.Builder b;
                if (Build.VERSION.SDK_INT >= 26) b = new Notification.Builder(c, CH);
                else b = new Notification.Builder(c);
                b.setSmallIcon(android.R.drawable.ic_popup_reminder);
                b.setContentTitle("道的提醒");
                b.setContentText(text);
                b.setStyle(new Notification.BigTextStyle().bigText(text));
                b.setAutoCancel(true);
                b.setDefaults(Notification.DEFAULT_ALL);
                if (Build.VERSION.SDK_INT >= 21) b.setPriority(Notification.PRIORITY_HIGH);
                Intent open = new Intent(c, DaoActivity.class);
                open.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_SINGLE_TOP);
                open.putExtra(EXTRA_TEXT, text);
                open.putExtra(EXTRA_ID, id);
                int flags = PendingIntent.FLAG_UPDATE_CURRENT;
                if (Build.VERSION.SDK_INT >= 23) flags |= PendingIntent.FLAG_IMMUTABLE;
                b.setContentIntent(PendingIntent.getActivity(c, id, open, flags));
                nm.notify(1000 + id, b.build());
            } catch (Exception e) { }
        }
    }
}
