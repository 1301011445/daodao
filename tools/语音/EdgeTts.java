import javax.net.ssl.SSLParameters;
import javax.net.ssl.SSLSocket;
import javax.net.ssl.SSLSocketFactory;
import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.nio.charset.StandardCharsets;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;
import java.util.TimeZone;
import java.util.UUID;

/**
 * 手机直连 Edge 朗读：自己实现 WebSocket（RFC6455）握手与帧收发，不依赖 OkHttp。
 * 音频来自服务端二进制帧：前 2 字节是大端头长度，跟着是 "audio" 之类路径，其后才是 mp3 数据。
 *
 * 用法：java EdgeTts "要念的话" out.mp3
 */
public class EdgeTts {

    static final String HOST = "speech.platform.bing.com";
    static final String PATH = "/consumer/speech/synthesize/readaloud/edge/v1";
    static final String TRUSTED = "6A5AA1D4EAFF4E9FB37E23D68491D6F4";
    static final String GEC_VER = "2-143.0.3650.75";
    static final String UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            + "(KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36 Edg/143.0.0.0";

    static String b64(byte[] b) {
        final char[] T = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/".toCharArray();
        StringBuilder sb = new StringBuilder();
        int i = 0;
        while (i + 2 < b.length) {
            int n = ((b[i] & 0xFF) << 16) | ((b[i + 1] & 0xFF) << 8) | (b[i + 2] & 0xFF);
            sb.append(T[(n >> 18) & 63]).append(T[(n >> 12) & 63]).append(T[(n >> 6) & 63]).append(T[n & 63]);
            i += 3;
        }
        int rem = b.length - i;
        if (rem == 1) {
            int n = (b[i] & 0xFF) << 16;
            sb.append(T[(n >> 18) & 63]).append(T[(n >> 12) & 63]).append("==");
        } else if (rem == 2) {
            int n = ((b[i] & 0xFF) << 16) | ((b[i + 1] & 0xFF) << 8);
            sb.append(T[(n >> 18) & 63]).append(T[(n >> 12) & 63]).append(T[(n >> 6) & 63]).append('=');
        }
        return sb.toString();
    }

    static String gmtNow() {
        SimpleDateFormat f = new SimpleDateFormat("EEE MMM dd yyyy HH:mm:ss 'GMT+0000 (Coordinated Universal Time)'", Locale.US);
        f.setTimeZone(TimeZone.getTimeZone("UTC"));
        return f.format(new Date());
    }

