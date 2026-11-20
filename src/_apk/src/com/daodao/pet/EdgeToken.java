package com.daodao.pet;

import java.math.BigInteger;
import java.nio.charset.StandardCharsets;

/**
 * Edge 朗读服务 Sec-MS-GEC v2 令牌 —— 完整移植版。
 *
 * 说明（踩过的坑）：这版令牌**不是**标准 SHA-256。
 * 它把首块的 14 轮预先折叠进一个定制初值，并改了第 15 个轮常量与两个 sigma 的调整量，
 * 所以「SHA256(56个0+数据)」算出来的值对不上（实测差整段）。
 * 这里按 edge_tts 的 drm.py 逐行等价移植，用 BigInteger 承接超过 64 位的中间量。
 *
 * 自检：与 Python 的 generate_sec_ms_gec_v2(固定时间戳) 逐字符比对。
 */
public class EdgeToken {

    static final String TRUSTED = "6A5AA1D4EAFF4E9FB37E23D68491D6F4";
    static final long WIN_EPOCH = 11644473600L;
    static final long M = 0xFFFFFFFFL;

    static final BigInteger BM = BigInteger.valueOf(M);
    static final BigInteger B32 = BigInteger.ONE.shiftLeft(32);

    static final long[] INITIAL = {0x6A09E667L, 0xBB67AE85L, 0x3C6EF372L, 0xA54FF53AL,
                                   0x510E527FL, 0x9B05688CL, 0x1F83D9ABL, 0x5BE0CD19L};
    static final long[] STATE0 = {0xFD9FBEA2L, 0x91243CE7L, 0xBE499094L, 0xCD2E1E0AL,
                                  0x6C006F49L, 0x04BD35ABL, 0xFEB0A7E4L, 0x03EFFBD2L};
    static final long[] SCHED = {0xEB24BF9EL, 0x1558691FL, 0xA0C09EE2L, 0x0CFA32BAL,
        0xA622EE8CL, 0xD1DD9491L, 0xC0DD25A0L, 0xF9E70AB6L,
        0xF0C31573L, 0x7058CE4EL, 0x7188E606L, 0x00E5AB33L,
        0xD258B060L, 0x72766564L};
    static final long[] ROUND = {0x428A2F98L, 0x71374491L, 0xB5C0FBCFL, 0xE9B5DBA5L,
        0x3956C25BL, 0x59F111F1L, 0x923F82A4L, 0xAB1C5ED5L, 0xD807AA98L, 0x12835B01L,
        0x243185BEL, 0x550C7DC3L, 0x72BE5D74L, 0x80DEB1FEL, 0x9BDC06A7L, 0xC19BF174L,
        0xE49B69C1L, 0xEFBE4786L, 0x0FC19DC6L, 0x240CA1CCL, 0x2DE92C6FL, 0x4A7484AAL,
        0x5CB0A9DCL, 0x76F988DAL, 0x983E5152L, 0xA831C66DL, 0xB00327C8L, 0xBF597FC7L,
        0xC6E00BF3L, 0xD5A79147L, 0x06CA6351L, 0x14292967L, 0x27B70A85L, 0x2E1B2138L,
        0x4D2C6DFCL, 0x53380D13L, 0x650A7354L, 0x766A0ABBL, 0x81C2C92EL, 0x92722C85L,
        0xA2BFE8A1L, 0xA81A664BL, 0xC24B8B70L, 0xC76C51A3L, 0xD192E819L, 0xD6990624L,
        0xF40E3585L, 0x106AA070L, 0x19A4C116L, 0x1E376C08L, 0x2748774CL, 0x34B0BCB5L,
        0x391C0CB3L, 0x4ED8AA4AL, 0x5B9CCA4FL, 0x682E6FF3L, 0x748F82EEL, 0x78A5636FL,
        0x84C87814L, 0x8CC70208L, 0x90BEFFFAL, 0xA4506CEBL, 0xBEF9A3F7L, 0xC67178F2L};
    static final long ADJ = 0xC9DC06A7L;
    static final long SIGMA0_ADJ = 0x059C0B80L;
    static final long SIGMA1_ADJ = 0x000B92C0L;

    static long sigma0(long v) {
        v &= M;
        return ((v >>> 7) ^ (v << 25) ^ (v >>> 18) ^ (v << 14) ^ (v >>> 3)) & M;
    }

