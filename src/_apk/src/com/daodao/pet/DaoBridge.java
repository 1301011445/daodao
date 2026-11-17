package com.daodao.pet;

import android.app.DownloadManager;
import android.content.Context;
import android.content.SharedPreferences;
import android.net.Uri;
import android.os.Environment;
import android.os.Handler;
import android.os.Looper;
import android.webkit.JavascriptInterface;
import android.webkit.WebView;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.DatagramPacket;
import java.net.DatagramSocket;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.ArrayList;
import java.util.List;

public class DaoBridge {

    private static final String API = "https://open.bigmodel.cn/api/paas/v4/chat/completions";
    private static final String KEY = "e753a789a9fe4821b46d6558346b6dd8.P5ASHghZ3RX0tPJ9";
    private static final String MODEL = "glm-4-flash";
    private static final String MODEL_ALT = "glm-4.7-flash";

    // 电脑端的局域网同步服务端口
    private static final int PC_PORT = 8848;
    private static final int UDP_PORT = 8849;

    // 公网版本来源：一个只有几十 KB 的版本清单，外加完整下载页做后备。
    // 有了这个，手机不用跟电脑连同一个 WiFi 也能查到新版。
    private static final String VER_PAGE =
        "https://4mf81m04wehh3.doubao.link/app/app_17hpue26uuw";
    private static final String PUB_PAGE =
        "https://4mf81m04wehh3.doubao.link/app/app_17hnj8acgs2";

    private final Context ctx;
    private final WebView web;
    private final Handler ui = new Handler(Looper.getMainLooper());
    private final SharedPreferences sp;

    public DaoBridge(Context c, WebView w) {
        this.ctx = c;
        this.web = w;
        this.sp = c.getSharedPreferences("daodao", Context.MODE_PRIVATE);
    }

    // 每天换一枚桌面图标：manifest 里 7 个 Launcher 别名各带一张图，只启用当天那一个
    public void rotateLauncherIcon() {
        try {
            int idx = java.util.Calendar.getInstance().get(java.util.Calendar.DAY_OF_YEAR) % 7;
            android.content.pm.PackageManager pm = ctx.getPackageManager();
            for (int i = 0; i < 7; i++) {
                android.content.ComponentName cn =
                        new android.content.ComponentName(ctx, "com.daodao.pet.Launcher" + i);
                int st = (i == idx)
                        ? android.content.pm.PackageManager.COMPONENT_ENABLED_STATE_ENABLED
                        : android.content.pm.PackageManager.COMPONENT_ENABLED_STATE_DISABLED;
                pm.setComponentEnabledSetting(cn, st,
                        android.content.pm.PackageManager.DONT_KILL_APP);
            }
        } catch (Exception e) { }
    }

    private static final String SYS_CHAT =
        "你是桌面小宠物「道」，一只会走路会蹦跳的小家伙，性格温和、好奇、爱说话。"
        + "你的主人是农村初中数学老师。回复要短，1到3句，不超过60个字，口语化，像朋友说话。"
        + "不要说教，不要用列表，不要堆表情符号，不要提自己是AI或助手。"
        + "输出必须严格是这一种格式：情绪|回复。情绪只能从这几个词里选一个：开心、生气、难过、惊讶、得意、疑惑、平静。"
        + "例如：开心|这道题你讲得真清楚，我记住了。";

    @JavascriptInterface
    public void chat(final String text, final String cbId) {
        final String q = (text == null) ? "" : text.trim();
        final String id = (cbId == null) ? "" : cbId;
        if (q.length() == 0) {
            postReply(id, "你想跟我说点什么？", 0);
            return;
        }
        new Thread(new Runnable() {
            public void run() {
                String out = requestChat(SYS_CHAT, q, 0.7, 130);
                if (out == null) {
                    postReply(id, "我这边网有点慢，刚没连上，等一下再跟我说一次吧。", 0);
                    return;
                }
                String mood = "平静";
                String body = out;
                int bar = out.indexOf('|');
                if (bar > 0 && bar <= 10) {
                    mood = out.substring(0, bar).trim();
                    body = out.substring(bar + 1).trim();
                }
                if (body.length() == 0) body = out;
                if (body.length() > 200) body = body.substring(0, 200);
                saveTurn(q, body);
                postReply(id, body, moodCode(mood));
            }
        }).start();
    }

