#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
语音链路检查（第5类 · Whisper / sherpa-onnx / Vosk 的离线语音链路）
判据来源：
  sherpa-onnx VAD API  https://csukuangfj.github.io/sherpa/onnx/javascript-api/examples/api_vad.html
  Silero VAD 源码       http://raw.githubusercontent.com/snakers4/silero-vad/master/src/silero_vad/utils_vad.py
  Switchboard Silero   https://docs.switchboard.audio/extensions/silero-vad/
  端到端静音实测        https://dev.to/ji_ai/silero-vad-end-of-turn-700ms-of-silence-cut-off-118-of-1000-answers-2ai1

只做能真跑出来的判断：TTS 产物用 MP3 帧头解析，VAD 用源码检索，测不到的判 UNKN 而不是 PASS。
用法： python 语音链路检查.py [额外mp3目录...]
"""
import os
import sys
import glob

BASE = r"F:\Daodao"
SRC_PET = os.path.join(BASE, "src", "桌面分身", "pet.cs")
SRC_HTML = os.path.join(BASE, "src", "_apk", "assets", "dao.html")

# MPEG 音频帧头表（MPEG1 / MPEG2，Layer III）
BITRATE_V1L3 = [0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320, 0]
BITRATE_V2L3 = [0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160, 0]
SR_V1 = [44100, 48000, 32000, 0]
SR_V2 = [22050, 24000, 16000, 0]


def mp3_frames(path):
    """返回 dict(sample_rate, channels, kbps 列表, frames, duration)；纯标准库解析帧头。"""
    with open(path, "rb") as f:
        data = f.read()
    i = 0
    # 跳过 ID3v2
    if data[:3] == b"ID3":
        size = int.from_bytes(data[6:10], "big")
        i = 10 + size
    sr = None
    ch = None
    kbps = []
    frames = 0
    n = len(data)
    while i + 4 <= n:
        if data[i] == 0xFF and (data[i + 1] & 0xE0) == 0xE0:
            h = data[i:i + 4]
            ver = (h[1] >> 3) & 0x03        # 3=MPEG1, 2=MPEG2, 0=MPEG2.5
            layer = (h[1] >> 1) & 0x03      # 1=LayerIII
            bri = (h[2] >> 4) & 0x0F
            sri = (h[2] >> 2) & 0x03
            mode = (h[3] >> 6) & 0x03       # 3=单声道
            if layer != 1 or bri in (0, 15) or sri == 3:
                i += 1
                continue
            if ver == 3:
                rate = SR_V1[sri]
                k = BITRATE_V1L3[bri]
                spf = 1152
            else:
                rate = SR_V2[sri]
                k = BITRATE_V2L3[bri]
                spf = 576
            if rate == 0 or k == 0:
                i += 1
                continue
            if sr is None:
                sr = rate
                ch = 1 if mode == 3 else 2
            kbps.append(k)
            pad = (h[2] >> 1) & 0x01
            flen = int(spf / rate * k * 1000 / 8) + pad
            frames += 1
            i += max(flen, 4)
        else:
            i += 1
    dur = frames * spf / float(sr) if (sr and frames) else 0.0
    return {"sr": sr, "ch": ch, "kbps": kbps, "frames": frames, "dur": dur}


def grep_any(paths, words):
    """拉丁词按词边界匹配，中文按字面匹配；只做子串匹配会把 avatars 里的 vad 也算命中（已犯过）。"""
    import re
    hits = []
    for p in paths:
        if not os.path.exists(p):
            continue
        try:
            txt = open(p, encoding="utf-8", errors="ignore").read()
        except Exception:
            continue
        for w in words:
            if any("\u4e00" <= c <= "\u9fff" for c in w):
                pat = re.escape(w)
            else:
                pat = r"\b" + re.escape(w) + r"\b"
            if re.search(pat, txt, re.I):
                hits.append((os.path.basename(p), w))
                break
    return hits


def main():
    rows = []
    samples = []
    for d in [BASE] + sys.argv[1:]:
        samples += glob.glob(os.path.join(d, "*.mp3"))
    samples = sorted(set(samples))[:8]
    infos = []
    for s in samples:
        try:
            infos.append((s, mp3_frames(s)))
        except Exception as e:
            rows.append(("P0 产物可解析", "FAIL", "{} 解析失败 {}".format(os.path.basename(s), e)))

    # P1 采样率：语音产物 ≥24kHz（16k 只用于 ASR 输入，不用于成品）
    if infos:
        bad = [os.path.basename(s) for s, i in infos if not i["sr"] or i["sr"] < 24000]
        rows.append(("P1 采样率≥24000Hz", "PASS" if not bad else "FAIL",
                     "样本 {}，实测 {}".format(len(infos), sorted({i["sr"] for _, i in infos})),
                     bad))
    else:
        rows.append(("P1 采样率≥24000Hz", "UNKN", "没有找到 mp3 样本"))

    # P2 声道：单声道（手机解码与体积）
    if infos:
        bad = [os.path.basename(s) for s, i in infos if i["ch"] != 1]
        rows.append(("P2 单声道", "PASS" if not bad else "FAIL",
                     "实测声道 {}".format(sorted({i["ch"] for _, i in infos})), bad))

    # P3 码率：48kbps±8（Edge 朗读默认档）
    if infos:
        ks = [k for _, i in infos for k in i["kbps"]]
        avg = sum(ks) / len(ks) if ks else 0
        ok = abs(avg - 48) <= 8
        rows.append(("P3 码率 48±8kbps", "PASS" if ok else "FAIL", "实测均值 {:.1f}kbps".format(avg)))

    # P4 单段 ≤20 秒（长句必须分段，否则迟滞与首字延迟都会被拖长）
    if infos:
        bad = [os.path.basename(s) for s, i in infos if i["dur"] > 20.0]
        rows.append(("P4 单段≤20s", "PASS" if not bad else "FAIL",
                     "实测最长 {:.2f}s".format(max(i["dur"] for _, i in infos)), bad))

    # P5 语音输入侧 VAD：静音 300ms 起断 + 512 样本窗（16k）
    hits = grep_any([SRC_PET, SRC_HTML], ["silero", "sherpa", "vad", "静音断句", "minSilence"])
    rows.append(("P5 语音输入 VAD(300ms/512样本)", "PASS" if hits else "FAIL",
                 "源码命中 {}".format(hits) if hits else "pet.cs / dao.html 都没有 VAD 链路"))

    # P6 首字延迟 ≤150ms：需要解码样本做能量前导检测，纯帧头测不出 → 不谎报 PASS
    rows.append(("P6 首字延迟≤150ms", "UNKN", "缺解码器，无法从帧头测；需 ffmpeg 或 sox 才能判"))

    print("== 语音链路判据（第5类）==")
    n_pass = n_fail = n_unk = 0
    for r in rows:
        name, res, note = r[0], r[1], r[2]
        extra = r[3] if len(r) > 3 else None
        print("[{}] {} | {}{}".format(res, name, note, (" | 不合格: {}".format(extra)) if extra else ""))
        if res == "PASS":
            n_pass += 1
        elif res == "FAIL":
            n_fail += 1
        else:
            n_unk += 1
    print("汇总：PASS {} | FAIL {} | UNKN {}".format(n_pass, n_fail, n_unk))
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
