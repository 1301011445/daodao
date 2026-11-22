# 程序版本：v0.1 | 2026-11-22 | 一次性：DaoBridge 音乐播放改「边解边写 + 进度上报 + 错误带码」
import io

P = r'F:\Daodao\src\_apk\src\com\daodao\pet\DaoBridge.java'
s = io.open(P, encoding='utf-8').read()

# 1) 新增字段
old_fields = '    private volatile int songGen = 0;\n'
new_fields = old_fields + '''    // 2026-11-22 晚（第二轮）：进度与诊断，页面靠这几个值判断「到底出没出声」
    private volatile int songSr = 22050;
    private volatile long songSamples = 0;      // 已成功写进 AudioTrack 的采样数
    private volatile long songFramesTotal = 0;
    private volatile int songPeak = 0;          // 解出来的最大幅值（0 = 全是静音，说明数据就有问题）
    private volatile int songUnder = 0;         // underrun 次数（>0 说明喂得太慢，会断续）
    private volatile String songErr = "";
'''
assert old_fields in s
s = s.replace(old_fields, new_fields, 1)

# 2) 整段替换：从「用户报播放失败」注释到 readAsset 之前
i0 = s.index('    // 2026-11-22 用户报「播放失败没声音，还按不了，退不出来」')
i1 = s.index('    private byte[] readAsset(String path) {')
new_block = '''    // 2026-11-22 晚（第二轮）：用户截图报「播放失败没声音，还按不了，退不出来」。查到三处硬伤：
    // ① decodePcm 一次解出 11MB short[] 才开播，低内存机直接 OOM，页面只看到「播放中」；
    // ② 失败后页面走 assetB64 / assetXhr——8MB base64 同步过桥，JS 线程被堵死，× 和歌单行都点不动；
    // ③ 开播就把行标成「♪ 播放中」，其实只是起了个线程，成没成一个字不回报。
    // 这一版：边解边写（每帧 2048 采样，内存几百 KB）、先起 track 再回 OK、进度用 songPos() 让页面轮询，
    // 出错一律带代码（NOFILE/HEADER/TRACK/WRITE/CATCH），不再静默。
    @JavascriptInterface
    public String playSongAsset(final String name) {
        if (name == null || name.length() == 0) return "ERR|NONAME 没给歌名";
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
                    int pos = 12, f = 0, zero = 0;
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

    // 页面轮询这两个：Position 是「真写进去了多少采样」折算的秒数，没出声就一直是 0
    @JavascriptInterface
    public double songPos() {
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

'''
s = s[:i0] + new_block + s[i1:]
io.open(P, 'w', encoding='utf-8').write(s)
print('DaoBridge OK, 行数', s.count('\n') + 1)