    // 讲题 / 总结：同一套脑子，换个用法
    private static final String SYS_EXPLAIN =
        "你是初中数学老师身边的助教。用最朴实的话讲清这道题该往哪想，说一两步关键思路就行，"
        + "不要写成完整解题过程，不要列步骤，不要加「提示」「思路」这类前缀，直接从话里说，不超过一百字。";

    private static final String SYS_SUM =
        "把收到的内容用大白话总结，三句话以内，抓住重点，不要复述原句。";

    @JavascriptInterface
    public void explain(String text, String cbId) {
        doSide(text, cbId, SYS_EXPLAIN, 4);
    }

    @JavascriptInterface
    public void summarize(String text, String cbId) {
        doSide(text, cbId, SYS_SUM, 1);
    }

    private void doSide(final String text, final String cbId, final String sys, final int mood) {
        final String q = (text == null) ? "" : text.trim();
        final String id = (cbId == null) ? "" : cbId;
        if (q.length() == 0) {
            postReply(id, "把内容贴进来我再看看。", 0);
            return;
        }
        new Thread(new Runnable() {
            public void run() {
                String out = request(sys, q, 0.5, 500);
                if (out == null) {
                    postReply(id, "我这会儿没连上脑子，过一会儿再试。", 0);
                    return;
                }
                String body = out.trim();
                if (body.length() > 300) body = body.substring(0, 300);
                postReply(id, body, mood);
            }
        }).start();
    }

    // 页面左上角那个版本牌问的就是这里：读到安装包自己的 versionName
    @JavascriptInterface
    public String getVersion() {
        try {
            return ctx.getPackageManager().getPackageInfo(ctx.getPackageName(), 0).versionName;
        } catch (Exception e) {
            return "";
        }
    }

    // 页面收起输入条时顺手让原生把系统键盘也按下去
    @JavascriptInterface
    public void hideKeyboard() {
        ui.post(new Runnable() {
            public void run() {
                try {
                    android.view.inputmethod.InputMethodManager imm =
                        (android.view.inputmethod.InputMethodManager)
                        ctx.getSystemService(Context.INPUT_METHOD_SERVICE);
                    if (imm != null && web != null) imm.hideSoftInputFromWindow(web.getWindowToken(), 0);
                } catch (Exception e) {
                }
            }
        });
    }

    @JavascriptInterface
    public String getLines() {
        try {
            JSONArray arr = new JSONArray(sp.getString("extra_lines", "[]"));
            return arr.toString();
        } catch (Exception e) {
            return "[]";
        }
    }

    @JavascriptInterface
    public String getKnowledge() {
        try {
            JSONObject o = new JSONObject();
            o.put("today", sp.getString("today_learn", ""));
            o.put("count", sp.getInt("learn_count", 0));
            o.put("lines", new JSONArray(sp.getString("extra_lines", "[]")).length());
            o.put("recent", new JSONArray(sp.getString("learn_history", "[]")));
            o.put("last", sp.getLong("last_update", 0));
            return o.toString();
        } catch (Exception e) {
            return "{}";
        }
    }

