# -*- coding: utf-8 -*-
"""用大模型给「道」做一次音色总结，并把结论落成可用的参数。

输入（全部是实测/已有文件，不臆造）：
  1. 音色库.json  —— 8 个唱法模板（feats/唱法/放宽/blended_55）
  2. 音色池.json  —— 编配层的人声通道（少年声/自然声/戏曲腔/电音）
  3. 绮萱神经声库这一轮真实渲染的 37.6 s 试听 —— 现测 f0/音域/颤音/亮度/动态

输出：
  音色总结.md          —— 人读的总结（能用/不能用/边界/题材/缺口）
  音色应用.json        —— 段落级参数（前奏/主歌/预副歌/副歌/桥段/尾奏 的 bre/dyn/vib）
"""
import io
import json
import math
import os
import urllib.request

import numpy as np
import soundfile as sf

ROOT = r"F:\Daodao"
LIB = os.path.join(ROOT, r"tools\音乐\音色\音色库.json")
POOL = os.path.join(ROOT, r"自我状态\音色池.json")
SAMPLE = os.path.join(ROOT, r"曲库\麦子熟的时候_绮萱试听.wav")
KEY = open(os.path.join(ROOT, r"src\桌面分身\key.txt"), encoding="utf-8").read().strip()
API = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
MODEL = "glm-4-flash"
OUT_MD = os.path.join(ROOT, r"tools\音乐\音色\音色总结.md")
OUT_JSON = os.path.join(ROOT, r"tools\音乐\音色\音色应用.json")


def feats_of(x, sr):
    """粗测：f0 中位/音域/颤音率/颤音深度/频谱重心/动态。够用就好，不求学术精度。"""
    hop, win = int(0.02 * sr), int(0.04 * sr)
    f0s = []
    for i in range(0, len(x) - win, hop):
        seg = x[i:i + win]
        if np.sqrt((seg ** 2).mean()) < 0.01:
            continue
        seg = seg - seg.mean()
        ac = np.correlate(seg, seg, "full")[win - 1:]
        lo, hi = int(sr / 800), int(sr / 80)
        if hi >= len(ac):
            continue
        k = lo + int(np.argmax(ac[lo:hi]))
        if ac[k] > 0.3 * ac[0]:
            f0s.append(sr / k)
    f0s = np.array(f0s)
    semis = 12 * np.log2(f0s / np.median(f0s)) if len(f0s) else np.array([0])
    # 颤音：对半音曲线做 4–10 Hz 带内能量
    if len(semis) > 40:
        s = semis - semis.mean()
        sp = np.abs(np.fft.rfft(s, n=len(s) * 4))
        freqs = np.fft.rfftfreq(len(s) * 4, hop / sr)
        band = (freqs > 4) & (freqs < 10)
        depth = float(np.std(s)) * 2
        rate = float(freqs[band][np.argmax(sp[band])]) if band.any() else 0.0
    else:
        depth, rate = 0.0, 0.0
    sp = np.abs(np.fft.rfft(x[: sr * 10] * np.hanning(sr * 10)))
    fr = np.fft.rfftfreq(sr * 10, 1 / sr)
    centroid = float((sp * fr).sum() / (sp.sum() + 1e-9))
    frame = [np.sqrt((x[i:i + hop] ** 2).mean()) for i in range(0, len(x) - hop, hop)]
    db = 20 * np.log10(np.array(frame) + 1e-9)
    dyn = float(np.percentile(db, 95) - np.percentile(db, 10))
    return {"f0中位Hz": round(float(np.median(f0s)), 1) if len(f0s) else 0,
            "音域半音": round(float(np.percentile(semis, 95) - np.percentile(semis, 5)), 1),
            "颤音率Hz": round(rate, 2), "颤音深度semi": round(depth, 2),
            "频谱重心Hz": round(centroid, 0), "动态范围dB": round(dyn, 1)}


def ask(prompt):
    req = urllib.request.Request(
        API, data=json.dumps({"model": MODEL, "messages": [
            {"role": "system", "content": "你是「道」的音色档案管理员。只用给定数据说话，不编造，输出 JSON。"},
            {"role": "user", "content": prompt}], "temperature": 0.4, "max_tokens": 1200}).encode(),
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + KEY})
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.loads(r.read().decode("utf-8"))["choices"][0]["message"]["content"]