    /** 合成，返回 mp3 字节；失败抛异常 */
    public static byte[] synth(String text, String voice) throws Exception {
        String token = EdgeToken.gec(0);
        String url = PATH + "?TrustedClientToken=" + TRUSTED
                + "&ConnectionId=" + UUID.randomUUID().toString().replace("-", "")
                + "&Sec-MS-GEC=" + token + "&Sec-MS-GEC-Version=" + GEC_VER;

        SSLSocketFactory sf = (SSLSocketFactory) SSLSocketFactory.getDefault();
        SSLSocket s = (SSLSocket) sf.createSocket(HOST, 443);
        // 低版本安卓（API<24）没有 SNIHostName，这里兜一下，别直接崩
        try {
            SSLParameters p = s.getSSLParameters();
            p.setServerNames(java.util.Collections.singletonList(new javax.net.ssl.SNIHostName(HOST)));
            p.setEndpointIdentificationAlgorithm("HTTPS");
            s.setSSLParameters(p);
        } catch (Throwable ignore) { }
        s.setSoTimeout(20000);
        s.startHandshake();

        byte[] keyBytes = new byte[16];
        java.util.Random rnd = new java.util.Random();
        rnd.nextBytes(keyBytes);
        String wsKey = b64(keyBytes);

        String req = "GET " + url + " HTTP/1.1\r\n"
                + "Host: " + HOST + "\r\n"
                + "Upgrade: websocket\r\n"
                + "Connection: Upgrade\r\n"
                + "Sec-WebSocket-Key: " + wsKey + "\r\n"
                + "Sec-WebSocket-Version: 13\r\n"
                + "Origin: chrome-extension://jdiccldimpdaibmpdkjnbmckianbfold\r\n"
                + "Pragma: no-cache\r\n"
                + "Cache-Control: no-cache\r\n"
                + "User-Agent: " + UA + "\r\n\r\n";
        OutputStream os = s.getOutputStream();
        os.write(req.getBytes(StandardCharsets.UTF_8));
        os.flush();

        InputStream is = s.getInputStream();
        ByteArrayOutputStream hs = new ByteArrayOutputStream();
        int state = 0;
        while (state < 4) {
            int c = is.read();
            if (c < 0) throw new IOException("握手无响应");
            hs.write(c);
            state = (c == '\r' && (state == 0 || state == 2)) || (c == '\n' && (state == 1 || state == 3))
                    ? state + 1 : (c == '\r' ? 1 : 0);
        }
        String hsStr = new String(hs.toByteArray(), StandardCharsets.ISO_8859_1);
        if (!hsStr.startsWith("HTTP/1.1 101")) throw new IOException("握手失败: " + hsStr.split("\r\n")[0]);

        String ts = gmtNow();
        String cfg = "X-Timestamp:" + ts + "\r\nContent-Type:application/json; charset=utf-8\r\n"
                + "Path:speech.config\r\n\r\n"
                + "{\"context\":{\"synthesis\":{\"audio\":{\"metadataoptions\":{\"sentenceBoundaryEnabled\":\"false\","
                + "\"wordBoundaryEnabled\":\"true\"},\"outputFormat\":\"audio-24khz-48kbitrate-mono-mp3\"}}}}\r\n";
        writeFrame(os, 0x1, cfg.getBytes(StandardCharsets.UTF_8));

        String rid = UUID.randomUUID().toString().replace("-", "");
        String ssml = "X-RequestId:" + rid + "\r\nContent-Type:application/ssml+xml\r\n"
                + "X-Timestamp:" + ts + "Z\r\nPath:ssml\r\n\r\n"
                + "<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' xml:lang='en-US'>"
                + "<voice name='" + voice + "'><prosody pitch='+0Hz' rate='+0%' volume='+0%'>"
                + escapeXml(text) + "</prosody></voice></speak>";
        writeFrame(os, 0x1, ssml.getBytes(StandardCharsets.UTF_8));

        ByteArrayOutputStream audio = new ByteArrayOutputStream();
        boolean done = false;
        long deadline = System.currentTimeMillis() + 30000;
        while (!done && System.currentTimeMillis() < deadline) {
            int b0 = is.read();
            if (b0 < 0) break;
            int b1 = is.read();
            int opcode = b0 & 0x0F;
            boolean masked = (b1 & 0x80) != 0;
            long len = b1 & 0x7F;
            if (len == 126) {
                len = ((is.read() & 0xFF) << 8) | (is.read() & 0xFF);
            } else if (len == 127) {
                len = 0;
                for (int i = 0; i < 8; i++) len = (len << 8) | (is.read() & 0xFF);
            }
            byte[] mask = new byte[4];
            if (masked) readFully(is, mask);
            byte[] payload = new byte[(int) len];
            readFully(is, payload);
            if (masked) for (int i = 0; i < payload.length; i++) payload[i] ^= mask[i % 4];

            if (opcode == 0x8) break;                       // close
            else if (opcode == 0x9) writeFrame(os, 0xA, payload);  // ping -> pong
            else if (opcode == 0x1) {                        // 文本帧：找 turn.end
                String t = new String(payload, StandardCharsets.UTF_8);
                if (t.contains("Path:turn.end")) done = true;
            } else if (opcode == 0x2) {                      // 二进制帧：头 + mp3
                if (payload.length > 2) {
                    int hl = ((payload[0] & 0xFF) << 8) | (payload[1] & 0xFF);
                    int st = 2 + hl;
                    if (st < payload.length) audio.write(payload, st, payload.length - st);
                }
            }
        }
        try { writeFrame(os, 0x8, new byte[]{3, (byte) 0xE8}); } catch (Exception e) { }
        try { s.close(); } catch (Exception e) { }
        return audio.toByteArray();
    }

    static class IOException extends java.io.IOException {
        IOException(String m) { super(m); }
    }

    static void readFully(InputStream is, byte[] b) throws java.io.IOException {
        int got = 0;
        while (got < b.length) {
            int n = is.read(b, got, b.length - got);
            if (n < 0) throw new java.io.IOException("连接提前关闭");
            got += n;
        }
    }

    static void writeFrame(OutputStream os, int opcode, byte[] payload) throws java.io.IOException {
        os.write(0x80 | opcode);
        int len = payload.length;
        if (len < 126) os.write(0x80 | len);
        else if (len < 65536) { os.write(0x80 | 126); os.write((len >> 8) & 0xFF); os.write(len & 0xFF); }
        else {
            os.write(0x80 | 127);
            for (int i = 7; i >= 0; i--) os.write((int) ((((long) len) >> (8 * i)) & 0xFF));
        }
        byte[] mask = new byte[4];
        new java.util.Random().nextBytes(mask);
        os.write(mask);
        byte[] out = new byte[len];
        for (int i = 0; i < len; i++) out[i] = (byte) (payload[i] ^ mask[i % 4]);
        os.write(out);
        os.flush();
    }

    static String escapeXml(String s) {
        return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                .replace("\"", "&quot;").replace("'", "&apos;");
    }

    public static void main(String[] a) throws Exception {
        String text = a.length > 0 ? a[0] : "你好，我是道，手机自己说话。";
        String voice = a.length > 1 ? a[1] : "zh-CN-XiaoxiaoNeural";
        String out = a.length > 2 ? a[2] : "F:/Daodao/_tmp_edge_java.mp3";
        long t0 = System.currentTimeMillis();
        byte[] mp3 = synth(text, voice);
        java.io.FileOutputStream fos = new java.io.FileOutputStream(out);
        fos.write(mp3);
        fos.close();
        System.out.println("音频字节 " + mp3.length + " 耗时 " + (System.currentTimeMillis() - t0) + "ms");
    }
}