    @JavascriptInterface
    public void autoUpdate() {
        long now = System.currentTimeMillis();
        long last = sp.getLong("last_update", 0);
        final boolean force = (sp.getInt("learn_count", 0) == 0);
        if (!force && now - last < 6L * 3600 * 1000) {
            return;
        }
        new Thread(new Runnable() {
            public void run() {
                boolean changed = false;

                String p1 = "给桌宠「道」写3条新的日常关心语，对象是农村初中数学老师。"
                    + "每条不超过22个字，要具体、口语、有生活味，别用套话。"
                    + "只输出3行，一行一条，不要编号，不要书名号，不要引号。";
                String r1 = request("你是文案助手，只输出要求的文本，不加解释。", p1, 0.9, 160);
                if (r1 != null) {
                    String[] ls = r1.split("\\n");
                    List<String> add = new ArrayList<String>();
                    for (int i = 0; i < ls.length && add.size() < 3; i++) {
                        String s = cleanLine(ls[i]);
                        if (s.length() >= 4 && s.length() <= 30) add.add(s);
                    }
                    if (!add.isEmpty()) {
                        JSONArray arr;
                        try {
                            arr = new JSONArray(sp.getString("extra_lines", "[]"));
                        } catch (Exception e) {
                            arr = new JSONArray();
                        }
                        int keep = arr.length() > 40 ? 40 : arr.length();
                        JSONArray neu = new JSONArray();
                        for (int i = 0; i < keep; i++) {
                            try { neu.put(arr.getString(i)); } catch (Exception e) { }
                        }
                        for (int i = 0; i < add.size(); i++) neu.put(add.get(i));
                        sp.edit().putString("extra_lines", neu.toString()).apply();
                        changed = true;
                    }
                }

                String p2 = "说一个今天值得知道的小知识，跟初中数学、教学、或者生活常识有关。"
                    + "一句话，不超过40个字，直接说内容，不要开头解释。";
                String r2 = request("你是知识助手，只输出一句话，不加解释。", p2, 0.8, 90);
                if (r2 != null) {
                    String s = cleanLine(r2);
                    if (s.length() >= 5) {
                        JSONArray hist;
                        try {
                            hist = new JSONArray(sp.getString("learn_history", "[]"));
                        } catch (Exception e) {
                            hist = new JSONArray();
                        }
                        JSONArray nh = new JSONArray();
                        int keep = hist.length() > 9 ? 9 : hist.length();
                        for (int i = 0; i < keep; i++) {
                            try { nh.put(hist.getString(i)); } catch (Exception e) { }
                        }
                        nh.put(s);
                        int cnt = sp.getInt("learn_count", 0) + 1;
                        sp.edit()
                          .putString("today_learn", s)
                          .putString("learn_history", nh.toString())
                          .putInt("learn_count", cnt)
                          .putLong("last_update", System.currentTimeMillis())
                          .apply();
                        changed = true;
                    }
                }

                if (!sp.contains("last_update") || changed) {
                    sp.edit().putLong("last_update", System.currentTimeMillis()).apply();
                }

                final boolean c = changed;
                ui.post(new Runnable() {
                    public void run() {
                        try {
                            web.evaluateJavascript(
                                "window.__daoUpdated && window.__daoUpdated(" + c + ");", null);
                        } catch (Exception e) { }
                    }
                });
            }
        }).start();
    }

    // ================= 电脑-手机互通 =================

    // 在局域网里找电脑：先试上次存的地址，不行就收电脑发的广播
    private String discover() {
        String saved = sp.getString("pc_addr", "");
        if (saved != null && saved.trim().length() > 0) {
            if (httpGet("http://" + saved.trim() + "/ping", 2500) != null) return saved.trim();
        }
        DatagramSocket ds = null;
        try {
            ds = new DatagramSocket(UDP_PORT);
            ds.setBroadcast(true);
            ds.setSoTimeout(8000);
            byte[] buf = new byte[256];
            DatagramPacket p = new DatagramPacket(buf, buf.length);
            ds.receive(p);
            String ip = p.getAddress().getHostAddress();
            int port = PC_PORT;
            try {
                String msg = new String(p.getData(), 0, p.getLength(), "UTF-8");
                String[] parts = msg.split("\\|");
                if (parts.length >= 3) port = Integer.parseInt(parts[2].trim());
            } catch (Exception e) { }
            String addr = ip + ":" + port;
            sp.edit().putString("pc_addr", addr).apply();
            return addr;
        } catch (Exception e) {
            return "";
        } finally {
            if (ds != null) { try { ds.close(); } catch (Exception e) { } }
        }
    }

    private int myVersionCode() {
        try {
            return ctx.getPackageManager()
                      .getPackageInfo(ctx.getPackageName(), 0).versionCode;
        } catch (Exception e) {
            return 0;
        }
    }