    static long sigma1(long v) {
        v &= M;
        return ((v >>> 17) ^ (v << 15) ^ (v >>> 19) ^ (v << 13) ^ (v >>> 10)) & M;
    }

    static BigInteger bi(long v) { return BigInteger.valueOf(v & M); }

    static long[] rounds(long[] state, long[] words, int firstRound) {
        BigInteger a = bi(state[0]), b = bi(state[1]), c = bi(state[2]), d = bi(state[3]),
                   e = bi(state[4]), f = bi(state[5]), g = bi(state[6]), h = bi(state[7]);
        long[] constants = (firstRound == 14) ? blockConstants() : ROUND;
        int aligned = Math.min(64, ((firstRound + 7) / 8) * 8);
        final BigInteger K = BigInteger.valueOf(0x100000001L);

        for (int i = firstRound; i < aligned; i++) {
            BigInteger rotE = e.multiply(K);
            BigInteger rotA = a.multiply(K);
            BigInteger t1 = h
                .add(rotE.shiftRight(6).xor(rotE.shiftRight(11)).xor(rotE.shiftRight(25)))
                .add(g.xor(e.and(f.xor(g))))
                .add(bi(constants[i]))
                .add(bi(words[i]));
            BigInteger t2 = rotA.shiftRight(2).xor(rotA.shiftRight(13)).xor(rotA.shiftRight(22))
                .add(a.and(b).or(c.and(a.or(b))));
            BigInteger na = t1.add(t2).and(BM);
            BigInteger ne = d.add(t1).and(BM);
            // 一次 8 轮，寄存器顺序回到原位
            h = g; g = f; f = e; e = ne; d = c; c = b; b = a; a = na;
        }
        for (int i = aligned; i < 64; i += 8) {
            long[] idx = {i, i + 1, i + 2, i + 3, i + 4, i + 5, i + 6, i + 7};
            BigInteger tmp;
            // 逐轮：d += t1; h = t1 + t2
            for (int r = 0; r < 8; r++) {
                BigInteger rotE = e.multiply(K);
                BigInteger rotA = a.multiply(K);
                BigInteger t1 = h
                    .add(rotE.shiftRight(6).xor(rotE.shiftRight(11)).xor(rotE.shiftRight(25)))
                    .add(g.xor(e.and(f.xor(g))))
                    .add(bi(constants[(int) idx[r]]))
                    .add(bi(words[(int) idx[r]]));
                BigInteger t2 = rotA.shiftRight(2).xor(rotA.shiftRight(13)).xor(rotA.shiftRight(22))
                    .add(a.and(b).or(c.and(a.or(b))));
                d = d.add(t1).and(BM);
                BigInteger nh = t1.add(t2).and(BM);
                // 轮换寄存器（等价于 python 里那一串显式赋值）
                BigInteger oldD = d;
                d = c; c = b; b = a; a = nh;
                h = g; g = f; f = e; e = oldD;
            }
        }
        return new long[]{a.longValue() & M, b.longValue() & M, c.longValue() & M, d.longValue() & M,
                          e.longValue() & M, f.longValue() & M, g.longValue() & M, h.longValue() & M};
    }

    static long[] blockConstants() {
        long[] b = new long[64];
        for (int i = 0; i < 14; i++) b[i] = ROUND[i];
        b[14] = ADJ;
        for (int i = 15; i < 64; i++) b[i] = ROUND[i];
        return b;
    }

    static void expand(long[] words, int firstWord) {
        for (int i = firstWord; i < 64; i++) {
            long x = words[i - 2], y = words[i - 15];
            long s1 = ((x >>> 17) ^ (x << 15) ^ (x >>> 19) ^ (x << 13) ^ (x >>> 10));
            long s0 = ((y >>> 7) ^ (y << 25) ^ (y >>> 18) ^ (y << 14) ^ (y >>> 3));
            words[i] = (s1 + words[i - 7] + s0 + words[i - 16]) & M;
        }
    }

