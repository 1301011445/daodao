package com.daodao.pet;

import android.app.Activity;
import android.content.Intent;
import android.os.Bundle;
import android.view.View;
import android.view.WindowManager;
import android.webkit.WebChromeClient;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;

public class DaoActivity extends Activity {

    private WebView web;
    private DaoBridge bridge;
    private String pendingAlarm = "";

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);

        web = new WebView(this);
        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setAllowFileAccess(true);
        s.setAllowContentAccess(true);
        // 2026-11-22：页面在 file:///android_asset 下，允许它自己去读 assets（曲库兜底用）
        try {
            s.setAllowFileAccessFromFileURLs(true);
            s.setAllowUniversalAccessFromFileURLs(true);
        } catch (Exception e) { }
        s.setMediaPlaybackRequiresUserGesture(false);
        s.setLoadWithOverviewMode(false);
        s.setUseWideViewPort(true);
        s.setSupportZoom(false);
        s.setBuiltInZoomControls(false);
        s.setCacheMode(WebSettings.LOAD_NO_CACHE);
        try {
            s.setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW);
        } catch (Exception e) { }

        web.setBackgroundColor(0xFF0B1022);
        web.setVerticalScrollBarEnabled(false);
        web.setHorizontalScrollBarEnabled(false);
        web.setOverScrollMode(View.OVER_SCROLL_NEVER);
        web.setWebChromeClient(new WebChromeClient());

        bridge = new DaoBridge(this, web);
        web.addJavascriptInterface(bridge, "DaoNative");
        bridge.rotateLauncherIcon();

        // 从闹钟通知点进来时，带到点的那条事项；页面加载完再交给它说一遍
        try {
            Intent in0 = getIntent();
            if (in0 != null) {
                String t0 = in0.getStringExtra(NoteAlarm.EXTRA_TEXT);
                if (t0 != null) pendingAlarm = t0;
            }
        } catch (Exception e) { }
        web.setWebViewClient(new WebViewClient() {
            @Override
            public void onPageFinished(WebView v, String url) {
                super.onPageFinished(v, url);
                if (pendingAlarm != null && pendingAlarm.length() > 0) {
                    String t = pendingAlarm;
                    pendingAlarm = "";
                    deliverAlarm(t);
                }
            }
        });
        // 启动就要一次麦克风：按住说话第一次点才弹框，用户常常以为没反应就松手了
        try {
            if (checkSelfPermission(android.Manifest.permission.RECORD_AUDIO)
                    != android.content.pm.PackageManager.PERMISSION_GRANTED) {
                requestPermissions(new String[]{android.Manifest.permission.RECORD_AUDIO}, 9002);
            }
        } catch (Exception e) { }

        web.loadUrl("file:///android_asset/dao.html");
        setContentView(web);
    }

    @Override
    protected void onResume() {
        super.onResume();
        try {
            // 2026-11-22：浮窗要知道「道」是不是在前台——在前台就自己躲起来，不挡页面
            android.content.SharedPreferences p = getSharedPreferences(DaoOverlay.SP, MODE_PRIVATE);
            p.edit().putInt("app", 1).apply();
            if (p.getBoolean("want", false) && DaoOverlay.canDraw(this)) {
                DaoOverlay.start(this, p.getInt("mode", DaoOverlay.MODE_PEEK));
            }
        } catch (Exception e) { }
    }

    @Override
    protected void onPause() {
        try {
            // 退回桌面 / 去别的应用，浮窗再出来
            getSharedPreferences(DaoOverlay.SP, MODE_PRIVATE).edit().putInt("app", 0).apply();
        } catch (Exception e) { }
        super.onPause();
    }

    @Override
    public void onBackPressed() {
        moveTaskToBack(true);
    }

    @Override
    protected void onNewIntent(Intent it) {
        super.onNewIntent(it);
        try {
            setIntent(it);
            String t = it == null ? null : it.getStringExtra(NoteAlarm.EXTRA_TEXT);
            if (t != null && t.length() > 0) {
                if (web != null) deliverAlarm(t);
                else pendingAlarm = t;
            }
        } catch (Exception e) { }
    }

    // 把到点事项交给页面：页面里的 __daoAlarm 会显示出来并念一遍
    private void deliverAlarm(final String text) {
        if (web == null) return;
        final String esc = text.replace("\\", "\\\\").replace("'", "\\'").replace("\n", " ");
        web.post(new Runnable() {
            @Override
            public void run() {
                try {
                    web.evaluateJavascript("(function(){try{if(window.__daoAlarm)window.__daoAlarm('" + esc + "');}catch(e){}})()", null);
                } catch (Exception e) { }
            }
        });
    }

    @Override
    public void onRequestPermissionsResult(int code, String[] perms, int[] res) {
        super.onRequestPermissionsResult(code, perms, res);
        if ((code == 9001 || code == 9002) && bridge != null) {
            if (res != null && res.length > 0 && res[0] == android.content.pm.PackageManager.PERMISSION_GRANTED) {
                bridge.startListenNow();
            } else {
                bridge.tellNoMic();
            }
        }
    }

    @Override
    protected void onDestroy() {
        if (web != null) {
            web.stopLoading();
            web.destroy();
            web = null;
        }
        super.onDestroy();
    }
}
