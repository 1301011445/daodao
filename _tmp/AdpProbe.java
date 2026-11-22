// 把 pet.apk 里 DaoBridge.adpToWav 的解码逻辑原样搬出来，在 PC 上跑真包，看解码本身对不对
import java.io.*;

public class AdpProbe {
    static final int[] ADP_STEP = {
        7, 8, 9, 10, 11, 12, 13, 14, 16, 17, 19, 21, 23, 25, 28, 31, 34, 37, 41, 45, 50, 55, 60, 66,
        73, 80, 88, 97, 107, 118, 130, 143, 157, 173, 190, 209, 230, 253, 279, 307, 337, 371, 408, 449,
        494, 544, 598, 658, 724, 796, 876, 963, 1060, 1166, 1282, 1411, 1552, 1707, 1878, 2066, 2272,
        2499, 2749, 3024, 3327, 3660, 4026, 4428, 4871, 5358, 5894, 6484, 7132, 7845, 8630, 9493,
        10442, 11487, 12635, 13899, 15289, 16818, 18500, 20350, 22385, 24623, 27086, 29794, 32767 };
    static final int[] ADP_IDX = { -1, -1, -1, -1, 2, 4, 6, 8, -1, -1, -1, -1, 2, 4, 6, 8 };

    static void writeInt(OutputStream fo, int v) throws IOException {
        fo.write(v & 0xff); fo.write((v >> 8) & 0xff); fo.write((v >> 16) & 0xff); fo.write((v >> 24) & 0xff);
    }
    static void writeShort(OutputStream fo, int v) throws IOException {
        fo.write(v & 0xff); fo.write((v >> 8) & 0xff);
    }

    public static void main(String[] a) throws Exception {
        byte[] raw = readAll(a[0]);
        System.out.println("输入字节 " + raw.length);
        if (raw[0] != 'D' || raw[1] != 'A' || raw[2] != 'O' || raw[3] != '1') { System.out.println("magic 不对"); return; }
        int sr = (raw[4] & 0xff) | ((raw[5] & 0xff) << 8) | ((raw[6] & 0xff) << 16) | ((raw[7] & 0xff) << 24);
        int frames = (raw[8] & 0xff) | ((raw[9] & 0xff) << 8) | ((raw[10] & 0xff) << 16) | ((raw[11] & 0xff) << 24);
        int total = frames * 2048;
        short[] pcm = new short[total];
        int o = 0, pos = 12;
        for (int f = 0; f < frames; f++) {
            if (pos + 4 > raw.length) break;
            int pred = (short) ((raw[pos] & 0xff) | ((raw[pos + 1] & 0xff) << 8));
            int idx = raw[pos + 2] & 0xff;
            int end = Math.min(pos + 1028, raw.length);
            for (int b = pos + 4; b < end; b++) {
                int by = raw[b] & 0xff;
                for (int k = 0; k < 2; k++) {
                    int code = (k == 0) ? ((by >> 4) & 15) : (by & 15);
                    if (idx < 0) idx = 0;
                    if (idx > 88) idx = 88;
                    int step = ADP_STEP[idx];
                    int delta = step >> 3;
                    if ((code & 4) != 0) delta += step;
                    if ((code & 2) != 0) delta += step >> 1;
                    if ((code & 1) != 0) delta += step >> 2;
                    pred += ((code & 8) != 0) ? -delta : delta;
                    if (pred > 32767) pred = 32767; else if (pred < -32768) pred = -32768;
                    idx += ADP_IDX[code & 7];
                    if (idx < 0) idx = 0; else if (idx > 88) idx = 88;
                    if (o < total) pcm[o++] = (short) pred;
                }
            }
            pos += 1028;
        }
        System.out.println("sr=" + sr + " frames=" + frames + " 解出采样=" + o + " 时长=" + (o / (double) sr) + "s");
        // 找峰值，确认不是全 0
        int peak = 0;
        for (int i = 0; i < o; i++) { int v = Math.abs(pcm[i]); if (v > peak) peak = v; }
        System.out.println("峰值=" + peak);
        FileOutputStream fo = new FileOutputStream(a[1]);
        int dataLen = o * 2;
        fo.write(new byte[] { 'R', 'I', 'F', 'F' }); writeInt(fo, 36 + dataLen);
        fo.write(new byte[] { 'W', 'A', 'V', 'E', 'f', 'm', 't', ' ' }); writeInt(fo, 16);
        writeShort(fo, 1); writeShort(fo, 1); writeInt(fo, sr); writeInt(fo, sr * 2); writeShort(fo, 2); writeShort(fo, 16);
        fo.write(new byte[] { 'd', 'a', 't', 'a' }); writeInt(fo, dataLen);
        for (int i = 0; i < o; i++) writeShort(fo, pcm[i]);
        fo.close();
        System.out.println("写出 " + a[1] + " " + new File(a[1]).length() + " 字节");
    }

    static byte[] readAll(String p) throws IOException {
        File f = new File(p);
        byte[] b = new byte[(int) f.length()];
        DataInputStream in = new DataInputStream(new FileInputStream(f));
        in.readFully(b); in.close(); return b;
    }
}