    // 一键同步：先拉电脑上的，再把手机上新增的推过去
    @JavascriptInterface
    public void syncNow(final String cbId) {
        final String id = (cbId == null) ? "" : cbId;
        new Thread(new Runnable() {
            public void run() {
                String addr = discover();
                if (addr.length() == 0) {
                    postSync(id, "no_pc", "没找到电脑。手机和电脑要连同一个 WiFi，电脑上的道得开着。");
                    return;
                }
                int gotL = 0, gotK = 0;
                String pulled = httpGet("http://" + addr + "/sync", 5000);
                if (pulled != null) {
                    List<String> ls = new ArrayList<String>();
                    List<String> ks = new ArrayList<String>();
                    String[] rows = pulled.replace("\r", "").split("\n");
                    for (int i = 0; i < rows.length; i++) {
                        String r = rows[i];
                        if (r.length() < 3 || r.charAt(1) != '|') continue;
                        char tag = r.charAt(0);
                        String val = r.substring(2).trim();
                        if (val.length() == 0 || val.startsWith("#")) continue;
                        if (tag == 'L') { if (val.length() <= 40) ls.add(val); }
                        else if (tag == 'K') { if (val.length() <= 90) ks.add(val); }
                    }
                    gotL = ls.size();
                    gotK = ks.size();
                    mergeLocalLines(ls);
                    mergeLocalKnowledge(ks);
                }

                // 把手机自己攒的推回电脑
                String push = buildPush();
                String pr = httpPost("http://" + addr + "/sync", push, 6000);

                String msg;
                if (pulled == null && pr == null) {
                    msg = "电脑没应答，可能防火墙挡着了。";
                } else {
                    msg = "跟电脑对上话了：拉过来 " + gotL + " 条话、" + gotK + " 条知识";
                    if (pr != null) msg = msg + "，推上去 " + push.length() + " 字节";
                }
                postSync(id, "ok", msg);
            }
        }).start();
    }

    // 手机端自检结果：先存本地，能找到电脑就推过去，电脑汇总进同一张待改清单
    @JavascriptInterface
    public void selfCheck(final String report) {
        final String r = (report == null) ? "" : report;
        new Thread(new Runnable() {
            public void run() {
                try {
                    sp.edit().putString("selfcheck_last", r)
                      .putLong("selfcheck_time", System.currentTimeMillis()).apply();
                } catch (Exception e) { }
                String addr = discover();
                if (addr.length() == 0) return;
                httpPost("http://" + addr + "/selfcheck", r, 5000);
            }
        }).start();
    }

    // 愉悦值：跟电脑要同一个数，两端不各存一份（不在这里自己算，避免两边吵架）
    @JavascriptInterface
    public String getJoy() {
        try {
            String addr = sp.getString("pc_addr", "");
            if (addr == null || addr.length() == 0) return "";
            String r = httpGet("http://" + addr + "/joy", 4000);
            if (r == null) return "";
            return r.trim();
        } catch (Exception e) { return ""; }
    }

    @JavascriptInterface
    public String getSelfCheck() {
        try { return sp.getString("selfcheck_last", ""); } catch (Exception e) { return ""; }
    }

    // 检查有没有新版本。
    // 先走公网：手机在什么地方都能查，不用跟电脑连同一个 WiFi，也不用电脑开着。
    // 公网查不到再退回局域网问电脑。
    @JavascriptInterface
    public void checkUpdate(final String cbId) {
        final String id = (cbId == null) ? "" : cbId;
        new Thread(new Runnable() {
            public void run() {
                String page = httpGet(VER_PAGE, 12000);
                if (page == null || page.length() < 200) page = httpGet(PUB_PAGE, 20000);

                int remote = -1;
                String apkUrl = null;
                if (page != null) {
                    java.util.regex.Matcher mv =
                        java.util.regex.Pattern.compile("data-ver=\"(\\d+)\"").matcher(page);
                    if (mv.find()) {
                        try { remote = Integer.parseInt(mv.group(1)); } catch (Exception e) { }
                    }
                    java.util.regex.Matcher ma =
                        java.util.regex.Pattern.compile("data-apk=\"([^\"]+)\"").matcher(page);
                    if (ma.find()) apkUrl = ma.group(1);
                }

                if (remote > 0 && apkUrl != null) {
                    if (remote <= myVersionCode()) {
                        postSync(id, "latest", "已经是最新版了（v" + myVersionCode() + "）");
                        return;
                    }
                    boolean ok = downloadApk(apkUrl, remote);
                    if (ok) postSync(id, "update", "网上有新版 v" + remote + "，正在下载，下完点通知就能装。");
                    else postSync(id, "err", "新版本下载没起来，可以到下载页手动装。");
                    return;
                }

                // 公网不通，问电脑
                String addr = discover();
                if (addr.length() == 0) {
                    postSync(id, "no_pc", "没连上外网，也没找到电脑，暂时查不了新版本。");
                    return;
                }
                String v = httpGet("http://" + addr + "/ver", 4000);
                int local = -1;
                if (v != null) {
                    String t = v.trim();
                    if (t.startsWith("VER|")) {
                        try { local = Integer.parseInt(t.substring(4).trim()); } catch (Exception e) { }
                    }
                }
                if (local <= 0) {
                    postSync(id, "err", "电脑没报版本号。");
                    return;
                }
                if (local <= myVersionCode()) {
                    postSync(id, "latest", "已经是最新版了（v" + myVersionCode() + "）");
                    return;
                }
                boolean ok = downloadNewApk(addr);
                if (ok) postSync(id, "update", "电脑上有新版 v" + local + "，已经在下载，下完点通知安装");
                else postSync(id, "err", "下载没起来，可能系统不给权限。");
            }
        }).start();
    }