    static long[] sha256Init(byte[] head7) {
        long[] words = new long[64];
        words[14] = ((head7[0] & 0xFFL) << 16) | ((head7[1] & 0xFFL) << 8) | (head7[2] & 0xFFL);
        words[15] = ((head7[3] & 0xFFL) << 24) | ((head7[4] & 0xFFL) << 16)
                  | ((head7[5] & 0xFFL) << 8) | (head7[6] & 0xFFL);
        for (int i = 16; i < 30; i++) {
            long value = SCHED[i - 16];
            if (i - 2 >= 14) value += (i == 16 ? (sigma1(words[i - 2]) ^ SIGMA1_ADJ) : sigma1(words[i - 2]));
            if (i - 7 >= 14) value += words[i - 7];
            if (i - 15 >= 14) value += (i == 29 ? (sigma0(words[i - 15]) ^ SIGMA0_ADJ) : sigma0(words[i - 15]));
            words[i] = value & M;
        }
        words[30] = (sigma1(words[28]) + words[23] + sigma0(words[15]) + words[14] + ADJ - ROUND[14]) & M;
        expand(words, 31);
        long[] working = rounds(STATE0, words, 14);
        long[] out = new long[8];
        for (int i = 0; i < 8; i++) out[i] = (INITIAL[i] + working[i]) & M;
        return out;
    }

    static byte[] sha256Digest(byte[] data) {
        int len = data.length;
        if (len < 7) throw new IllegalArgumentException("need >=7 bytes");
        int total = 57 + len;
        int padLen = (55 - total) % 64;
        if (padLen < 0) padLen += 64;
        byte[] padded = new byte[(len - 7) + 1 + padLen + 8];
        System.arraycopy(data, 7, padded, 0, len - 7);
        padded[len - 7] = (byte) 0x80;
        long bits = ((long) total) * 8;
        for (int i = 0; i < 8; i++) {
            padded[padded.length - 1 - i] = (byte) ((bits >>> (8 * i)) & 0xFF);
        }
        long[] state = sha256Init(new byte[]{data[0], data[1], data[2], data[3], data[4], data[5], data[6]});
        for (int off = 0; off + 64 <= padded.length; off += 64) {
            long[] words = new long[64];
            for (int i = 0; i < 16; i++) {
                int o = off + i * 4;
                words[i] = ((padded[o] & 0xFFL) << 24) | ((padded[o + 1] & 0xFFL) << 16)
                         | ((padded[o + 2] & 0xFFL) << 8) | (padded[o + 3] & 0xFFL);
            }
            expand(words, 16);
            long[] working = rounds(state, words, 0);
            for (int i = 0; i < 8; i++) state[i] = (state[i] + working[i]) & M;
        }
        byte[] out = new byte[32];
        for (int i = 0; i < 8; i++) {
            out[i * 4] = (byte) ((state[i] >>> 24) & 0xFF);
            out[i * 4 + 1] = (byte) ((state[i] >>> 16) & 0xFF);
            out[i * 4 + 2] = (byte) ((state[i] >>> 8) & 0xFF);
            out[i * 4 + 3] = (byte) (state[i] & 0xFF);
        }
        return out;
    }

    static long rol16(long v) { v &= M; return ((v << 16) | (v >>> 16)) & M; }

    static long u32(long v) { return v & M; }

    static final long[] COEF_A = {0xE82E91B1L, 0x44DE24C6L, 0x3BEB65BCL, 0xC89C5933L, 0x8D1EC211L,
        0x314EF5D5L, 0xE92491B1L, 0xF0A5B9D5L, 0x06064CF3L, 0xDA79FA60L,
        0xBED20560L, 0x89F9C9F8L, 0x35FA38C6L, 0xCB49E3C6L};
    static final long[] COEF_B = {0xB32700D0L, 0x88DFF51DL, 0x29514038L, 0xB328CBDFL, 0xD405B4D5L,
        0x26E55F3CL, 0x607801C6L, 0x82B2C1FBL, 0xFA51A3DAL, 0x207CC464L,
        0x3C3C74F3L, 0xD2D14B61L, 0xBB04A2C1L, 0xC5626167L};
    static final long CS_FACTOR = 0x82893933L;
    static final long ADJ0 = 0xF2F90B1AL;
    static final long ADJ1 = 0x0B1A0000L;

    static long[] wordsLe4Even(byte[] data) {
        byte[] b = new byte[data.length + 1];
        System.arraycopy(data, 0, b, 1, data.length);
        int pad = (4 - (b.length % 4)) % 4;
        byte[] p = new byte[b.length + pad];
        System.arraycopy(b, 0, p, 0, b.length);
        int n = p.length / 4;
        if (n % 2 == 1) n++;
        long[] w = new long[n];
        for (int i = 0; i < p.length / 4; i++) {
            int o = i * 4;
            w[i] = (p[o] & 0xFFL) | ((p[o + 1] & 0xFFL) << 8)
                 | ((p[o + 2] & 0xFFL) << 16) | ((p[o + 3] & 0xFFL) << 24);
        }
        return w;
    }

