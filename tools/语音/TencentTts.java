import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;
import java.util.TimeZone;

/**
 * 腾讯云语音合成 TextToVoice 的最小实现（TC3-HMAC-SHA256 签名）。
 * 单独可跑：javac TencentTts.java && java TencentTts <SecretId> <SecretKey> <文本>
 * 手机上 DaoBridge 里用的是同一套签名逻辑，两边保持一致。
 */
public class TencentTts {

    static final String HOST = "tts.tencentcloudapi.com";
    static final String SERVICE = "tts";
    static final String ACTION = "TextToVoice";
    static final String VERSION = "2019-08-23";
    static final String REGION = "ap-guangzhou";

    static String sha256hex(String s) throws Exception {
        MessageDigest md = MessageDigest.getInstance("SHA-256");
        byte[] d = md.digest(s.getBytes(StandardCharsets.UTF_8));
        StringBuilder sb = new StringBuilder();
        for (byte b : d) sb.append(String.format("%02x", b));
        return sb.toString();
    }

    static byte[] hmac(byte[] key, String msg) throws Exception {
        Mac mac = Mac.getInstance("HmacSHA256");
        mac.init(new SecretKeySpec(key, "HmacSHA256"));
        return mac.doFinal(msg.getBytes(StandardCharsets.UTF_8));
    }

    static String hex(byte[] b) {
        StringBuilder sb = new StringBuilder();
        for (byte x : b) sb.append(String.format("%02x", x));
        return sb.toString();
    }

    /** 返回 {状态码, 响应体} */
    public static Object[] synth(String secretId, String secretKey, String text,
                                 int voiceType, String codec, int sampleRate) throws Exception {
        long ts = System.currentTimeMillis() / 1000;
        SimpleDateFormat f = new SimpleDateFormat("yyyy-MM-dd", Locale.US);
        f.setTimeZone(TimeZone.getTimeZone("UTC"));
        String date = f.format(new Date(ts * 1000));

        String ct = "application/json; charset=utf-8";
        String payload = "{\"Text\":" + jstr(text) + ",\"SessionId\":\"dao-" + ts
                + "\",\"VoiceType\":" + voiceType + ",\"Codec\":\"" + codec
                + "\",\"SampleRate\":" + sampleRate + ",\"ModelType\":1,\"Speed\":0}";

        String canonical = "POST\n/\n\n" + "content-type:" + ct + "\nhost:" + HOST
                + "\n\ncontent-type;host\n" + sha256hex(payload);
        String toSign = "TC3-HMAC-SHA256\n" + ts + "\n" + date + "/" + SERVICE + "/tc3_request\n"
                + sha256hex(canonical);
        byte[] kDate = hmac(("TC3" + secretKey).getBytes(StandardCharsets.UTF_8), date);
        byte[] kSvc = hmac(kDate, SERVICE);
        byte[] kSign = hmac(kSvc, "tc3_request");
        String sig = hex(hmac(kSign, toSign));

        String auth = "TC3-HMAC-SHA256 Credential=" + secretId + "/" + date + "/" + SERVICE
                + "/tc3_request, SignedHeaders=content-type;host, Signature=" + sig;

        HttpURLConnection c = (HttpURLConnection) new URL("https://" + HOST).openConnection();
        c.setRequestMethod("POST");
        c.setDoOutput(true);
        c.setConnectTimeout(8000);
        c.setReadTimeout(30000);
        c.setRequestProperty("Authorization", auth);
        c.setRequestProperty("Content-Type", ct);
        c.setRequestProperty("Host", HOST);
        c.setRequestProperty("X-TC-Action", ACTION);
        c.setRequestProperty("X-TC-Timestamp", String.valueOf(ts));
        c.setRequestProperty("X-TC-Version", VERSION);
        c.setRequestProperty("X-TC-Region", REGION);
        OutputStream os = c.getOutputStream();
        os.write(payload.getBytes(StandardCharsets.UTF_8));
        os.close();

        InputStream is = c.getResponseCode() >= 400 ? c.getErrorStream() : c.getInputStream();
        ByteArrayOutputStream bo = new ByteArrayOutputStream();
        byte[] buf = new byte[8192];
        int n;
        while (is != null && (n = is.read(buf)) > 0) bo.write(buf, 0, n);
        if (is != null) is.close();
        return new Object[]{c.getResponseCode(), bo.toByteArray()};
    }

    static String jstr(String s) {
        StringBuilder sb = new StringBuilder("\"");
        for (char ch : s.toCharArray()) {
            if (ch == '"' || ch == '\\') sb.append('\\').append(ch);
            else if (ch == '\n') sb.append("\\n");
            else if (ch < 32) sb.append(String.format("\\u%04x", (int) ch));
            else sb.append(ch);
        }
        return sb.append('"').toString();
    }

    public static void main(String[] a) throws Exception {
        String sid = a.length > 0 ? a[0] : "AKIDfakefakefakefakefakefakefake";
        String skey = a.length > 1 ? a[1] : "fakekeyfakekeyfakekeyfakekeyfake";
        String text = a.length > 2 ? a[2] : "你好，我是道。";
        Object[] r = synth(sid, skey, text, 0, "mp3", 16000);
        System.out.println("HTTP " + r[0]);
        System.out.println(new String((byte[]) r[1], StandardCharsets.UTF_8));
    }
}