    // 从公网地址下载新版 apk，交给系统下载器，文件名自己定，不会被改
    private boolean downloadApk(String url, int ver) {
        try {
            DownloadManager dm = (DownloadManager) ctx.getSystemService(Context.DOWNLOAD_SERVICE);
            if (dm == null) return false;
            DownloadManager.Request r = new DownloadManager.Request(Uri.parse(url));
            r.setTitle("道 新版本 v" + ver);
            r.setDescription("下载完点一下通知就能装");
            r.setMimeType("application/vnd.android.package-archive");
            r.setNotificationVisibility(
                DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED);
            r.setDestinationInExternalPublicDir(
                Environment.DIRECTORY_DOWNLOADS, "道-v" + ver + ".apk");
            r.setAllowedOverMetered(true);
            dm.enqueue(r);
            return true;
        } catch (Exception e) {
            return false;
        }
    }

    private boolean downloadNewApk(String addr) {
        try {
            DownloadManager dm = (DownloadManager) ctx.getSystemService(Context.DOWNLOAD_SERVICE);
            if (dm == null) return false;
            DownloadManager.Request r =
                new DownloadManager.Request(Uri.parse("http://" + addr + "/apk"));
            r.setTitle("道 新版本");
            r.setDescription("下载完点一下就能装");
            r.setMimeType("application/vnd.android.package-archive");
            r.setNotificationVisibility(
                DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED);
            r.setDestinationInExternalPublicDir(Environment.DIRECTORY_DOWNLOADS, "道-新版本.apk");
            r.setAllowedOverMetered(true);
            dm.enqueue(r);
            return true;
        } catch (Exception e) {
            return false;
        }
    }

    // 把电脑的话术并进手机本地
    private void mergeLocalLines(List<String> add) {
        if (add.isEmpty()) return;
        JSONArray arr;
        try { arr = new JSONArray(sp.getString("extra_lines", "[]")); }
        catch (Exception e) { arr = new JSONArray(); }
        java.util.HashSet<String> have = new java.util.HashSet<String>();
        List<String> all = new ArrayList<String>();
        for (int i = 0; i < arr.length(); i++) {
            try {
                String s = arr.getString(i);
                if (have.add(s)) all.add(s);
            } catch (Exception e) { }
        }
        for (int i = 0; i < add.size(); i++) {
            String s = add.get(i);
            if (have.add(s)) all.add(s);
        }
        while (all.size() > 60) all.remove(0);
        JSONArray neu = new JSONArray();
        for (int i = 0; i < all.size(); i++) neu.put(all.get(i));
        sp.edit().putString("extra_lines", neu.toString()).apply();
    }

    // 把电脑的知识并进手机本地
    private void mergeLocalKnowledge(List<String> add) {
        if (add.isEmpty()) return;
        JSONArray hist;
        try { hist = new JSONArray(sp.getString("learn_history", "[]")); }
        catch (Exception e) { hist = new JSONArray(); }
        java.util.HashSet<String> have = new java.util.HashSet<String>();
        List<String> all = new ArrayList<String>();
        for (int i = 0; i < hist.length(); i++) {
            try {
                String s = hist.getString(i);
                if (have.add(s)) all.add(s);
            } catch (Exception e) { }
        }
        for (int i = 0; i < add.size(); i++) {
            String s = add.get(i);
            if (have.add(s)) all.add(s);
        }
        while (all.size() > 20) all.remove(0);
        JSONArray nh = new JSONArray();
        for (int i = 0; i < all.size(); i++) nh.put(all.get(i));
        int cnt = sp.getInt("learn_count", 0) + add.size();
        sp.edit()
          .putString("learn_history", nh.toString())
          .putInt("learn_count", cnt)
          .putString("today_learn", add.get(add.size() - 1))
          .apply();
    }

