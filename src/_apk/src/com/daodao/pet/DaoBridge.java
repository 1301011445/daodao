package com.daodao.pet;

import android.app.DownloadManager;
import java.util.Locale;
import android.speech.tts.TextToSpeech;
import android.speech.SpeechRecognizer;
import android.speech.RecognizerIntent;
import android.os.Bundle;
import android.content.pm.PackageManager;
import android.content.Intent;
import android.app.Activity;
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
    private static final String MODEL = "glm-4-flash";
    private static final String MODEL_ALT = "glm-4.7-flash";

    // 密钥不再写死在代码里（仓库是公开的）。优先用本机设置里填的，其次读打包时注入的
    // assets/glm_key.txt；两处都没有就返回空串，调用方按“未配置”处理，不发请求。
    private String _key;
    private String key() {
        if (_key != null) return _key;
        String k = sp.getString("glm_key", "");
        if (k == null) k = "";
        k = k.trim();
        if (k.isEmpty()) {
            java.io.InputStream in = null;
            try {
                in = ctx.getAssets().open("glm_key.txt");
                java.io.ByteArrayOutputStream bo = new java.io.ByteArrayOutputStream();
                byte[] b = new byte[4096];
                int n;
                while ((n = in.read(b)) > 0) bo.write(b, 0, n);
                k = bo.toString("UTF-8").trim();
            } catch (Exception e) {
                k = "";
            } finally {
                try { if (in != null) in.close(); } catch (Exception e) {}
            }
        }
        _key = k;
        return k;
    }
    public boolean hasKey() { return !key().isEmpty(); }
    public void setGlmKey(String k) {
        sp.edit().putString("glm_key", k == null ? "" : k.trim()).apply();
        _key = null;
    }

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

    // ==== 说话与听（2026-11-20 补）====
    // 说话走系统 TTS（离线、免流量）；听走系统语音识别（需 RECORD_AUDIO）。
    // 两边都用 evaluateJavascript 回给页面：window.__daoVoice(id, 文本)
    private TextToSpeech tts;
    private SpeechRecognizer sr;
    private String voiceCb = "";

    private void initTts() {
        if (tts != null) return;
        try {
            tts = new TextToSpeech(ctx, new TextToSpeech.OnInitListener() {
                public void onInit(int status) {
                    try { if (status == TextToSpeech.SUCCESS) tts.setLanguage(Locale.CHINA); } catch (Exception e) { }
                }
            });
        } catch (Exception e) { }
    }

    @JavascriptInterface
    public void speak(final String text) {
        final String t = (text == null) ? "" : text.trim();
        if (t.length() == 0) return;
        initTts();
        stopAudio();
        ui.post(new Runnable() {
            public void run() {
                try {
                    if (tts == null) return;
                    tts.setSpeechRate(0.95f);
                    tts.speak(t, TextToSpeech.QUEUE_FLUSH, null, "dao" + System.currentTimeMillis());
                } catch (Exception e) { }
            }
        });
    }

    // 三条出声通道（系统 TTS / MediaPlayer / 网页 WebAudio）必须互斥：
    // 不说话时叠着放，就是「对话时会冒出别的声音」
    private void stopAudio() {
        stopSong();
        try { cancelSay(); } catch (Exception e) { }
        try { if (tts != null) tts.stop(); } catch (Exception e) { }
        try { if (mp != null) { mp.stop(); mp.release(); mp = null; } } catch (Exception e) { try { if (mp != null) mp.release(); } catch (Exception e2) { } mp = null; }
    }

    @JavascriptInterface
    public void stopAll() { stopAudio(); }

    // ==== 记事本：手机本地闹钟（电脑关机也能提醒）====
    @JavascriptInterface
    public void noteAlarm(final int id, final long whenMillis, final String text) {
        try { NoteAlarm.schedule(ctx, id, whenMillis, text); } catch (Exception e) { }
    }

    @JavascriptInterface
    public void noteCancel(final int id) {
        try { NoteAlarm.cancel(ctx, id); } catch (Exception e) { }
    }

    @JavascriptInterface
    public boolean noteCanNotify() {
        try { return NoteAlarm.canNotify(ctx); } catch (Exception e) { return true; }
    }

    @JavascriptInterface
    public void noteAskPermission() {
        try { NoteAlarm.askPermission(ctx); } catch (Exception e) { }
    }

    // 精确闹钟：Android 12 起要单独授权，没开的话提醒可能晚几分钟
    @JavascriptInterface
    public boolean noteAlarmOk() {
        try { return NoteAlarm.canExact(ctx); } catch (Exception e) { return true; }
    }

    @JavascriptInterface
    public boolean noteOpenAlarmSetting() {
        try { return NoteAlarm.openExactSettings(ctx); } catch (Exception e) { return false; }
    }

    @JavascriptInterface
    public void stopSpeak() { try { if (tts != null) tts.stop(); } catch (Exception e) { } }

    // ==== 本地曲库（2026-11-20 晚）：改成原生解码 + MediaPlayer ====
    // 原来页面用 assetB64 把整首 2MB 曲子拉进 JS 再自己解，真机上出现过「拿不到曲库文件」，
    // 而且 4M 采样在 JS 里解要一两秒。这里直接读 assets、解 ADPCM、写 wav 缓存，再交给 MediaPlayer。
    private String songName = "";
    // 2026-11-22 晚：MediaPlayer 那条路（写 11MB wav 再 prepare）整条删掉了，只留 AudioTrack 直推 PCM
    private android.media.AudioTrack songTrack;
    private android.media.MediaPlayer songMp;      // 演唱版 m4a/mp3 走这条：原生解码，音质和进度都准
    private volatile double songStartSec = 0;      // 快进/续播用：从第几秒开始
    private Thread songTrackThread;
    private volatile boolean songStop = false;
    // 代次：连点两首时，前一首的后台线程不许再建 track，否则会把新歌的 songTrack 盖掉
    private volatile int songGen = 0;
    // 2026-11-22 晚（第二轮）：进度与诊断，页面靠这几个值判断「到底出没出声」
    private volatile int songSr = 22050;
    private volatile long songSamples = 0;      // 已成功写进 AudioTrack 的采样数
    private volatile long songFramesTotal = 0;
    private volatile int songPeak = 0;          // 解出来的最大幅值（0 = 全是静音，说明数据就有问题）
    private volatile int songUnder = 0;         // underrun 次数（>0 说明喂得太慢，会断续）
    private volatile String songErr = "";

    @JavascriptInterface
    public void stopSong() {
        songStop = true;
        android.media.MediaPlayer m = songMp;
        songMp = null;
        if (m != null) {
            try { m.stop(); } catch (Exception e) { }
            try { m.release(); } catch (Exception e) { }
        }
        android.media.AudioTrack t = songTrack;
        songTrack = null;
        if (t != null) {
            try { t.pause(); } catch (Exception e) { }
            try { t.flush(); } catch (Exception e) { }
            try { t.release(); } catch (Exception e) { }
        }
        songTrackThread = null;
        songName = "";
    }

    @JavascriptInterface
    public String nowSong() { return songName; }

    // 2026-11-22 晚（第二轮）：用户截图报「播放失败没声音，还按不了，退不出来」。查到三处硬伤：
    // ① decodePcm 一次解出 11MB short[] 才开播，低内存机直接 OOM，页面只看到「播放中」；
    // ② 失败后页面走 assetB64 / assetXhr——8MB base64 同步过桥，JS 线程被堵死，× 和歌单行都点不动；
    // ③ 开播就把行标成「♪ 播放中」，其实只是起了个线程，成没成一个字不回报。
    // 这一版：边解边写（每帧 2048 采样，内存几百 KB）、先起 track 再回 OK、进度用 songPos() 让页面轮询，
    // 出错一律带代码（NOFILE/HEADER/TRACK/WRITE/CATCH），不再静默。
    @JavascriptInterface
    public String playSongAsset(final String name) {
        if (name == null || name.length() == 0) return "ERR|NONAME 没给歌名";
        // 2026-11-22 夜：包里带了演唱版（m4a/mp3）就用原生解码器放——比 4-bit ADPCM 干净，进度也能精确 seek
        String mA = "music/" + name + ".m4a";
        if (!assetExists(mA)) mA = "music/" + name + ".mp3";
        if (assetExists(mA)) return playMediaAsset(name, mA);
        stopSong();
        songStop = false;
        songName = name;
        songErr = "";
        songSamples = 0;
        songPeak = 0;
        songUnder = 0;
        songFramesTotal = 0;
        final String nm = name;
        final int gen = ++songGen;
        songTrackThread = new Thread(new Runnable() {
            public void run() {
                String evt = "";
                android.media.AudioTrack t = null;
                try {
                    byte[] raw = readAsset("music/" + nm + ".adp");
                    if (raw == null || raw.length < 16) { songEvt("ERR|NOFILE 包里没有这首：" + nm); return; }
                    if (!(raw[0] == 'D' && raw[1] == 'A' && raw[2] == 'O' && raw[3] == '1')) { songEvt("ERR|HEADER 包头不是 DAO1"); return; }
                    int sr = (raw[4] & 0xff) | ((raw[5] & 0xff) << 8) | ((raw[6] & 0xff) << 16) | ((raw[7] & 0xff) << 24);
                    int frames = (raw[8] & 0xff) | ((raw[9] & 0xff) << 8) | ((raw[10] & 0xff) << 16) | ((raw[11] & 0xff) << 24);
                    if (sr <= 0) sr = 22050;
                    songSr = sr;
                    songFramesTotal = frames;
                    if (frames <= 0) { songEvt("ERR|HEADER 帧数=" + frames); return; }
                    t = makeTrack(sr);
                    songTrack = t;
                    try { t.play(); } catch (Exception e) { songEvt("ERR|TRACK play 抛了：" + e.getMessage()); return; }
                    if (t.getPlayState() != android.media.AudioTrack.PLAYSTATE_PLAYING) {
                        songEvt("ERR|TRACK 建好了但没起来 state=" + t.getPlayState());
                        return;
                    }
                    long secs = ((long) frames * 2048L) / sr;
                    songEvt("OK|" + secs + "|" + sr + "|" + nm);
                    short[] chunk = new short[2048];
                    double from = songStartSec;
                    songStartSec = 0;
                    int skipF = from > 0.5 ? (int) ((from * (double) sr) / 2048.0) : 0;
                    if (skipF < 0) skipF = 0;
                    if (skipF > frames - 1) skipF = frames - 1;
                    int pos = 12 + skipF * 1028, f = skipF, zero = 0;
                    songSamples = (long) skipF * 2048;
                    for (; f < frames; f++) {
                        if (songStop || gen != songGen) { evt = "STOP|" + nm; break; }
                        int end = Math.min(pos + 1028, raw.length);
                        if (end <= pos + 4) break;
                        int cnt = decodeFrame(raw, pos, end, chunk);
                        pos += 1028;
                        if (cnt <= 0) continue;
                        for (int q = 0; q < cnt; q++) { int a = chunk[q] < 0 ? -chunk[q] : chunk[q]; if (a > songPeak) songPeak = a; }
                        int i0 = 0;
                        while (i0 < cnt) {
                            if (songStop || gen != songGen) break;
                            int w = writeChunk(t, chunk, i0, cnt - i0);
                            if (w <= 0) {
                                if (w < 0) { evt = "ERR|WRITE 写入失败 code=" + w; break; }
                                zero++;
                                if (zero > 300) { evt = "ERR|WRITE 一直写不进去"; break; }
                                try { Thread.sleep(5); } catch (Exception e) { break; }
                                continue;
                            }
                            zero = 0;
                            i0 += w;
                            songSamples += w;
                        }
                        if (evt.length() > 0) break;
                        if ((f % 200) == 0 && android.os.Build.VERSION.SDK_INT >= 24) {
                            try { songUnder = t.getUnderrunCount(); } catch (Exception e) { }
                        }
                    }
                } catch (Throwable e) {
                    songErr = e.getClass().getSimpleName() + " " + (e.getMessage() == null ? "" : e.getMessage());
                    evt = "ERR|CATCH " + songErr;
                } finally {
                    android.media.AudioTrack tt = songTrack;
                    songTrack = null;
                    if (tt != null) {
                        if (evt.length() == 0) { try { Thread.sleep(250); } catch (Exception e) { } }
                        try { tt.stop(); } catch (Exception e) { }
                        try { tt.release(); } catch (Exception e) { }
                    }
                }
                if (evt.length() == 0) evt = "DONE|" + nm;
                if (evt.indexOf("ERR") == 0) songErr = evt;
                songEvt(evt);
            }
        });
        songTrackThread.start();
        return "START|" + name;
    }

    private void songEvt(String evt) {
        final String js = "window.__daoSong && window.__daoSong(" + org.json.JSONObject.quote(evt) + ");";
        ui.post(new Runnable() {
            public void run() {
                try { web.evaluateJavascript(js, null); } catch (Exception e) { }
            }
        });
    }

    private boolean assetExists(String p) {
        try {
            java.io.InputStream in = ctx.getAssets().open(p);
            in.close();
            return true;
        } catch (Exception e) {
            return false;
        }
    }

    // 演唱版：把包里的 m4a 拷到缓存再交给 MediaPlayer（m4a 在 assets 里被压缩，直接 openFd 会失败）
    private String playMediaAsset(final String name, final String asset) {
        stopSong();
        songStop = false;
        songName = name;
        songErr = "";
        songSamples = 0;
        try {
            java.io.File f = new java.io.File(ctx.getCacheDir(), "song_" + name);
            if (!f.exists() || f.length() < 1024) {
                java.io.InputStream in = ctx.getAssets().open(asset);
                java.io.FileOutputStream os = new java.io.FileOutputStream(f);
                byte[] buf = new byte[8192];
                int n;
                while ((n = in.read(buf)) > 0) os.write(buf, 0, n);
                os.close();
                in.close();
            }
            android.media.MediaPlayer m = new android.media.MediaPlayer();
            m.setDataSource(f.getAbsolutePath());
            m.setOnCompletionListener(new android.media.MediaPlayer.OnCompletionListener() {
                public void onCompletion(android.media.MediaPlayer mp) { songEvt("DONE|" + name); }
            });
            m.setOnErrorListener(new android.media.MediaPlayer.OnErrorListener() {
                public boolean onError(android.media.MediaPlayer mp, int what, int extra) {
                    songErr = "MEDIA what=" + what + " extra=" + extra;
                    songEvt("ERR|MEDIA " + songErr);
                    return true;
                }
            });
            m.prepare();
            int dur = m.getDuration() / 1000;
            double from = songStartSec;
            songStartSec = 0;
            if (from > 0.5 && from < dur - 2) m.seekTo((int) (from * 1000));
            m.start();
            songMp = m;
            songEvt("OK|" + dur + "|0|" + name);
            return "START|" + name;
        } catch (Throwable e) {
            songErr = "CATCH " + e.getClass().getSimpleName() + " " + (e.getMessage() == null ? "" : e.getMessage());
            return "ERR|MEDIA " + songErr;
        }
    }

    // 快进/跳到指定秒：演唱版直接 seekTo；ADPCM 那几首按帧重开一条
    @JavascriptInterface
    public boolean seekSong(double sec) {
        android.media.MediaPlayer m = songMp;
        if (m != null) {
            try {
                int dur = m.getDuration() / 1000;
                int ms = (int) (sec * 1000);
                if (ms < 0) ms = 0;
                if (dur > 0 && ms > dur * 1000 - 300) ms = dur * 1000 - 300;
                m.seekTo(ms);
                return true;
            } catch (Exception e) {
                return false;
            }
        }
        if (songTrack != null && songName != null && songName.length() > 0) {
            String nm = songName;
            songStartSec = sec;
            playSongAsset(nm);
            return true;
        }
        return false;
    }

    @JavascriptInterface
    public void pauseSong() {
        android.media.MediaPlayer m = songMp;
        if (m != null) { try { if (m.isPlaying()) m.pause(); } catch (Exception e) { } return; }
        android.media.AudioTrack t = songTrack;
        if (t != null) { try { t.pause(); } catch (Exception e) { } }
    }

    @JavascriptInterface
    public void resumeSong() {
        android.media.MediaPlayer m = songMp;
        if (m != null) { try { m.start(); } catch (Exception e) { } return; }
        android.media.AudioTrack t = songTrack;
        if (t != null) { try { t.play(); } catch (Exception e) { } }
    }

    @JavascriptInterface
    public boolean isPaused() {
        android.media.MediaPlayer m = songMp;
        if (m != null) {
            try { return !m.isPlaying(); } catch (Exception e) { return false; }
        }
        return false;
    }

    // 页面轮询这两个：Position 是「真写进去了多少采样」折算的秒数，没出声就一直是 0
    @JavascriptInterface
    public double songPos() {
        android.media.MediaPlayer m = songMp;
        if (m != null) {
            try { return m.getCurrentPosition() / 1000.0; } catch (Exception e) { return 0; }
        }
        int sr = songSr;
        if (sr <= 0) return -1;
        return (double) songSamples / (double) sr;
    }

    @JavascriptInterface
    public String songDiag() {
        int sr = songSr;
        double p = sr > 0 ? (double) songSamples / (double) sr : -1;
        return "pos=" + (sr > 0 ? String.format(java.util.Locale.US, "%.2f", p) : "-1")
                + " sr=" + sr + " peak=" + songPeak + " under=" + songUnder
                + " frames=" + songFramesTotal + " err=" + songErr;
    }

    // 只解一帧（1028 字节 → 最多 2048 个采样），内存恒定
    private int decodeFrame(byte[] raw, int pos, int end, short[] out) {
        int o = 0;
        int pred = (short) ((raw[pos] & 0xff) | ((raw[pos + 1] & 0xff) << 8));
        int idx = raw[pos + 2] & 0xff;
        for (int b = pos + 4; b < end; b++) {
            int by = raw[b] & 0xff;
            for (int k = 0; k < 2; k++) {
                int code = (k == 0) ? ((by >> 4) & 15) : (by & 15);
                if (idx < 0) idx = 0; if (idx > 88) idx = 88;
                int step = ADP_STEP[idx];
                int delta = step >> 3;
                if ((code & 4) != 0) delta += step;
                if ((code & 2) != 0) delta += step >> 1;
                if ((code & 1) != 0) delta += step >> 2;
                pred += ((code & 8) != 0) ? -delta : delta;
                if (pred > 32767) pred = 32767; else if (pred < -32768) pred = -32768;
                idx += ADP_IDX[code & 7];
                if (idx < 0) idx = 0; else if (idx > 88) idx = 88;
                if (o < out.length) out[o++] = (short) pred;
            }
        }
        return o;
    }

    // 建 track：必须走媒体流（USAGE_MEDIA / STREAM_MUSIC），否则音量键压不住、听不见
    private android.media.AudioTrack makeTrack(int sr) {
        int minBuf = android.media.AudioTrack.getMinBufferSize(sr,
                android.media.AudioFormat.CHANNEL_OUT_MONO,
                android.media.AudioFormat.ENCODING_PCM_16BIT);
        if (minBuf < 4096) minBuf = 4096;
        int bufBytes = minBuf * 2;
        android.media.AudioTrack t;
        if (android.os.Build.VERSION.SDK_INT >= 21) {
            android.media.AudioAttributes aa = new android.media.AudioAttributes.Builder()
                    .setUsage(android.media.AudioAttributes.USAGE_MEDIA)
                    .setContentType(android.media.AudioAttributes.CONTENT_TYPE_MUSIC).build();
            android.media.AudioFormat fmt = new android.media.AudioFormat.Builder()
                    .setEncoding(android.media.AudioFormat.ENCODING_PCM_16BIT)
                    .setSampleRate(sr)
                    .setChannelMask(android.media.AudioFormat.CHANNEL_OUT_MONO).build();
            t = new android.media.AudioTrack(aa, fmt, bufBytes, android.media.AudioTrack.MODE_STREAM,
                    android.media.AudioManager.AUDIO_SESSION_ID_GENERATE);
        } else {
            t = new android.media.AudioTrack(android.media.AudioManager.STREAM_MUSIC, sr,
                    android.media.AudioFormat.CHANNEL_OUT_MONO,
                    android.media.AudioFormat.ENCODING_PCM_16BIT,
                    bufBytes, android.media.AudioTrack.MODE_STREAM);
        }
        try { t.setVolume(1.0f); } catch (Exception e) { }
        return t;
    }

    private int writeChunk(android.media.AudioTrack t, short[] pcm, int off, int n) {
        if (android.os.Build.VERSION.SDK_INT >= 23) {
            return t.write(pcm, off, n, android.media.AudioTrack.WRITE_BLOCKING);
        }
        return t.write(pcm, off, n);
    }

    private byte[] readAsset(String path) {
        java.io.InputStream is = null;
        try {
            is = ctx.getAssets().open(path);
            java.io.ByteArrayOutputStream bo = new java.io.ByteArrayOutputStream();
            byte[] buf = new byte[16384];
            int n;
            while ((n = is.read(buf)) > 0) bo.write(buf, 0, n);
            return bo.toByteArray();
        } catch (Exception e) {
            return null;
        } finally {
            try { if (is != null) is.close(); } catch (Exception e) { }
        }
    }

    private static final int[] ADP_STEP = {
        7, 8, 9, 10, 11, 12, 13, 14, 16, 17, 19, 21, 23, 25, 28, 31, 34, 37, 41, 45, 50, 55, 60, 66,
        73, 80, 88, 97, 107, 118, 130, 143, 157, 173, 190, 209, 230, 253, 279, 307, 337, 371, 408, 449,
        494, 544, 598, 658, 724, 796, 876, 963, 1060, 1166, 1282, 1411, 1552, 1707, 1878, 2066, 2272,
        2499, 2749, 3024, 3327, 3660, 4026, 4428, 4871, 5358, 5894, 6484, 7132, 7845, 8630, 9493,
        10442, 11487, 12635, 13899, 15289, 16818, 18500, 20350, 22385, 24623, 27086, 29794, 32767 };
    private static final int[] ADP_IDX = { -1, -1, -1, -1, 2, 4, 6, 8, -1, -1, -1, -1, 2, 4, 6, 8 };

    // ==== 云端语音（2026-11-20 补，手机一直有网就不用靠电脑）====
    // 听：本地录 16k 单声道 PCM，存成 wav，传 GLM-ASR-2512 换文字（实测 0.4s、转写准）
    // 说：GLM-TTS（/audio/speech）。当前账号语音合成额度不足（错误码 1113），
    //     所以这条只在页面切到「云语音」时才走，失败立刻退回系统 TTS
    private android.media.AudioRecord rec;
    private Thread recThread;
    private volatile boolean recording = false;
    private java.io.File recWav;
    private android.media.MediaPlayer mp;

    // 授权框只能在主线程弹：JS 桥接线程里直接 requestPermissions 会 throw，
    // 表现就是「按住说话」点了没反应、后面什么都没有（v0.71 及以前就是这样）
    private void askMicOnMain(final int code) {
        if (!(ctx instanceof Activity)) { postVoice("麦克风没给权限"); return; }
        final Activity act = (Activity) ctx;
        act.runOnUiThread(new Runnable() {
            public void run() {
                try {
                    act.requestPermissions(
                        new String[]{android.Manifest.permission.RECORD_AUDIO}, code);
                } catch (Exception e) {
                    postVoice("麦克风没给权限");
                }
            }
        });
    }

    /** 预热：页面刚起来就把到智谱的 TLS 连接握好，等下识别/对话少一次握手（约 150~300ms） */
    /** 2026-11-25：手机主界面「换动作」也去指挥桌面那只，不然点了只有页面里的人换姿势，浮窗纹丝不动。 */
    @JavascriptInterface
    public void petAct(final String name) {
        int k = DaoOverlay.ACT_WAVE;
        if ("fly".equals(name)) k = DaoOverlay.ACT_HOP;
        else if ("ride".equals(name)) k = DaoOverlay.ACT_SQUAT;
        else if ("tea".equals(name)) k = DaoOverlay.ACT_NOD;
        else if ("tv".equals(name)) k = DaoOverlay.ACT_SQUAT;
        else if ("skate".equals(name)) k = DaoOverlay.ACT_HOP;
        else if ("dance".equals(name)) k = DaoOverlay.ACT_WAVE;
        try { DaoOverlay.sendAction(k); } catch (Throwable e) { }
    }

    @JavascriptInterface
    public void warmUp() {
        new Thread(new Runnable() { public void run() {
            try { httpGet("https://open.bigmodel.cn/api/paas/v4/models", 4000); } catch (Exception e) { }
        }}).start();
    }

    @JavascriptInterface
    public void listenCloud(String cbId) {
        voiceCb = (cbId == null) ? "" : cbId;
        try {
            if (ctx.checkSelfPermission(android.Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
                if (ctx instanceof Activity) {
                final Activity act = (Activity) ctx;
                // 授权框只能在主线程弹；这里是 JS 桥接线程，直接 requestPermissions 会抛异常，
                // 现象就是「按住说话」点了毫无反应
                act.runOnUiThread(new Runnable() { public void run() { try { act.requestPermissions(new String[]{android.Manifest.permission.RECORD_AUDIO}, 9001); } catch (Exception e2) { postVoice("麦克风没给权限"); } } });
                } else {
                    postVoice("麦克风没给权限");
                }
                return;
            }
        } catch (Exception e) { postVoice("麦克风没给权限"); return; }
        startRecCloud();
    }

    private void startRecCloud() {
        try {
            int hz = 16000;
            int min = android.media.AudioRecord.getMinBufferSize(hz,
                android.media.AudioFormat.CHANNEL_IN_MONO,
                android.media.AudioFormat.ENCODING_PCM_16BIT);
            if (min <= 0) { postVoice("录音初始化失败"); return; }
            int bufSize = Math.max(min, 4096);
            if (rec == null) {
                rec = new android.media.AudioRecord(android.media.MediaRecorder.AudioSource.MIC, hz,
                    android.media.AudioFormat.CHANNEL_IN_MONO,
                    android.media.AudioFormat.ENCODING_PCM_16BIT, bufSize);
            }
            recWav = new java.io.File(ctx.getCacheDir(), "rec_" + System.currentTimeMillis() + ".wav");
            recording = true;
            try { rec.startRecording(); } catch (Exception e) { postVoice("录音启动失败"); recording = false; return; }
            final int bs = bufSize;
            final java.io.File out = recWav;
            recThread = new Thread(new Runnable() {
                public void run() {
                    java.io.FileOutputStream fos = null;
                    try {
                        fos = new java.io.FileOutputStream(out);
                        byte[] hdr = new byte[44];
                        fos.write(hdr);                    // 先占位，收尾再回填头
                        byte[] buf = new byte[bs];
                        int total = 0;
                        while (recording) {
                            int n = rec.read(buf, 0, buf.length);
                            if (n > 0) { fos.write(buf, 0, n); total += n; }
                        }
                        fos.close();
                        writeWavHeader(out, total, 16000);
                    } catch (Exception e) {
                        try { if (fos != null) fos.close(); } catch (Exception x) { }
                    }
                }
            });
            recThread.start();
        } catch (Exception e) { postVoice("录音启动失败"); }
    }

    private void writeWavHeader(java.io.File f, int dataLen, int hz) {
        try {
            java.io.RandomAccessFile raf = new java.io.RandomAccessFile(f, "rw");
            raf.seek(0);
            raf.writeBytes("RIFF");
            raf.write(intLE(36 + dataLen));
            raf.writeBytes("WAVEfmt ");
            raf.write(intLE(16));
            raf.write(shortLE(1));
            raf.write(shortLE(1));
            raf.write(intLE(hz));
            raf.write(intLE(hz * 2));
            raf.write(shortLE(2));
            raf.write(shortLE(16));
            raf.writeBytes("data");
            raf.write(intLE(dataLen));
            raf.close();
        } catch (Exception e) { }
    }

    private byte[] intLE(int v) {
        return new byte[]{(byte) (v & 0xff), (byte) ((v >> 8) & 0xff), (byte) ((v >> 16) & 0xff), (byte) ((v >> 24) & 0xff)};
    }

    private byte[] shortLE(int v) {
        return new byte[]{(byte) (v & 0xff), (byte) ((v >> 8) & 0xff)};
    }

    @JavascriptInterface
    public void stopListenCloud() {
        if (!recording) return;
        recording = false;
        try { if (rec != null) rec.stop(); } catch (Exception e) { }
        final java.io.File f = recWav;
        // 原来固定等 250ms 让录音线程把文件收尾；现在直接等线程结束，能少等就少等
        try { if (recThread != null) recThread.join(600); } catch (Exception e) { }
        new Thread(new Runnable() {
            public void run() {
                if (f == null || !f.exists() || f.length() < 3000) { postVoice("没录到声音"); return; }
                java.io.File up = trimSilence(f);      // 先裁首尾静音：少传一段、识别也快一点
                if (up == null) up = f;
                String t = asrCloud(up);
                try { if (up != f) up.delete(); } catch (Exception e) { }
                try { f.delete(); } catch (Exception e) { }
                if (t == null) { postVoice("没听清（网络不通）"); return; }
                t = t.trim();
                if (t.length() == 0) { postVoice("没听清，再说一遍"); return; }
                postVoice(t);
            }
        }).start();
    }

    /** 裁掉首尾静音：16k 单声道 16bit，50ms 一窗算 RMS，阈值 300（约 -40dBFS）。
     *  常见一句话前后各有一两秒空白，裁掉后上传量少 20%~40%，云识别也更快。 */
    private java.io.File trimSilence(java.io.File f) {
        try {
            byte[] all = java.nio.file.Files.readAllBytes(f.toPath());
            int n = (all.length - 44) / 2;
            if (n < 800) return null;
            int win = 800;                                   // 50ms
            int frames = n / win;
            int first = -1, last = -1;
            for (int i = 0; i < frames; i++) {
                long sum = 0;
                int base = 44 + i * win * 2;
                for (int j = 0; j < win; j++) {
                    int s = all[base + j * 2] | (all[base + j * 2 + 1] << 8);
                    sum += s * s;
                }
                double rms = Math.sqrt((double) sum / win);
                if (rms > 300) { if (first < 0) first = i; last = i; }
            }
            if (first < 0) return null;
            int s0 = Math.max(0, (first - 2) * win);          // 前后各留 100ms 余量
            int s1 = Math.min(n, (last + 3) * win);
            if (s1 - s0 < win) return null;                   // 太短就别折腾
            java.io.File out = new java.io.File(ctx.getCacheDir(), "rec_trim_" + System.currentTimeMillis() + ".wav");
            java.io.FileOutputStream fos = new java.io.FileOutputStream(out);
            byte[] hdr = new byte[44];
            fos.write(hdr);
            byte[] body = new byte[(s1 - s0) * 2];
            System.arraycopy(all, 44 + s0 * 2, body, 0, body.length);
            fos.write(body);
            fos.close();
            writeWavHeader(out, body.length, 16000);
            return out;
        } catch (Exception e) { return null; }
    }

    private String asrCloud(java.io.File f) {
        HttpURLConnection c = null;
        try {
            String B = "----dao" + System.currentTimeMillis();
            c = (HttpURLConnection) new URL("https://open.bigmodel.cn/api/paas/v4/audio/transcriptions").openConnection();
            c.setRequestMethod("POST");
            c.setDoOutput(true);
            c.setConnectTimeout(8000);
            c.setReadTimeout(30000);
            c.setRequestProperty("Authorization", "Bearer " + key());
            c.setRequestProperty("Content-Type", "multipart/form-data; boundary=" + B);
            OutputStream os = c.getOutputStream();
            os.write(("--" + B + "\r\nContent-Disposition: form-data; name=\"model\"\r\n\r\nglm-asr-2512\r\n").getBytes("UTF-8"));
            os.write(("--" + B + "\r\nContent-Disposition: form-data; name=\"file\"; filename=\"a.wav\"\r\nContent-Type: audio/wav\r\n\r\n").getBytes("UTF-8"));
            java.io.FileInputStream fis = new java.io.FileInputStream(f);
            byte[] buf = new byte[8192];
            int n;
            while ((n = fis.read(buf)) > 0) os.write(buf, 0, n);
            fis.close();
            os.write(("\r\n--" + B + "--\r\n").getBytes("UTF-8"));
            os.flush();
            os.close();
            if (c.getResponseCode() != 200) return null;
            String r = readAllText(c.getInputStream());
            JSONObject o = new JSONObject(r);
            return o.optString("text", "");
        } catch (Exception e) {
            return null;
        } finally {
            try { if (c != null) c.disconnect(); } catch (Exception e) { }
        }
    }

    private String readAllText(InputStream is) {
        try {
            java.io.ByteArrayOutputStream bo = new java.io.ByteArrayOutputStream();
            byte[] b = new byte[4096];
            int n;
            while ((n = is.read(b)) > 0) bo.write(b, 0, n);
            is.close();
            return new String(bo.toByteArray(), "UTF-8");
        } catch (Exception e) { return ""; }
    }

    // 云端合成：拿到 wav 存本地，用 MediaPlayer 放（系统 TTS 和它互不干扰）
    @JavascriptInterface
    public void speakCloud(final String text, final String voice) {
        stopAudio();
        final String t = (text == null) ? "" : text.trim();
        if (t.length() == 0) return;
        new Thread(new Runnable() {
            public void run() {
                try {
                    JSONObject body = new JSONObject();
                    body.put("model", "glm-tts");
                    body.put("input", t);
                    body.put("voice", (voice == null || voice.length() == 0) ? "female" : voice);
                    body.put("speed", 1.0);
                    body.put("volume", 1.0);
                    body.put("response_format", "wav");
                    HttpURLConnection c = (HttpURLConnection) new URL("https://open.bigmodel.cn/api/paas/v4/audio/speech").openConnection();
                    c.setRequestMethod("POST");
                    c.setDoOutput(true);
                    c.setConnectTimeout(8000);
                    c.setReadTimeout(40000);
                    c.setRequestProperty("Authorization", "Bearer " + key());
                    c.setRequestProperty("Content-Type", "application/json");
                    OutputStream os = c.getOutputStream();
                    os.write(body.toString().getBytes("UTF-8"));
                    os.close();
                    if (c.getResponseCode() != 200) { fallbackNative(t); return; }
                    java.io.File f = new java.io.File(ctx.getCacheDir(), "tts_" + System.currentTimeMillis() + ".wav");
                    java.io.FileOutputStream fos = new java.io.FileOutputStream(f);
                    java.io.InputStream is = c.getInputStream();
                    byte[] buf = new byte[8192];
                    int n;
                    while ((n = is.read(buf)) > 0) fos.write(buf, 0, n);
                    is.close();
                    fos.close();
                    c.disconnect();
                    if (f.length() < 2000) { fallbackNative(t); return; }
                    ui.post(new Runnable() {
                        public void run() {
                            try {
                                if (mp != null) { try { mp.release(); } catch (Exception e) { } }
                                mp = new android.media.MediaPlayer();
                                mp.setDataSource(f.getAbsolutePath());
                                mp.prepare();
                                mp.start();
                            } catch (Exception e) { fallbackNative(t); }
                        }
                    });
                } catch (Exception e) { fallbackNative(t); }
            }
        }).start();
    }

    private void fallbackNative(final String t) { ui.post(new Runnable() { public void run() { speak(t); } }); }

    // ==== 腾讯云语音合成（TextToVoice，TC3-HMAC-SHA256）====
    // 为什么选它：通用合成基础音色有 800 万字符免费额度，日常说话够用好几辈子。
    // 密钥不写死在代码里，存在本机 SharedPreferences；页面长按「听歌」可录入。
    private static final String TC_HOST = "tts.tencentcloudapi.com";
    private static final String TC_SERVICE = "tts";
    private static final String TC_ACTION = "TextToVoice";
    private static final String TC_VERSION = "2019-08-23";
    private static final String TC_REGION = "ap-guangzhou";

    @JavascriptInterface
    public void setTencentKeys(String sid, String skey) {
        try {
            sp.edit().putString("tc_sid", sid == null ? "" : sid.trim())
                      .putString("tc_skey", skey == null ? "" : skey.trim()).apply();
        } catch (Exception e) { }
    }

    @JavascriptInterface
    public String hasTencentKeys() {
        try {
            String a = sp.getString("tc_sid", "");
            String b = sp.getString("tc_skey", "");
            return (a.length() > 10 && b.length() > 10) ? "1" : "0";
        } catch (Exception e) { return "0"; }
    }

    private static String tcHex(byte[] b) {
        StringBuilder sb = new StringBuilder();
        for (byte x : b) sb.append(String.format("%02x", x));
        return sb.toString();
    }

    private static String tcSha256(String s) throws Exception {
        java.security.MessageDigest md = java.security.MessageDigest.getInstance("SHA-256");
        return tcHex(md.digest(s.getBytes("UTF-8")));
    }

    private static byte[] tcHmac(byte[] key, String msg) throws Exception {
        javax.crypto.Mac mac = javax.crypto.Mac.getInstance("HmacSHA256");
        mac.init(new javax.crypto.spec.SecretKeySpec(key, "HmacSHA256"));
        return mac.doFinal(msg.getBytes("UTF-8"));
    }

    private static String tcJsonStr(String s) {
        StringBuilder sb = new StringBuilder("\"");
        for (char ch : s.toCharArray()) {
            if (ch == '"' || ch == '\\') sb.append('\\').append(ch);
            else if (ch == '\n') sb.append("\\n");
            else if (ch < 32) sb.append(String.format("\\u%04x", (int) ch));
            else sb.append(ch);
        }
        return sb.append('"').toString();
    }

    @JavascriptInterface
    public void speakTencent(final String text, final int voiceType) {
        stopAudio();
        final String t = (text == null) ? "" : text.trim();
        if (t.length() == 0) return;
        final String sid = sp.getString("tc_sid", "");
        final String skey = sp.getString("tc_skey", "");
        if (sid.length() < 10 || skey.length() < 10) {
            ui.post(new Runnable() { public void run() { speak(t); } });
            return;
        }
        new Thread(new Runnable() {
            public void run() {
                try {
                    long ts = System.currentTimeMillis() / 1000;
                    java.text.SimpleDateFormat sdf = new java.text.SimpleDateFormat("yyyy-MM-dd", Locale.US);
                    sdf.setTimeZone(java.util.TimeZone.getTimeZone("UTC"));
                    String date = sdf.format(new java.util.Date(ts * 1000));
                    String ct = "application/json; charset=utf-8";
                    String payload = "{\"Text\":" + tcJsonStr(t) + ",\"SessionId\":\"dao" + ts
                            + "\",\"VoiceType\":" + voiceType + ",\"Codec\":\"mp3\""
                            + ",\"SampleRate\":16000,\"ModelType\":1,\"Speed\":0}";
                    String canonical = "POST\n/\n\n" + "content-type:" + ct + "\nhost:" + TC_HOST
                            + "\n\ncontent-type;host\n" + tcSha256(payload);
                    String toSign = "TC3-HMAC-SHA256\n" + ts + "\n" + date + "/" + TC_SERVICE
                            + "/tc3_request\n" + tcSha256(canonical);
                    byte[] k1 = tcHmac(("TC3" + skey).getBytes("UTF-8"), date);
                    byte[] k2 = tcHmac(k1, TC_SERVICE);
                    byte[] k3 = tcHmac(k2, "tc3_request");
                    String sig = tcHex(tcHmac(k3, toSign));
                    String auth = "TC3-HMAC-SHA256 Credential=" + sid + "/" + date + "/" + TC_SERVICE
                            + "/tc3_request, SignedHeaders=content-type;host, Signature=" + sig;

                    HttpURLConnection c = (HttpURLConnection) new URL("https://" + TC_HOST).openConnection();
                    c.setRequestMethod("POST");
                    c.setDoOutput(true);
                    c.setConnectTimeout(8000);
                    c.setReadTimeout(30000);
                    c.setRequestProperty("Authorization", auth);
                    c.setRequestProperty("Content-Type", ct);
                    c.setRequestProperty("Host", TC_HOST);
                    c.setRequestProperty("X-TC-Action", TC_ACTION);
                    c.setRequestProperty("X-TC-Timestamp", String.valueOf(ts));
                    c.setRequestProperty("X-TC-Version", TC_VERSION);
                    c.setRequestProperty("X-TC-Region", TC_REGION);
                    OutputStream os = c.getOutputStream();
                    os.write(payload.getBytes("UTF-8"));
                    os.close();
                    if (c.getResponseCode() != 200) { fallbackNative(t); return; }
                    String rs = readAllText(c.getInputStream());
                    JSONObject resp = new JSONObject(rs).optJSONObject("Response");
                    String audio = (resp == null) ? "" : resp.optString("Audio", "");
                    if (audio.length() < 100) { fallbackNative(t); return; }
                    byte[] mp3 = android.util.Base64.decode(audio, android.util.Base64.DEFAULT);
                    final java.io.File f = new java.io.File(ctx.getCacheDir(), "tc_" + System.currentTimeMillis() + ".mp3");
                    java.io.FileOutputStream fos = new java.io.FileOutputStream(f);
                    fos.write(mp3);
                    fos.close();
                    ui.post(new Runnable() {
                        public void run() {
                            try {
                                if (mp != null) { try { mp.release(); } catch (Exception e) { } }
                                mp = new android.media.MediaPlayer();
                                mp.setDataSource(f.getAbsolutePath());
                                mp.prepare();
                                mp.start();
                            } catch (Exception e) { fallbackNative(t); }
                        }
                    });
                } catch (Exception e) { fallbackNative(t); }
            }
        }).start();
    }

    // ==== Edge 直连发音（2026-11-20 补，手机自己连微软朗读，不要密钥不要额度）====
    // 令牌是 Sec-MS-GEC v2（私有 SHA256 变体 + CS64），算法在 EdgeToken.java；
    // WebSocket 自己在 EdgeTts.java 里手搓，手机端不依赖 OkHttp。
    // 实测：7 秒句子约 3 秒出声，mp3 直接 MediaPlayer 放，不烧任何额度。
    public static final String[] EDGE_VOICES = {
        "zh-CN-XiaoxiaoNeural",   // 0 少女清亮
        "zh-CN-YunxiNeural",      // 1 少年
        "zh-CN-YunjianNeural",    // 2 男声偏厚
        "zh-CN-XiaoyiNeural"      // 3 女声温柔
    };

    @JavascriptInterface
    public void speakEdge(final String text, final int vIdx) {
        stopAudio();
        final String t = (text == null) ? "" : text.trim();
        if (t.length() == 0) return;
        final String voice = EDGE_VOICES[(vIdx < 0 || vIdx >= EDGE_VOICES.length) ? 0 : vIdx];
        new Thread(new Runnable() {
            public void run() {
                try {
                    byte[] mp3 = EdgeTts.synth(t, voice);
                    if (mp3 == null || mp3.length < 1500) { fallbackNative(t); return; }
                    final java.io.File f = new java.io.File(ctx.getCacheDir(), "edge_" + System.currentTimeMillis() + ".mp3");
                    java.io.FileOutputStream fos = new java.io.FileOutputStream(f);
                    fos.write(mp3);
                    fos.close();
                    ui.post(new Runnable() {
                        public void run() {
                            try {
                                if (mp != null) { try { mp.release(); } catch (Exception e) { } }
                                mp = new android.media.MediaPlayer();
                                mp.setDataSource(f.getAbsolutePath());
                                mp.prepare();
                                mp.start();
                            } catch (Exception e) { fallbackNative(t); }
                        }
                    });
                } catch (Exception e) { fallbackNative(t); }
            }
        }).start();
    }

    // ================== 低延迟说话（v0.79） ==================
    // 旧路径：整段回答 -> 合成整段 mp3（1.3~1.8s）-> 才出声，加上识别和对话，一趟要 4~6 秒。
    // 新路径：回答按句流出 -> 每句单独合成 -> 第 1 句一好就开口，
    //        后面几句在播第 1 句的同时后台预合成，句子之间不断档。
    // 常用短句命中缓存（cacheDir/dao_tts）就不用联网，出声只要几十毫秒。
    private final java.util.ArrayDeque<String> sayQ = new java.util.ArrayDeque<String>();
    private final java.util.HashSet<String> saying = new java.util.HashSet<String>();
    private final Object sayLock = new Object();
    private Thread sayWorker = null;
    private volatile int sayGen = 0;

    private String md5h(String s) {
        try {
            java.security.MessageDigest md = java.security.MessageDigest.getInstance("MD5");
            byte[] d = md.digest(s.getBytes("UTF-8"));
            StringBuilder sb = new StringBuilder();
            for (int i = 0; i < d.length; i++) sb.append(String.format("%02x", d[i]));
            return sb.toString();
        } catch (Exception e) { return Integer.toHexString(s.hashCode()); }
    }

    private java.io.File ttsCacheFile(String text) {
        try {
            java.io.File dir = new java.io.File(ctx.getCacheDir(), "dao_tts");
            if (!dir.exists()) dir.mkdirs();
            return new java.io.File(dir, md5h(EDGE_VOICES[0] + "|" + text) + ".mp3");
        } catch (Exception e) { return null; }
    }

    /** 作废当前说话队列（停歌、开新话题、页面喊停时都调） */
    private void cancelSay() {
        synchronized (sayLock) {
            sayGen++;
            sayQ.clear();
            try { sayLock.notifyAll(); } catch (Exception e) { }
        }
    }

    /** 把一句放进说话队列（线程安全，可边生成边放） */
    private void sayEnqueue(String text) {
        if (text == null) return;
        final String t0 = text.trim();
        if (t0.length() == 0) return;
        synchronized (sayLock) {
            sayQ.add(t0);
            if (sayWorker == null || !sayWorker.isAlive()) {
                final int gen = sayGen;
                sayWorker = new Thread(new Runnable() { public void run() { sayPump(gen); } });
                sayWorker.setPriority(Thread.NORM_PRIORITY + 2);
                sayWorker.start();
            }
        }
    }

    private void sayPump(int gen) {
        while (true) {
            String t;
            synchronized (sayLock) {
                t = sayQ.poll();
                if (t == null) { sayWorker = null; return; }
            }
            if (gen != sayGen) { sayWorker = null; return; }
            String nx;
            synchronized (sayLock) { nx = sayQ.peek(); }
            if (nx != null) prefetchTts(nx);           // 边播这句边备下一句
            sayOne(t, gen);
        }
    }

    private void prefetchTts(final String text) {
        final java.io.File f = ttsCacheFile(text);
        if (f == null || (f.exists() && f.length() > 1200)) return;
        synchronized (saying) { if (!saying.add(text)) return; }
        new Thread(new Runnable() { public void run() {
            try {
                byte[] mp3 = EdgeTts.synth(text, EDGE_VOICES[0]);
                if (mp3 != null && mp3.length > 1200) {
                    java.io.FileOutputStream fos = new java.io.FileOutputStream(f);
                    fos.write(mp3); fos.close();
                }
            } catch (Exception e) { }
            finally { synchronized (saying) { saying.remove(text); } }
        }}).start();
    }

    /** 系统 TTS 兜底：追加不打断，一段段接下去说 */
    private void speakRaw(final String t) {
        initTts();
        ui.post(new Runnable() { public void run() {
            try {
                if (tts == null) return;
                tts.setSpeechRate(0.95f);
                tts.speak(t, TextToSpeech.QUEUE_ADD, null, "dao" + System.currentTimeMillis());
            } catch (Exception e) { }
        }});
    }

    private void sayOne(final String text, int gen) {
        if (gen != sayGen) return;
        java.io.File f = ttsCacheFile(text);
        boolean ok = false;
        try {
            if (f != null && !(f.exists() && f.length() > 1200)) {
                byte[] mp3 = EdgeTts.synth(text, EDGE_VOICES[0]);
                if (mp3 != null && mp3.length > 1200) {
                    java.io.FileOutputStream fos = new java.io.FileOutputStream(f);
                    fos.write(mp3); fos.close();
                }
            }
            ok = (f != null && f.exists() && f.length() > 1200);
        } catch (Exception e) { ok = false; }
        if (!ok) { speakRaw(text); return; }

        final Object done = new Object();
        final boolean[] fin = new boolean[]{false};
        final java.io.File ff = f;
        ui.post(new Runnable() { public void run() {
            try {
                if (mp != null) { try { mp.release(); } catch (Exception e) { } }
                mp = new android.media.MediaPlayer();
                mp.setDataSource(ff.getAbsolutePath());
                mp.prepare();
                mp.setOnCompletionListener(new android.media.MediaPlayer.OnCompletionListener() {
                    public void onCompletion(android.media.MediaPlayer m) {
                        synchronized (done) { fin[0] = true; done.notifyAll(); }
                    }
                });
                mp.start();
            } catch (Exception e) { synchronized (done) { fin[0] = true; done.notifyAll(); } }
        }});
        synchronized (done) {
            long dl = System.currentTimeMillis() + 20000;
            while (!fin[0] && System.currentTimeMillis() < dl) {
                try { done.wait(200); } catch (Exception e) { break; }
                if (gen != sayGen) { try { if (mp != null) mp.stop(); } catch (Exception e) { } return; }
            }
        }
        trimTtsCache();
    }

    private long ttsTrimAt = 0;
    private void trimTtsCache() {
        long now = System.currentTimeMillis();
        if (now - ttsTrimAt < 60000) return;
        ttsTrimAt = now;
        try {
            java.io.File dir = new java.io.File(ctx.getCacheDir(), "dao_tts");
            java.io.File[] fs = dir.listFiles();
            if (fs == null || fs.length < 80) return;
            java.util.Arrays.sort(fs, new java.util.Comparator<java.io.File>() {
                public int compare(java.io.File a, java.io.File b) {
                    return Long.compare(a.lastModified(), b.lastModified());
                }
            });
            int n = fs.length - 60;
            for (int i = 0; i < n; i++) { try { fs[i].delete(); } catch (Exception e) { } }
        } catch (Exception e) { }
    }

    /** JS 直接丢一句话来念（不需要走对话） */
    @JavascriptInterface
    public void sayText(String text) {
        stopAudio();
        sayEnqueue(text);
    }

    /** 流式对话：边生成边按句说话，字幕最后一次性给 */
    @JavascriptInterface
    public void chatStream(final String text, final String cbId) {
        final String q = (text == null) ? "" : text.trim();
        final String id = (cbId == null) ? "" : cbId;
        if (q.length() == 0) { postReply(id, "你想跟我说点什么？", 0); return; }
        if (!hasKey()) { postReply(id, "还没配置对话密钥，先在电脑端设置里填上，我就能聊天了。", 0); return; }
        stopAudio();
        new Thread(new Runnable() {
            public void run() {
                StringBuilder body = new StringBuilder();
                StringBuilder raw = new StringBuilder();
                boolean moodParsed = false;
                int mood = 0;
                int spoken = 0;
                HttpURLConnection conn = null;
                try {
                    JSONObject o = new JSONObject();
                    o.put("model", MODEL);
                    o.put("temperature", 0.7);
                    o.put("max_tokens", 130);
                    o.put("stream", true);
                    o.put("messages", buildMsgs(SYS_CHAT, q, true));
                    conn = (HttpURLConnection) new URL(API).openConnection();
                    conn.setRequestMethod("POST");
                    conn.setConnectTimeout(12000);
                    conn.setReadTimeout(30000);
                    conn.setDoOutput(true);
                    conn.setRequestProperty("Content-Type", "application/json");
                    conn.setRequestProperty("Authorization", "Bearer " + key());
                    OutputStream os = conn.getOutputStream();
                    os.write(o.toString().getBytes("UTF-8"));
                    os.flush(); os.close();
                    if (conn.getResponseCode() != 200) { chat(q, id); return; }

                    BufferedReader br = new BufferedReader(new InputStreamReader(conn.getInputStream(), "UTF-8"));
                    String line;
                    while ((line = br.readLine()) != null) {
                        if (line.length() < 5 || !line.startsWith("data:")) continue;
                        String d = line.substring(5).trim();
                        if (d.equals("[DONE]")) break;
                        JSONObject j;
                        try { j = new JSONObject(d); } catch (Exception e) { continue; }
                        JSONArray ch = j.optJSONArray("choices");
                        if (ch == null || ch.length() == 0) continue;
                        JSONObject dl = ch.getJSONObject(0).optJSONObject("delta");
                        if (dl == null) continue;
                        String piece = dl.optString("content", "");
                        if (piece.length() == 0) continue;

                        if (!moodParsed) {
                            raw.append(piece);
                            int bar = raw.indexOf("|");
                            if (bar >= 0) {
                                mood = moodCode(raw.substring(0, Math.min(bar, 10)).trim());
                                body.append(raw.substring(bar + 1));
                                raw.setLength(0);
                                moodParsed = true;
                            } else if (raw.length() > 14) {
                                body.append(raw); raw.setLength(0); moodParsed = true;
                            }
                        } else {
                            body.append(piece);
                        }
                        if (moodParsed) spoken = flushSpeak(body, spoken);
                    }
                    br.close();
                } catch (Exception e) {
                    if (body.length() == 0) { chat(q, id); return; }
                } finally { try { if (conn != null) conn.disconnect(); } catch (Exception e) { } }

                if (!moodParsed && raw.length() > 0) { body.append(raw); }
                String fin2 = body.toString().trim();
                if (fin2.length() == 0) { postReply(id, "我没想好怎么回，你再说一句？", 0); return; }
                if (spoken < fin2.length()) sayEnqueue(fin2.substring(spoken));
                if (fin2.length() > 200) fin2 = fin2.substring(0, 200);
                saveTurn(q, fin2);
                postReply(id, fin2, mood);
            }
        }).start();
    }

    /** 从上次说到的位置往后切句子，够一句就入队；返回新的已说位置 */
    private int flushSpeak(StringBuilder body, int spoken) {
        String cur = body.toString();
        int last = cur.length();
        if (last <= spoken) return spoken;
        for (int i = spoken; i < last; i++) {
            char c = cur.charAt(i);
            if (c == '。' || c == '？' || c == '！' || c == '?' || c == '!') {
                String seg = cur.substring(spoken, i + 1).trim();
                if (seg.length() > 1) sayEnqueue(seg);
                return i + 1;
            }
        }
        if (last - spoken >= 24) {
            int p = cur.lastIndexOf('，', last - 1);
            if (p <= spoken + 8) p = cur.lastIndexOf('、', last - 1);
            if (p > spoken + 6) {
                String seg = cur.substring(spoken, p + 1).trim();
                if (seg.length() > 0) sayEnqueue(seg);
                return p + 1;
            }
        }
        return spoken;
    }



    private void postVoice(final String text) {
        final String id = voiceCb;
        final String tx = (text == null) ? "" : text;
        ui.post(new Runnable() {
            public void run() {
                try {
                    String js = "window.__daoVoice && window.__daoVoice(" + JSONObject.quote(id) + ","
                              + JSONObject.quote(tx) + ");";
                    web.evaluateJavascript(js, null);
                } catch (Exception e) { }
            }
        });
    }

    public void tellNoMic() {
        postVoice("麦克风被拒了：进 设置 → 应用 → 道 权限 → 麦克风 打开，再按住说话");
    }

    @JavascriptInterface
    public void listen(String cbId) {
        voiceCb = (cbId == null) ? "" : cbId;
        try {
            if (ctx.checkSelfPermission(android.Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
                if (ctx instanceof Activity) {
                final Activity act = (Activity) ctx;
                // 授权框只能在主线程弹；这里是 JS 桥接线程，直接 requestPermissions 会抛异常，
                // 现象就是「按住说话」点了毫无反应
                act.runOnUiThread(new Runnable() { public void run() { try { act.requestPermissions(new String[]{android.Manifest.permission.RECORD_AUDIO}, 9001); } catch (Exception e2) { postVoice("麦克风没给权限"); } } });
                } else {
                    postVoice("麦克风没给权限");
                }
                return;
            }
        } catch (Exception e) { postVoice("麦克风没给权限"); return; }
        startListenNow();
    }

    public void startListenNow() {
        ui.post(new Runnable() {
            public void run() {
                try {
                    if (!SpeechRecognizer.isRecognitionAvailable(ctx)) { postVoice("这台手机没有语音识别服务"); return; }
                    if (sr == null) sr = SpeechRecognizer.createSpeechRecognizer(ctx);
                    sr.setRecognitionListener(new android.speech.RecognitionListener() {
                        public void onReadyForSpeech(Bundle b) { }
                        public void onBeginningOfSpeech() { }
                        public void onRmsChanged(float v) { }
                        public void onBufferReceived(byte[] b) { }
                        public void onEndOfSpeech() { }
                        public void onError(int code) { postVoice("没听清（" + code + "）"); }
                        public void onPartialResults(Bundle p) { }
                        public void onEvent(int type, Bundle p) { }
                        public void onResults(Bundle res) {
                            String t = "";
                            try {
                                ArrayList<String> xs = res.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION);
                                if (xs != null && xs.size() > 0) t = xs.get(0);
                            } catch (Exception e) { }
                            postVoice(t);
                        }
                    });
                    Intent it = new Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH);
                    it.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM);
                    it.putExtra(RecognizerIntent.EXTRA_LANGUAGE, "zh-CN");
                    it.putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, false);
                    sr.startListening(it);
                } catch (Exception e) {
                    postVoice("语音识别启动失败");
                }
            }
        });
    }

    @JavascriptInterface
    public void stopListen() {
        ui.post(new Runnable() {
            public void run() { try { if (sr != null) sr.stopListening(); } catch (Exception e) { } }
        });
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

    // 道的「脑子」：把记得的事拼进系统提示，模型才知道自己是谁、在跟谁说话
    private static final String[] FIXED_FACTS = {
        "主人是农村的初中数学老师，平时要备课、批作业、管学生。",
        "主人喜欢听歌写歌，道自己有 3 首歌：归途的月光、把好日子扛在肩上、少年模样。",
        "道说话要短、要暖，不说教，不列清单，不炫耀。"
    };

    private String fullSys(String sys) {
        StringBuilder sb = new StringBuilder(sys);
        sb.append("\n\n【你记得的事，能自然用到就用，不要生硬背诵】\n");
        for (int i = 0; i < FIXED_FACTS.length; i++) sb.append("- ").append(FIXED_FACTS[i]).append("\n");
        try {
            JSONArray f = new JSONArray(sp.getString("chat_facts", "[]"));
            int st = Math.max(0, f.length() - 8);
            for (int i = st; i < f.length(); i++) {
                String s = f.optString(i, "").trim();
                if (s.length() > 0) sb.append("- ").append(s).append("\n");
            }
        } catch (Exception e) { }
        try {
            JSONArray lh = new JSONArray(sp.getString("learn_history", "[]"));
            if (lh.length() > 0) {
                sb.append("- 最近跟主人学过：")
                  .append(lh.optString(lh.length() - 1, "").trim()).append("\n");
            }
        } catch (Exception e) { }
        return sb.toString();
    }

    // 页面可以随时教它记一件事（"记住：…"），下次对话自动带上
    @JavascriptInterface
    public String remember(String fact) {
        String f = (fact == null) ? "" : fact.trim();
        if (f.length() < 2) return "没记住";
        if (f.length() > 60) f = f.substring(0, 60);
        try {
            JSONArray arr = new JSONArray(sp.getString("chat_facts", "[]"));
            for (int i = 0; i < arr.length(); i++) {
                if (f.equals(arr.optString(i, ""))) return "记着呢";
            }
            arr.put(f);
            while (arr.length() > 24) {
                JSONArray n = new JSONArray();
                for (int i = 1; i < arr.length(); i++) n.put(arr.optString(i, ""));
                arr = n;
            }
            sp.edit().putString("chat_facts", arr.toString()).apply();
            // 同时写进分布式库：这条从此有自己的 id，别的设备按 id 认出它
            JSONArray box = memLoad();
            memPut(box, memId(f), "phone", System.currentTimeMillis(), 1, f);
            memSave(box);
            new Thread(new Runnable() { public void run() { syncPullMerge(); syncPush(); } }).start();
            return "记住了：" + f;
        } catch (Exception e) { return "没记住"; }
    }

    // ==== 分布式记忆（2026-11-20 改）====
    // 一条记忆 = 一个独立记录，按 id 认（内容 SHA-256 前 8 位），谁缺谁补。
    // 去中心：每台设备都是完整副本，同步只交换「对方没有的」条目，最后收敛到同一集合。
    private static final String SYNC_TOPIC = "dao_sync_2f7b8e14c9a36d50";
    private static final String MEM_KEY = "mem_entries";
    private java.util.ArrayList<String> lastRemoteIds = new java.util.ArrayList<String>();

    private String memId(String t) {
        try {
            java.security.MessageDigest md = java.security.MessageDigest.getInstance("SHA-256");
            byte[] h = md.digest(t.getBytes("UTF-8"));
            StringBuilder sb = new StringBuilder();
            for (int i = 0; i < 4; i++) sb.append(String.format("%02x", h[i]));
            return sb.toString();
        } catch (Exception e) { return Integer.toHexString(t.hashCode()); }
    }

    private JSONArray memLoad() {
        try { return new JSONArray(sp.getString(MEM_KEY, "[]")); } catch (Exception e) { return new JSONArray(); }
    }

    private void memSave(JSONArray a) {
        try {
            JSONArray keep = new JSONArray();
            int st = Math.max(0, a.length() - 300);
            for (int i = st; i < a.length(); i++) keep.put(a.get(i));
            sp.edit().putString(MEM_KEY, keep.toString()).apply();
        } catch (Exception e) { }
    }

    // 收一条；返回 true 表示是新的
    private boolean memPut(JSONArray a, String id, String src, long at, int rev, String t) {
        try {
            for (int i = 0; i < a.length(); i++) {
                JSONObject o = a.optJSONObject(i);
                if (o == null || !id.equals(o.optString("i"))) continue;
                if (o.optInt("r", 1) == -1) return false;   // 已删的条目不许复活
                if (rev > o.optInt("r", 1)) { o.put("r", rev); o.put("t", t); }
                return false;
            }
            JSONObject n = new JSONObject();
            n.put("i", id); n.put("s", src); n.put("a", at); n.put("r", rev); n.put("t", t);
            a.put(n);
            return true;
        } catch (Exception e) { return false; }
    }

    // 第一次跑：把老的 chat_facts 搬进分布式库
    private void memMigrate() {
        try {
            if (memLoad().length() > 0) return;
            JSONArray f = new JSONArray(sp.getString("chat_facts", "[]"));
            JSONArray a = new JSONArray();
            for (int i = 0; i < f.length(); i++) {
                String t = f.optString(i, "").trim();
                if (t.length() < 2) continue;
                memPut(a, memId(t), "phone", 0, 1, t);
            }
            if (a.length() > 0) memSave(a);
        } catch (Exception e) { }
    }

    private void memMirror(JSONArray a) {
        try {
            JSONArray f = new JSONArray();
            int st = Math.max(0, a.length() - 24);
            for (int i = st; i < a.length(); i++) {
                JSONObject o = a.optJSONObject(i);
                if (o != null) f.put(o.optString("t", ""));
            }
            sp.edit().putString("chat_facts", f.toString()).apply();
        } catch (Exception e) { }
    }

    private String readHttp(String url, int timeout) throws Exception {
        HttpURLConnection c = (HttpURLConnection) new URL(url).openConnection();
        c.setConnectTimeout(timeout);
        c.setReadTimeout(timeout);
        int code = c.getResponseCode();
        String t = (code == 200) ? readAllText(c.getInputStream()) : "";
        c.disconnect();
        return t;
    }

    private void ntfyPost(String body) throws Exception {
        byte[] raw = body.getBytes("UTF-8");
        HttpURLConnection c = (HttpURLConnection) new URL("https://ntfy.sh/" + SYNC_TOPIC).openConnection();
        c.setRequestMethod("POST");
        c.setDoOutput(true);
        c.setConnectTimeout(8000);
        c.setReadTimeout(8000);
        c.setRequestProperty("Content-Type", "text/plain; charset=utf-8");
        OutputStream os = c.getOutputStream();
        os.write(raw);
        os.close();
        int code = c.getResponseCode();
        c.disconnect();
        if (code != 200) throw new Exception("发送被拒 " + code);
    }

    // 拉：按 id 并进来
    private String syncPullMerge() {
        try {
            String text = readHttp("https://ntfy.sh/" + SYNC_TOPIC + "/json?poll=1&since=all", 8000);
            JSONArray box = memLoad();
            memMigrate();
            box = memLoad();
            lastRemoteIds = new java.util.ArrayList<String>();
            int added = 0, removed = 0;
            // ntfy 的 /raw 会把换行压平，这里按 /json 每行取 message 原文
            java.util.ArrayList<String> allLines = new java.util.ArrayList<String>();
            for (String nl : text.split("\\n")) {
                String tl = nl.trim();
                if (!tl.startsWith("{")) continue;
                try {
                    JSONObject o = new JSONObject(tl);
                    String msg = o.optString("message", "");
                    for (String ml : msg.split("\\n")) if (ml.trim().length() > 0) allLines.add(ml.trim());
                } catch (Exception e) { }
            }
            for (String line : allLines) {
                String l = line.trim();
                if (!l.startsWith("DAO2|")) continue;
                String[] f = l.split("\\|", 6);
                if (f.length < 6) continue;
                lastRemoteIds.add(f[1]);
                if ("phone".equals(f[2])) continue;
                if (f[5].trim().length() < 2) continue;
                if (f[5].indexOf("DAO2") >= 0) continue;   // 粘包的脏数据不收
                long at = 0; int rev = 1;
                try { at = Long.parseLong(f[3]); } catch (Exception e) { }
                try { rev = Integer.parseInt(f[4]); } catch (Exception e) { }
                if (rev == -1) {                     // 删除标记：落墓碑，永远压住正面记录
                    boolean found = false;
                    for (int i = 0; i < box.length(); i++) {
                        JSONObject o = box.optJSONObject(i);
                        if (o != null && f[1].equals(o.optString("i", ""))) { o.put("r", -1); found = true; }
                    }
                    if (!found) {
                        JSONObject nt = new JSONObject();
                        nt.put("i", f[1]); nt.put("s", f[2]); nt.put("a", at); nt.put("r", -1); nt.put("t", f[5]);
                        box.put(nt);
                    }
                    removed++;
                    continue;
                }
                if (memPut(box, f[1], f[2], at, rev, f[5])) added++;
            }
            memSave(box);
            memMirror(memLoad());
            if (removed > 0 && added == 0) return "别处删了 " + removed + " 条";
            if (removed > 0) return "别处同步来 " + added + " 条、删了 " + removed + " 条";
            return added > 0 ? ("别处同步来 " + added + " 条") : "已经是最新的";
        } catch (Exception e) { return "拉取失败：" + e.getMessage(); }
    }

    // 推：只发对方没有的，3KB 一批
    private String syncPush() {
        try {
            JSONArray box = memLoad();
            StringBuilder one = new StringBuilder();
            int sent = 0, chunks = 0;
            for (int i = 0; i < box.length(); i++) {
                JSONObject o = box.optJSONObject(i);
                if (o == null) continue;
                String id = o.optString("i", "");
                if (id.length() == 0 || lastRemoteIds.contains(id)) continue;
                String line = "DAO2|" + id + "|" + o.optString("s", "phone") + "|" + o.optLong("a", 0)
                        + "|" + o.optInt("r", 1) + "|" + o.optString("t", "") + "\n";
                if (one.length() + line.length() > 3000) {
                    if (one.length() > 0) { ntfyPost(one.toString()); chunks++; sent += lenLines(one.toString()); one.setLength(0); }
                }
                one.append(line);
            }
            if (one.length() > 0) { ntfyPost(one.toString()); chunks++; sent += lenLines(one.toString()); }
            return chunks == 0 ? "没有要发的新东西" : ("发出 " + sent + " 条（" + chunks + " 批）");
        } catch (Exception e) { return "发送失败：" + e.getMessage(); }
    }

    private int lenLines(String s) {
        int n = 0;
        for (String line : s.split("\n")) if (line.trim().length() > 0) n++;
        return n;
    }

    // 忘掉一件事：本地删掉，再发一条 rev=-1 的删除标记，别处跟着删
    @JavascriptInterface
    public void forget(final String text) {
        final String t0 = (text == null) ? "" : text.trim();
        if (t0.length() < 2) return;
        new Thread(new Runnable() {
            public void run() {
                String msg;
                try {
                    String t = t0.length() > 60 ? t0.substring(0, 60) : t0;
                    String id = memId(t);
                    JSONArray box = memLoad();
                    boolean hit = false;
                    for (int i = box.length() - 1; i >= 0; i--) {
                        JSONObject o = box.optJSONObject(i);
                        if (o != null && id.equals(o.optString("i", ""))) { box.remove(i); hit = true; }
                    }
                    if (!hit) { msg = "库里没这条，不用忘"; }
                    else {
                        for (int i = 0; i < box.length(); i++) {
                            JSONObject o = box.optJSONObject(i);
                            if (o != null && id.equals(o.optString("i", ""))) o.put("r", -1);
                        }
                        memSave(box);
                        memMirror(memLoad());
                        ntfyPost("DAO2|" + id + "|phone|" + System.currentTimeMillis() + "|-1|" + t + "\n");
                        msg = "忘掉了：" + t;
                    }
                } catch (Exception e) { msg = "忘掉失败：" + e.getMessage(); }
                final String m = msg;
                ui.post(new Runnable() {
                    public void run() {
                        try { web.evaluateJavascript("window.__daoSync && window.__daoSync(" + JSONObject.quote(m) + ");", null); } catch (Exception e) { }
                    }
                });
            }
        }).start();
    }

    @JavascriptInterface
    public void syncNow() {
        new Thread(new Runnable() {
            public void run() {
                String a = syncPullMerge();
                String b = syncPush();
                final String msg = a + " / " + b;
                ui.post(new Runnable() {
                    public void run() {
                        try {
                            web.evaluateJavascript("window.__daoSync && window.__daoSync(" + JSONObject.quote(msg) + ");", null);
                        } catch (Exception e) { }
                    }
                });
            }
        }).start();
    }

    // 页面要放本地音乐，得先把 assets 里的曲子读出来（WebView 的 file:// 不给读）
    @JavascriptInterface
    public String assetB64(String path) {
        InputStream is = null;
        try {
            is = ctx.getAssets().open(path);
            java.io.ByteArrayOutputStream bo = new java.io.ByteArrayOutputStream();
            byte[] buf = new byte[16384];
            int n;
            while ((n = is.read(buf)) > 0) bo.write(buf, 0, n);
            return android.util.Base64.encodeToString(bo.toByteArray(), android.util.Base64.NO_WRAP);
        } catch (Exception e) {
            return "";
        } finally {
            try { if (is != null) is.close(); } catch (Exception e) { }
        }
    }

    // 2026-11-22：assetB64 读不到时用来给出具体原因（同一个读法，但把异常说出来）
    @JavascriptInterface
    public String assetXhr(String path) {
        InputStream is = null;
        try {
            is = ctx.getAssets().open(path);
            java.io.ByteArrayOutputStream bo = new java.io.ByteArrayOutputStream();
            byte[] buf = new byte[16384];
            int n;
            while ((n = is.read(buf)) > 0) bo.write(buf, 0, n);
            return android.util.Base64.encodeToString(bo.toByteArray(), android.util.Base64.NO_WRAP);
        } catch (Exception e) {
            return "ERR|" + e.getClass().getSimpleName() + (e.getMessage() == null ? "" : " " + e.getMessage()) + " @" + path;
        } finally {
            try { if (is != null) is.close(); } catch (Exception e) { }
        }
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
                String out = requestChat(fullSys(SYS_CHAT), q, 0.7, 130);
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
            conn.setRequestProperty("Authorization", "Bearer " + key());

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

    // ==== 手机端「在桌面上」浮窗（2026-11-22）====
    // 页面只管点，真正挂窗口的是 DaoOverlay 那个前台服务。
    @JavascriptInterface
    public String overlayReady() {
        return DaoOverlay.canDraw(ctx) ? "1" : "0";
    }

    @JavascriptInterface
    public String overlayAsk() {
        DaoOverlay.askPermission(ctx);
        return "1";
    }

    /** 返回 是否开着|模式|哪一边 */
    @JavascriptInterface
    public String overlayState() {
        return DaoOverlay.state(ctx);
    }

    @JavascriptInterface
    public String overlayOn(int m) {
        if (!DaoOverlay.canDraw(ctx)) {
            DaoOverlay.askPermission(ctx);
            return "NEEDPERM";
        }
        DaoOverlay.start(ctx, m);
        return "OK";
    }

    @JavascriptInterface
    public String overlayMode(int m) {
        DaoOverlay.setMode(ctx, m);
        return "OK";
    }

    @JavascriptInterface
    public String overlaySide() {
        DaoOverlay.flipSide(ctx);
        return "OK";
    }

    @JavascriptInterface
    public String overlayOff() {
        DaoOverlay.stop(ctx);
        return "OK";
    }
}