    static long[] cs64(byte[] data, byte[] digest) {
        long keyA = ((digest[0] & 0xFFL) | ((digest[1] & 0xFFL) << 8)
                  | ((digest[2] & 0xFFL) << 16) | ((digest[3] & 0xFFL) << 24)) | 1L;
        long keyB = ((digest[4] & 0xFFL) | ((digest[5] & 0xFFL) << 8)
                  | ((digest[6] & 0xFFL) << 16) | ((digest[7] & 0xFFL) << 24)) | 1L;
        long[] factors = {u32(keyA * CS_FACTOR), u32(keyB * CS_FACTOR)};

        long[] w = wordsLe4Even(data);
        int total = 14 + w.length;
        long[] terms = new long[total];
        long[] offs = new long[total];
        for (int i = 0; i < 14; i++) {
            terms[i] = u32(COEF_A[i] * factors[i % 2]);
            offs[i] = COEF_B[i];
        }
        for (int i = 0; i < w.length; i++) {
            long word = w[i];
            long term = u32(word * (i % 2 == 0 ? keyA : keyB));
            long off = u32(rol16(word) * (i % 2 == 0 ? 0xEF0569FBL : 0xC31713DBL));
            if (i == 0) {
                term = u32(term + u32(ADJ0 * factors[0]));
                off = u32(off + ADJ1);
            }
            terms[14 + i] = term;
            offs[14 + i] = off;
        }
        long swapAcc = 0, swapLast = 0, state = 0, acc = 0;
        for (int i = 0; i + 1 < total; i += 2) {
            long x = terms[i], y = terms[i + 1];
            long t = rol16(u32(offs[i] + x));
            long q = u32(t * 0x76F50F34L);
            swapAcc = u32(swapAcc + u32(rol16(q) * 0xC3EFEA97L + q));
            t = rol16(u32(offs[i + 1] + y));
            q = u32(t * 0x1881CE3CL);
            swapLast = u32((rol16(q) * 0x35BD1EC9L) + q);
            swapAcc = u32(swapAcc + swapLast);

            state = u32(state * keyA + x);
            state = u32(rol16(state) * 0xCF98B111L);
            state = u32(rol16(state) * 0x87085B9FL);
            state = u32(rol16(state) * 0x12CEB96DL);
            state = u32(rol16(state) * 0x257E1D83L);
            acc = u32(acc + state);
            t = u32(state * keyB + y);
            t = u32(rol16(t) * 0xA27416F5L);
            t = u32(rol16(t) * 0xD38396FFL);
            state = u32(rol16(u32(rol16(t) * 0x7C932B89L)) * 0xBFA49F69L);
            acc = u32(acc + state);
        }
        return new long[]{swapLast ^ state, swapAcc ^ acc};
    }

    static String hexUpper(byte[] b) {
        StringBuilder sb = new StringBuilder();
        for (byte x : b) sb.append(String.format("%02X", x));
        return sb.toString();
    }

    static byte[] w2b(long v) {
        return new byte[]{(byte) (v & 0xFF), (byte) ((v >>> 8) & 0xFF),
                          (byte) ((v >>> 16) & 0xFF), (byte) ((v >>> 24) & 0xFF)};
    }

    static String le(byte[] b) {
        // b 已经是小端字节序列，按原序拼 hex 就是 Python 那边的排版
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < b.length; i++) sb.append(String.format("%02X", b[i]));
        return sb.toString();
    }

    public static String gec(long unixSec) {
        double ts = (unixSec > 0) ? (double) unixSec : (double) (System.currentTimeMillis() / 1000);
        long ticks = (long) (ts + WIN_EPOCH);
        ticks -= ticks % 300;
        long ns = ticks * 10000000L;
        String data = ns + TRUSTED;
        byte[] d = data.getBytes(StandardCharsets.US_ASCII);
        byte[] digest = sha256Digest(d);
        long[] cs = cs64(d, digest);
        // Python 端是 struct.pack("<II") 再取 hex，也就是单字按小端排版，这里要跟齐
        return le(w2b(cs[0])) + le(w2b(cs[1])) + "-" + hexUpper(digest);
    }

    public static void main(String[] a) {
        long ts = a.length > 0 ? Long.parseLong(a[0]) : 0L;
        System.out.println(gec(ts));
    }
}