    // 拼出手机这边的数据，推给电脑
    private String buildPush() {
        StringBuilder sb = new StringBuilder();
        try {
            JSONArray arr = new JSONArray(sp.getString("extra_lines", "[]"));
            for (int i = 0; i < arr.length(); i++) {
                String s = arr.getString(i).trim();
                if (s.length() > 0 && s.length() <= 40) sb.append("L|").append(s).append("\n");
            }
        } catch (Exception e) { }
        try {
            JSONArray h = new JSONArray(sp.getString("learn_history", "[]"));
            for (int i = 0; i < h.length(); i++) {
                String s = h.getString(i).trim();
                if (s.length() > 0 && s.length() <= 90) sb.append("K|").append(s).append("\n");
            }
        } catch (Exception e) { }
        return sb.toString();
    }

    private void postSync(final String id, final String status, final String msg) {
        ui.post(new Runnable() {
            public void run() {
                try {
                    String js = "window.__daoMsg && window.__daoMsg("
                        + JSONObject.quote(id) + "," + JSONObject.quote(status)
                        + "," + JSONObject.quote(msg) + ");";
                    web.evaluateJavascript(js, null);
                } catch (Exception e) { }
            }
        });
    }

    private String httpGet(String url, int timeoutMs) {
        HttpURLConnection c = null;
        try {
            c = (HttpURLConnection) new URL(url).openConnection();
            c.setConnectTimeout(timeoutMs);
            c.setReadTimeout(timeoutMs);
            c.setRequestMethod("GET");
            int code = c.getResponseCode();
            if (code != 200) return null;
            InputStream is = c.getInputStream();
            BufferedReader br = new BufferedReader(new InputStreamReader(is, "UTF-8"));
            StringBuilder sb = new StringBuilder();
            String line;
            while ((line = br.readLine()) != null) sb.append(line).append("\n");
            br.close();
            is.close();
            return sb.toString();
        } catch (Exception e) {
            return null;
        } finally {
            if (c != null) { try { c.disconnect(); } catch (Exception e) { } }
        }
    }

    private String httpPost(String url, String body, int timeoutMs) {
        HttpURLConnection c = null;
        try {
            c = (HttpURLConnection) new URL(url).openConnection();
            c.setConnectTimeout(timeoutMs);
            c.setReadTimeout(timeoutMs);
            c.setRequestMethod("POST");
            c.setDoOutput(true);
            c.setRequestProperty("Content-Type", "text/plain; charset=utf-8");
            OutputStream os = c.getOutputStream();
            os.write(body.getBytes("UTF-8"));
            os.flush();
            os.close();
            int code = c.getResponseCode();
            if (code != 200) return null;
            InputStream is = c.getInputStream();
            BufferedReader br = new BufferedReader(new InputStreamReader(is, "UTF-8"));
            StringBuilder sb = new StringBuilder();
            String line;
            while ((line = br.readLine()) != null) sb.append(line).append("\n");
            br.close();
            is.close();
            return sb.toString();
        } catch (Exception e) {
            return null;
        } finally {
            if (c != null) { try { c.disconnect(); } catch (Exception e) { } }
        }
    }

    private void postReply(final String id, final String reply, final int mood) {
        ui.post(new Runnable() {
            public void run() {
                try {
                    String js = "window.__daoReply && window.__daoReply("
                        + JSONObject.quote(id) + "," + JSONObject.quote(reply) + "," + mood + ");";
                    web.evaluateJavascript(js, null);
                } catch (Exception e) { }
            }
        });
    }

    private static int moodCode(String word) {
        if (word == null) return 0;
        if (word.indexOf("开心") >= 0) return 1;
        if (word.indexOf("生气") >= 0) return 2;
        if (word.indexOf("难过") >= 0) return 3;
        if (word.indexOf("惊讶") >= 0) return 4;
        if (word.indexOf("疑惑") >= 0) return 4;
        if (word.indexOf("得意") >= 0) return 1;
        return 0;
    }

    private static String cleanLine(String s) {
        if (s == null) return "";
        String t = s.trim();
        while (t.startsWith("-") || t.startsWith("*") || t.startsWith("·")
               || t.startsWith("「") || t.startsWith("\"") || t.startsWith("1")
               || t.startsWith("2") || t.startsWith("3")) {
            if (t.startsWith("「")) { t = t.substring(1); break; }
            if (t.length() > 1 && (t.charAt(1) == '.' || t.charAt(1) == '、' || t.charAt(1) == '）')) {
                t = t.substring(2).trim();
            } else {
                t = t.substring(1).trim();
            }
            if (t.length() == 0) return "";
        }
        if (t.endsWith("」")) t = t.substring(0, t.length() - 1);
        if (t.endsWith("\"")) t = t.substring(0, t.length() - 1);
        return t.trim();
    }