def main():
    lib = json.load(io.open(LIB, encoding="utf-8"))
    pool = json.load(io.open(POOL, encoding="utf-8"))
    x, sr = sf.read(SAMPLE, dtype="float32")
    if x.ndim > 1:
        x = x.mean(axis=1)
    mine = feats_of(x, sr)
    print("绮萱实测：", json.dumps(mine, ensure_ascii=False))

    profiles = {k: {"feats": v.get("feats"), "唱法": v.get("唱法"), "尾招": (v.get("唱法") or {}).get("尾招"),
                    "note": v.get("note", ""), "source": v.get("source", "")}
                for k, v in lib["profiles"].items()}
    voices = {v["名称"]: {"听感": v.get("听感"), "实现": v.get("实现"), "默认用在": v.get("默认用在")}
              for v in pool["人声"]}

    prompt = (
        "现场实测（绮萱 v2.7.0，神经声库，37.6 秒试听）：%s\n\n"
        "现有唱法模板（只取唱法特征、不做真人嗓音克隆）：%s\n\n"
        "编配层人声通道（这是老的电音/合成管线，已被用户否决，不能再用于成品）：%s\n\n"
        "任务：给「道」做一次音色总结，并对即将渲染的三分钟档新歌给出段落级参数。输出 JSON：\n"
        "{\"总结\":\"<=300字，说清现在能用的是什么声音、哪些不能用及原因、适用题材、还缺什么\","
        "\"可用音色\":[{\"名称\":\"绮萱\",\"定位\":\"...\",\"适用\":\"...\",\"边界\":\"...\"}],"
        "\"禁用\":[{\"名称\":\"...\",\"原因\":\"...\"}],"
        "\"段落参数\":{\"前奏\":{\"bre\":0-40,\"dyn\":0-30,\"vib_depth\":10-40,\"vib_len\":0-300},"
        "\"主歌\":{...},\"预副歌\":{...},\"副歌\":{...},\"桥段\":{...},\"尾奏\":{...}},"
        "\"缺口\":[\"<=20字\"]}"
        "要求：bre/dyn 是 OpenUtau 的 0~100 强度值（气声量/动态），vib_depth 单位是音分，vib_len 是音符时长的百分比(0-100)。"
        "参数必须结合实测特征（f0、颤音率、动态范围）给出，副歌要比主歌更实、更亮。"
    ) % (json.dumps(mine, ensure_ascii=False), json.dumps(profiles, ensure_ascii=False)[:2600],
         json.dumps(voices, ensure_ascii=False)[:900])

    txt = ask(prompt)
    txt = txt.replace("```json", "").replace("```", "").strip()
    if not txt.startswith("{"):
        txt = txt[txt.index("{"):txt.rindex("}") + 1]
    data = json.loads(txt)

    md = ["# 音色总结（%s）" % "2026-11-24", "",
          "## 一、结论", "", data.get("总结", ""), "",
          "## 二、能用的声音", ""]
    for v in data.get("可用音色", []):
        md.append("- **%s**：定位 %s；适用 %s；边界 %s" % (v.get("名称"), v.get("定位"), v.get("适用"), v.get("边界")))
    md += ["", "## 三、禁用的做法", ""]
    for v in data.get("禁用", []):
        md.append("- **%s**：%s" % (v.get("名称"), v.get("原因")))
    md += ["", "## 四、实测底数（绮萱 37.6 秒试听）", "",
           "`%s`" % json.dumps(mine, ensure_ascii=False), "",
           "## 五、缺口", ""]
    for g in data.get("缺口", []):
        md.append("- " + g)
    md += ["", "## 六、段落参数（直接喂给 make_song_v17.py）", "",
           "`%s`" % json.dumps(data.get("段落参数"), ensure_ascii=False), ""]
    io.open(OUT_MD, "w", encoding="utf-8").write("\n".join(md))
    io.open(OUT_JSON, "w", encoding="utf-8").write(json.dumps(
        {"实测": mine, "段落参数": data.get("段落参数"), "总结": data.get("总结"),
         "生成": "2026-11-24 音色总结.py"}, ensure_ascii=False, indent=2))
    print("写入", OUT_MD, "与", OUT_JSON)
    print(json.dumps(data.get("段落参数"), ensure_ascii=False))


if __name__ == "__main__":
    main()