    private String requestChat(String sys, String user, double temp, int maxTok) {
        String r = once(MODEL, buildMsgs(sys, user, true), temp, maxTok);
        if (r == null) {
            try { Thread.sleep(1200); } catch (InterruptedException e) { }
            r = once(MODEL_ALT, buildMsgs(sys, user, true), temp, maxTok);
        }
        return r;
    }

    // 带上最近几轮聊过的内容，才接得上话
    private JSONArray buildMsgs(String sys, String user, boolean withHistory) {
        JSONArray msgs = new JSONArray();
        try {
            msgs.put(new JSONObject().put("role", "system").put("content", sys));
            if (withHistory) {
                JSONArray h = loadHistory();
                int start = Math.max(0, h.length() - 6);
                for (int i = start; i < h.length(); i++) {
                    JSONObject t = h.getJSONObject(i);
                    String u = t.optString("u", "").trim();
                    String a = t.optString("a", "").trim();
                    if (u.length() > 0 && a.length() > 0) {
                        msgs.put(new JSONObject().put("role", "user").put("content", u));
                        msgs.put(new JSONObject().put("role", "assistant").put("content", a));
                    }
                }
            }
            msgs.put(new JSONObject().put("role", "user").put("content", user));
        } catch (Exception e) { }
        return msgs;
    }

    private JSONArray loadHistory() {
        try { return new JSONArray(sp.getString("chat_history", "[]")); }
        catch (Exception e) { return new JSONArray(); }
    }

    private void saveTurn(String u, String a) {
        try {
            if (u == null || u.length() == 0 || a == null || a.length() == 0) return;
            JSONArray arr = loadHistory();
            arr.put(new JSONObject().put("u", u).put("a", a));
            while (arr.length() > 20) arr.remove(0);
            sp.edit().putString("chat_history", arr.toString()).apply();
        } catch (Exception e) { }
    }

    private String request(String sys, String user, double temp, int maxTok) {
        String r = once(MODEL, sys, user, temp, maxTok);
        if (r == null) {
            try { Thread.sleep(1200); } catch (InterruptedException e) { }
            r = once(MODEL_ALT, sys, user, temp, maxTok);
        }
        return r;
    }

    private String once(String model, String sys, String user, double temp, int maxTok) {
        return once(model, buildMsgs(sys, user, false), temp, maxTok);
    }

    private String once(String model, JSONArray msgs, double temp, int maxTok) {
        HttpURLConnection conn = null;
        try {
            JSONObject body = new JSONObject();
            body.put("model", model);
            body.put("temperature", temp);
            body.put("max_tokens", maxTok);
            body.put("messages", msgs);

            URL u = new URL(API);
            conn = (HttpURLConnection) u.openConnection();
            conn.setRequestMethod("POST");
            conn.setConnectTimeout(15000);
            conn.setReadTimeout(45000);
            conn.setDoOutput(true);
            conn.setRequestProperty("Content-Type", "application/json");
            conn.setRequestProperty("Authorization", "Bearer " + KEY);

            OutputStream os = conn.getOutputStream();
            os.write(body.toString().getBytes("UTF-8"));
            os.flush();
            os.close();

            int code = conn.getResponseCode();
            if (code != 200) return null;

            InputStream is = conn.getInputStream();
            BufferedReader br = new BufferedReader(new InputStreamReader(is, "UTF-8"));
            StringBuilder sb = new StringBuilder();
            String line;
            while ((line = br.readLine()) != null) sb.append(line);
            br.close();
            is.close();

            JSONObject resp = new JSONObject(sb.toString());
            JSONArray choices = resp.getJSONArray("choices");
            if (choices.length() == 0) return null;
            JSONObject c0 = choices.getJSONObject(0);
            JSONObject msg = c0.getJSONObject("message");
            String content = msg.getString("content");
            if (content == null) return null;
            return content.trim();
        } catch (Exception e) {
            return null;
        } finally {
            if (conn != null) { try { conn.disconnect(); } catch (Exception e) { } }
        }
    }
}
