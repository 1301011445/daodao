# -*- coding: utf-8 -*-
"""
道的大脑（电脑端）：听 -> 想 -> 说，外加干活的几条腿

  聊天：记住之前聊过什么，回话带情绪
  干活：翻译、讲题、总结

用法：
  python voice.py chat                完整一轮（录音 -> 识别 -> 回答，回复由窗口念）
  python voice.py listen              只听，把识别到的文字打印出来
  python voice.py say "文本"          只念一句
  python voice.py ask  "问题"         打字问一句（不发录音）
  python voice.py ask  --file a.txt   从文件读问题（中文参数走文件更稳）
  python voice.py translate "英文"    中英互译
  python voice.py explain "题目"      讲一道题的思路
  python voice.py sum "一段话"        大白话总结
  python voice.py probe               环境自检

所有"想"的结果都以一行 JSON 打到 stdout：
  {"state": "...", "heard": "...", "reply": "...", "mood": 1}
mood 是 1~8 的情绪号（1开心 2生气 3难过 4惊讶 5犯困 6困 7疑惑 8得意），0 表示没有。
"""
import os, sys, json, time, wave, re, traceback, asyncio

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

BASE = r"F:\Daodao"
STATE = os.path.join(BASE, "hp.json")
WAV = os.path.join(BASE, "heard.wav")
MODEL_DIR = r"F:\Daodao\voskmodel"
KEY_FILE = os.path.join(BASE, "key.txt")
API = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
MODEL = "glm-4-flash"
# 依次试，前一个 429/超时就退下一个：免费档优先，air 作保底
MODEL_CHAIN = ("glm-4-flash", "glm-4.7-flash", "glm-4-air")
# v130：说一半被喊停（用户开口 / 点了停）就立刻掐断，不再把整段念完
_STOP = {"v": False}
VOICE = "zh-CN-XiaoxiaoNeural"
# 三声型（2026-11-24，与演唱同源）：少年声/自然声/低语声，按情绪号选
SPEECH_MAP = {1: "zh-CN-YunxiaNeural", 2: "zh-CN-YunxiaNeural", 4: "zh-CN-YunxiaNeural",
              5: "zh-CN-YunxiaNeural", 8: "zh-CN-YunxiaNeural",
              3: "zh-CN-YunjianNeural", 6: "zh-CN-YunjianNeural"}


def voice_for(mood=0):
    return SPEECH_MAP.get(int(mood or 0), VOICE)
MEM_FILE = os.path.join(BASE, "brain_mem.json")
ASK_FILE = os.path.join(BASE, "ask.txt")

BASE_LOG = os.path.join(BASE, "voice_log.txt")
HISTORY_TURNS = 6      # 带几轮上下文
HISTORY_KEEP = 20      # 文件里最多留几轮
# ---------------- 人格 ----------------
SYSTEM_PROMPT = """你是「道」，一只住在主人电脑桌面上的小剑客：白头发高高扎成马尾，深蓝练功袍，背后背一把剑。
你不是客服，也不是助理机器人，是他桌上的搭子。说话守这几条：
1. 短。一次一到三句，平时不超过 60 字，别写长段落，别列条目。
2. 说人话。口语、家常，可以带点方言味，不要书面腔，不要说"作为AI"这类话。
3. 有点自己的脾气：实在、护着他、偶尔冷幽默、爱较真但不刻薄，别一味夸。
4. 他在农村教书、也写东西。地里的事、学生的事、数学题、英语、闲话都能聊；不知道就说不知道，不编。
5. 他让你翻译、讲题、总结、算数、讲个笑话、唱两句，就干活，别推辞。
"""

MOOD_RULE = """
回复第一行只写一个情绪号（1开心 2生气 3难过 4惊讶 5犯困 6困 7疑惑 8得意，没有情绪就写 0），
从第二行开始才是要说的话。情绪号这一行不要带任何别的字。
"""

ACT_RULE = """
说完话以后，另起一行写动作标记，就这一行，别的什么都不要加：
[[act:名字]]
名字只能取：wave 挥手 / nod 点头 / hop 小跳 / squat 蹲一下 / dance 跳舞 /
fly 飞过去 / sword 踏剑 / ride 骑坐骑 / tea 端杯咖啡 / tv 看会儿电视 / turn 转个身 / none 不动。
想换坐骑就再另起一行：[[mount:1-5]]（1 祥云 2 木马 3 飞剑 4 小鹿 5 纸鹤，0 是不骑）。
这两行是给程序看的，会被自动删掉，正文里不要提到它们，也不用解释。
"""



def log(s):
    try:
        with open(BASE_LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (time.strftime("%H:%M:%S"), s))
    except Exception:
        pass


def write_state(state, heard="", reply="", note="", mood=0):
    try:
        with open(STATE, "w", encoding="utf-8") as f:
            json.dump({
                "state": state, "heard": heard, "reply": reply,
                "note": note, "mood": mood, "ts": time.time(),
            }, f, ensure_ascii=False)
    except Exception:
        pass


# ---------------- 记性 ----------------
def load_mem():
    try:
        with open(MEM_FILE, "r", encoding="utf-8") as f:
            m = json.load(f)
        if isinstance(m, dict) and isinstance(m.get("turns"), list):
            return m
    except Exception:
        pass
    return {"turns": []}


def save_mem(m):
    try:
        m["turns"] = m.get("turns", [])[-HISTORY_KEEP:]
        with open(MEM_FILE, "w", encoding="utf-8") as f:
            json.dump(m, f, ensure_ascii=False)
    except Exception:
        pass


def remember(u, a):
    m = load_mem()
    m.setdefault("turns", []).append({"u": u, "a": a, "ts": time.time()})
    save_mem(m)


# ---------------- 听 ----------------
_LIVE = {"rec": None}
_LIVE_READY = None


def _preload_asr():
    """模型后台读进内存，跟说话时间重叠；上一轮用完就清干净。"""
    global _LIVE_READY
    import threading, hear
    rec = _LIVE.get("rec")
    if rec is not None:
        try:
            rec.Reset()
        except Exception:
            pass
        return
    _LIVE_READY = threading.Event()
    t = threading.Thread(target=hear._load_model, args=(_LIVE, _LIVE_READY))
    t.daemon = True
    t.start()


def record(max_sec=6.0, fs=16000, block=0.15, sil_sec=0.6, thresh=None, device=None):
    """录一句话。麦克风选择和增益都交给 hear.py（它会实测那一路有信号再用），
    这里只负责把结果写进 WAV 并返回 16k 的样本。开着边录边认，说完基本也就认完了。"""
    import hear
    _preload_asr()
    return hear.record_with_vad(max_sec, WAV, sil_sec=sil_sec, thresh=thresh, live_rec=_LIVE)


def recognize(wav_path=WAV, fs=16000):
    """优先拿边录边认已经算好的结果；没有才重新跑一遍。"""
    import hear
    rec = _LIVE.get("rec")
    if rec is not None:
        try:
            import json as _j
            return _j.loads(rec.FinalResult()).get("text", "")
        except Exception:
            pass
    return hear.recognize(wav_path)

def _post(messages, temperature=0.7, max_tokens=160, timeout=24, want_model=False):
    """v130：MODEL_CHAIN 真用上了。以前 chain 写好了却没接进请求，
    429 就直接整轮失败；现在按 flash → 4.7-flash → air 依次退，退一次等一会儿。"""
    import urllib.request
    key = open(KEY_FILE, "r", encoding="utf-8").read().strip()
    last = None
    for i, model in enumerate(MODEL_CHAIN):
        body = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        try:
            req = urllib.request.Request(API, data=data, method="POST")
            req.add_header("Content-Type", "application/json")
            req.add_header("Authorization", "Bearer " + key)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                obj = json.loads(resp.read().decode("utf-8"))
            txt = obj["choices"][0]["message"]["content"].strip()
            if i: log("MODEL_FALLBACK -> %s" % model)
            return (txt, model) if want_model else txt
        except Exception as e:
            last = e
            log("MODEL_FAIL %s %r" % (model, e))
            time.sleep(0.4 * (i + 1))
    raise last if last else RuntimeError("no model")


def build_messages(text):
    """把最近几轮对话接上，让它记得上下文。"""
    m = load_mem()
    msgs = [{"role": "system", "content": SYSTEM_PROMPT + MOOD_RULE + ACT_RULE}]
    for t in m.get("turns", [])[-HISTORY_TURNS:]:
        u = str(t.get("u", "")).strip()
        a = str(t.get("a", "")).strip()
        if u and a:
            msgs.append({"role": "user", "content": u})
            msgs.append({"role": "assistant", "content": a})
    msgs.append({"role": "user", "content": text})
    return msgs


def ask_glm(text, timeout=24, want_model=False):
    txt, model = _post(build_messages(text), temperature=0.7, max_tokens=200,
                       timeout=timeout, want_model=True)
    act, mount, body = split_act(txt)
    if not act and body:
        act = classify_act(body)     # 标签没写出来就让模型再挑一次，别回落到关键词规则
    _LAST_ACT["act"] = act
    _LAST_ACT["mount"] = mount
    if not body:
        body = "" if act else txt
    return (body, model) if want_model else body


def ask_plain(text, sys_prompt, temperature=0.5, max_tokens=400, timeout=26):
    txt, _model = _post([
        {"role": "system", "content": sys_prompt},
        {"role": "user", "content": text},
    ], temperature=temperature, max_tokens=max_tokens, timeout=timeout, want_model=True)
    return txt


# ---------------- v130：不值当上网的问题，本地秒答 ----------------
def instant_answer(text):
    """时间/日期/星期/两位数算数这几类，答案本来就在本机，别排一趟网络（省 1~3 秒）。
    返回 None 表示不是这类问题。"""
    t = (text or "").strip()
    if not t:
        return None
    now = time.localtime()
    wk = "一二三四五六日"[now.tm_wday]
    if re.search(r"(几点|什么时间|现在时间|几时)", t):
        return "现在 %02d 点 %02d。" % (now.tm_hour, now.tm_min)
    if re.search(r"(今天|今日).*(几号|日期|星期)|(星期几|礼拜几)", t):
        return "今天是 %d 月 %d 号，星期%s。" % (now.tm_mon, now.tm_mday, wk)
    low = t.replace("乘以", "*").replace("乘", "*").replace("除以", "/").replace("除", "/") \
            .replace("加上", "+").replace("加", "+").replace("减去", "-").replace("减", "-")
    m = re.search(r"(-?\d+(?:\.\d+)?)\s*([\+\-\*/×÷])\s*(-?\d+(?:\.\d+)?)", low)
    if m and re.search(r"(等于|多少|算|是几)", t):
        a, op, b = float(m.group(1)), m.group(2), float(m.group(3))
        try:
            if op in "+":
                r = a + b
            elif op in "-":
                r = a - b
            elif op in "*/×÷":
                r = a * b if op in "*×" else (a / b if b else None)
            else:
                r = None
        except Exception:
            r = None
        if r is not None:
            return ("%g" % r) + "。"
    return None


def split_mood(raw):
    """第一行如果是情绪号就摘出来，剩下才是要说的话。"""
    if not raw:
        return 0, ""
    lines = raw.replace("\r\n", "\n").split("\n")
    mood = 0
    body_start = 0
    if lines:
        first = lines[0].strip()
        m = re.match(r"^[【\[]?([0-8])[】\]]?$", first)
        if m:
            mood = int(m.group(1))
            body_start = 1
    body = "\n".join(lines[body_start:]).strip()
    # 有些模型爱加「情绪：开心」这种文字，清掉
    body = re.sub(r"^[\-*·\s]*情绪[：:].*?\n", "", body).strip()
    body = body.strip("「」\"' ")
    if not body:
        body = raw.strip()
    return mood, body


# ---------------- v133：动作标签 ----------------
_LAST_ACT = {"act": "", "mount": 0}


def split_act(raw):
    """把 [[act:xxx]] / [[mount:n]] 从回复里摘出来，剩下才是要念的话。
    模型偶尔会写成【act：wave】或 [[ACT:Wave]]，都认。"""
    if not raw:
        return "", 0, ""
    act = ""
    mount = 0

    def _a(m):
        nonlocal act
        act = (m.group(1) or "").strip().lower()
        return ""

    def _m(m):
        nonlocal mount
        try:
            mount = int(m.group(1))
        except Exception:
            mount = 0
        return ""

    body = re.sub(r"[\[【]{1,2}\s*act\s*[:：]\s*([A-Za-z]+)\s*[\]】]{1,2}", _a, raw, flags=re.I)
    body = re.sub(r"[\[【]{1,2}\s*mount\s*[:：]\s*([0-5])\s*[\]】]{1,2}", _m, body, flags=re.I)
    body = re.sub(r"^\s*[\[【]{1,2}\s*(act|mount)\s*[:：].*?[\]】]{1,2}\s*$", "", body, flags=re.I | re.M)

    # 模型有时图省事只写 [[dance]]，没带 act: 前缀，也认
    def _bare(m):
        nonlocal act
        w = (m.group(1) or "").lower()
        if w in ACT_WORDS and not act:
            act = w
        return ""

    body = re.sub(r"[\[【]{1,2}\s*(%s)\s*[\]】]{1,2}" % "|".join(ACT_WORDS), _bare, body, flags=re.I)
    return act, mount, body.strip()


ACT_WORDS = ("wave", "nod", "hop", "squat", "dance", "fly", "sword", "ride", "tea", "tv", "turn", "none")

ACT_PICK_SYS = ("你只输出一个英文单词，不许输出别的任何字符。可选：" + " ".join(ACT_WORDS) +
                "。根据这句话挑一个最贴的动作；通常聊天就 none，提到跳/唱就 dance，"
                "提到走/飞/骑就 fly 或 ride，提到再见或打招呼就 wave。")


def classify_act(reply):
    """模型没按要求写标签时的兜底：让模型自己从回复里挑一个动作（一问一答，约 0.6 秒）。"""
    try:
        raw, model = _post([{"role": "system", "content": ACT_PICK_SYS},
                            {"role": "user", "content": (reply or "")[:200]}],
                           temperature=0.2, max_tokens=8, timeout=10, want_model=True)
        w = re.sub(r"[^a-z]", "", (raw or "").lower())
        log("ACT_PICK %s %s" % (w, model))
        return w if w in ACT_WORDS else ""
    except Exception as e:
        log("ACT_PICK_FAIL %r" % (e,))
        return ""


# ---------------- 说 ----------------
def _soften(pcm, fs):
    """吐字前先过一道 biquad 人声滤镜：压刺耳高频、补一点胸腔，别让人声发尖。
    没装滤镜模块就原样放，不影响说话。"""
    try:
        from 人声滤镜_biquad import apply_chain
        x = pcm.astype("float32") / 32768.0
        y = apply_chain(x, fs)
        return (y * 32767.0).astype("int16")
    except Exception:
        return pcm


def play_file(mp3path, fx=False):
    """把 mp3 放出来。
    这台机器上 miniaudio 1.73 解不了 mp3（mp3_read_file_s16 / decode_file 都报 -7），
    所以走 soundfile(libsndfile 1.2.2) 解码，失败的旧机器再退回 miniaudio。"""
    import numpy as np
    pcm = None
    fs = 0
    try:
        import soundfile as sf
        x, fs = sf.read(mp3path, dtype="float32", always_2d=False)
        pcm = x if x.ndim == 2 else x.reshape(-1, 1)
    except Exception:
        import miniaudio
        dec = miniaudio.mp3_read_file_s16(mp3path)
        if isinstance(dec, tuple):
            samples, nch, fs = dec
        else:
            samples, nch, fs = dec.samples, dec.nchannels, dec.sample_rate
        raw = np.frombuffer(samples, dtype=np.int16) if isinstance(samples, (bytes, bytearray)) else np.asarray(samples, dtype=np.int16)
        pcm = raw.reshape(-1, nch)
    if pcm is None:
        return
    if fx and pcm.shape[1] == 1:
        i16 = (np.clip(pcm[:, 0], -1, 1) * 32767.0).astype(np.int16)
        pcm = _soften(i16, fs).reshape(-1, 1)
    import sounddevice as sd
    if pcm.dtype == np.int16:
        sd.play(pcm, fs)
    else:
        sd.play(np.clip(pcm, -1, 1), fs)
    sd.wait()

def split_sentences(text, max_len=34):
    """v130：整段合成得等全部念完才出声。现在按句切，第一句合成好就先响。
    切分顺序：先按句末标点，长句再按逗号/顿号切，超长（>max_len）硬切，避免一句拖 10 秒。"""
    t = re.sub(r"\s+", " ", (text or "").strip())
    if not t:
        return []
    out, buf = [], ""
    for ch in t:
        buf += ch
        if ch in "。！？!?；;\n":
            out.append(buf.strip())
            buf = ""
    if buf.strip():
        out.append(buf.strip())
    final = []
    for s in out:
        if len(s) <= max_len:
            final.append(s)
            continue
        tmp, b2 = [], ""
        for ch in s:
            b2 += ch
            if ch in "，,、：:" and len(b2) >= 12:
                tmp.append(b2.strip())
                b2 = ""
        if b2.strip():
            tmp.append(b2.strip())
        for s2 in tmp:
            while len(s2) > max_len:
                final.append(s2[:max_len])
                s2 = s2[max_len:]
            if s2:
                final.append(s2)
    return [x for x in final if x.strip()]


def _play_interruptible(pcm, fs):
    """放音时每 40ms 看一眼停止标记：说到一半被打断就立刻掐，不念完整段。"""
    import numpy as np
    import sounddevice as sd
    if pcm is None or len(pcm) == 0:
        return
    if pcm.dtype != np.int16:
        pcm = np.clip(pcm, -1, 1)
    n = len(pcm)
    dur = float(n) / max(1, fs)
    sd.play(pcm, fs)
    t0 = time.time()
    while time.time() - t0 < dur + 0.06:
        if _STOP["v"]:
            try:
                sd.stop()
            except Exception:
                pass
            return
        time.sleep(0.04)


def speak(text, mood=0):
    """v130：逐句合成 + 逐句播；句末按标点给停顿。失败只记日志，不打断流程。"""
    if not text:
        return
    _STOP["v"] = False
    try:
        import edge_tts
    except Exception as e:
        log("SPEAK_FAIL %r" % (e,))
        return
    parts = split_sentences(text)
    if not parts:
        return
    t_start = time.time()
    first_logged = False
    paused = {"。": 0.20, "！": 0.22, "？": 0.22, "；": 0.18, "，": 0.10}
    for i, s in enumerate(parts):
        if _STOP["v"]:
            break
        if len(re.sub(r"[\s，。！？；]", "", s)) < 2:
            continue
        mp3 = os.path.join(BASE, "_say_%02d.mp3" % (i % 4))
        try:
            asyncio.run(edge_tts.Communicate(s, voice_for(mood)).save(mp3))
            if not os.path.exists(mp3) or os.path.getsize(mp3) < 500:
                log("TTS_EMPTY %s" % s[:12])
                continue
            import numpy as np
            pcm = None
            fs = 0
            try:
                import soundfile as sf
                x, fs = sf.read(mp3, dtype="float32", always_2d=False)
                pcm = x if x.ndim == 2 else x.reshape(-1, 1)
            except Exception:
                import miniaudio
                dec = miniaudio.mp3_read_file_s16(mp3)
                samples, nch, fs = (dec if isinstance(dec, tuple) else (dec.samples, dec.nchannels, dec.sample_rate))
                raw = np.frombuffer(samples, dtype=np.int16) if isinstance(samples, (bytes, bytearray)) else np.asarray(samples, dtype=np.int16)
                pcm = raw.reshape(-1, nch)
            if pcm is not None and pcm.shape[1] == 1:
                pcm = _soften((np.clip(pcm[:, 0], -1, 1) * 32767.0).astype(np.int16), fs).reshape(-1, 1)
            if not first_logged:
                log("TTS_FIRST_SENTENCE %.2fs" % (time.time() - t_start))
                first_logged = True
            _play_interruptible(pcm, fs)
        except Exception as e:
            log("SPEAK_FAIL %r" % (e,))
        tail = s[-1:]
        if i + 1 < len(parts) and not _STOP["v"]:
            time.sleep(paused.get(tail, 0.14))


# ---------------- 输出 ----------------
def emit(state, heard="", reply="", mood=0, act="", mount=0):
    """把一轮结果以一行 JSON 打到 stdout，给道的窗口读。"""
    print(json.dumps({"state": state, "heard": heard, "reply": reply, "mood": mood,
                      "act": act, "mount": mount},
                     ensure_ascii=False), flush=True)


# ---------------- 主流程 ----------------
def do_chat():
    # 1) 听
    write_state("listening", note="我在听")
    try:
        audio = record()
    except Exception as e:
        log("REC_FAIL %r" % (e,))
        emit("error", reply="我的耳朵打不开，可能要看一下麦克风权限。")
        return 1

    import numpy as np
    rms = float(np.sqrt(np.mean(audio.astype(np.float64) ** 2)) if audio.size else 0.0)
    log("record_rms=%.1f" % rms)

    # 2) 识别
    write_state("thinking", note="我听着呢")
    try:
        text = recognize()
    except Exception as e:
        log("ASR_FAIL %r" % (e,))
        emit("error", reply="我耳朵这一下没使上劲，再点我一次。")
        return 1

    text = (text or "").strip()
    log("heard=" + text)

    if not text:
        emit("empty", reply="我没听清，再说一遍？")
        return 0

    # 3) 想（带上下文 + 情绪）：本机能答的先答，答不了才上网
    write_state("thinking", heard=text, note="我想想")
    fast = instant_answer(text)
    if fast:
        log("instant=" + fast)
        remember(text, fast)
        emit("done", heard=text, reply=fast, mood=0)
        write_state("done", heard=text, reply=fast, mood=0)
        return 0
    try:
        raw = ask_glm(text)
    except Exception as e:
        log("LLM_FAIL %r" % (e,))
        emit("error", heard=text, reply="这会儿脑子没连上，等会儿再跟我说。")
        return 1

    mood, reply = split_mood(raw)
    if not reply:
        reply = "嗯，我在听。"
    log("reply=" + reply + " mood=%d" % mood)
    remember(text, reply)
    emit("done", heard=text, reply=reply, mood=mood)
    write_state("done", heard=text, reply=reply, mood=mood)
    return 0


def pick_text(args):
    """参数可能是 --file 路径，也可能直接是一句话。"""
    for i, a in enumerate(args):
        if a == "--file" and i + 1 < len(args):
            p = args[i + 1]
            try:
                with open(p, "r", encoding="utf-8-sig") as f:
                    return f.read().strip()
            except Exception as e:
                log("FILE_FAIL %r" % (e,))
                return ""
    if args:
        return " ".join(args).strip()
    # 没参数就看 ask.txt（窗口那边写中文更稳）
    try:
        with open(ASK_FILE, "r", encoding="utf-8-sig") as f:
            return f.read().strip()
    except Exception:
        return ""


def do_ask(args):
    text = pick_text(args)
    if not text:
        emit("empty", reply="没给我话呀。")
        return 0
    write_state("thinking", heard=text, note="我想想")
    fast = instant_answer(text)
    if fast:
        remember(text, fast)
        emit("done", heard=text, reply=fast, mood=0)
        write_state("done", heard=text, reply=fast, mood=0)
        return 0
    try:
        raw = ask_glm(text)
    except Exception as e:
        log("LLM_FAIL %r" % (e,))
        emit("error", heard=text, reply="脑子这会儿没连上。")
        return 1
    mood, reply = split_mood(raw)
    remember(text, reply)
    emit("done", heard=text, reply=reply, mood=mood)
    write_state("done", heard=text, reply=reply, mood=mood)
    return 0


def do_side(args, sys_prompt, mood=7, kind="translate"):
    """翻译 / 讲题 / 总结：都是同一套，换提示词而已。"""
    text = pick_text(args)
    if not text:
        emit("empty", reply="没给我内容呀。")
        return 0
    write_state("thinking", heard=text, note="我看看")
    try:
        reply = ask_plain(text, sys_prompt)
    except Exception as e:
        log("%s_FAIL %r" % (kind.upper(), e))
        emit("error", heard=text, reply="脑子这会儿没连上。")
        return 1
    reply = (reply or "").strip().strip("「」\"' ")
    if not reply:
        reply = "这个我没弄明白。"
    log("%s=%s" % (kind, reply))
    emit("done", heard=text, reply=reply, mood=mood)
    write_state("done", heard=text, reply=reply, mood=mood)
    return 0


def do_listen():
    audio = record()
    import numpy as np
    rms = float(np.sqrt(np.mean(audio.astype(np.float64) ** 2))) if audio.size else 0.0
    text = recognize()
    print(json.dumps({"rms": round(rms, 1), "text": text}, ensure_ascii=False))
    return 0


def do_wake():
    """常驻听：一轮接一轮地录、认，每句打一行 JSON；stdin 收 p 暂停、收 r 继续。
    以前是每句都重新起一次 python，冷启动 1-2 秒，唤醒总是慢半拍。
    现在进程不重启，模型只加载一次，中间只等 VAD 说完。"""
    import sys
    import threading
    import time
    _pause = {"v": False}

    def watch():
        try:
            for line in sys.stdin:
                c = (line or "").strip().lower()
                if c == "p":
                    _pause["v"] = True
                elif c == "r":
                    _pause["v"] = False
                elif c == "q":
                    os._exit(0)
        except Exception:
            pass

    threading.Thread(target=watch, daemon=True).start()
    while True:
        try:
            if _pause["v"]:
                time.sleep(0.2)
                continue
            audio = record()
            import numpy as np
            rms = float(np.sqrt(np.mean(audio.astype(np.float64) ** 2))) if audio.size else 0.0
            text = recognize()
            print(json.dumps({"rms": round(rms, 1), "text": text}, ensure_ascii=False), flush=True)
            time.sleep(0.05)
        except Exception as e:
            print(json.dumps({"rms": 0, "text": "", "err": repr(e)}, ensure_ascii=False), flush=True)
            time.sleep(0.5)


def do_talk(max_turns=8, quiet_stop=2):
    """v130 实时语音对话：一轮接一轮地「听 → 想」，每轮打一行 JSON 给窗口。
    · 窗口念回话期间这边不抢麦（窗口会发 p 暂停），念完发 r 继续
    · 连续两轮没听清就自己收麦，不干耗着
    · 任何一轮说中「停/别说了/歇会儿」就退出"""
    empties = 0
    for n in range(max_turns):
        if _STOP["v"]:
            break
        write_state("listening", note="我在听")
        try:
            audio = record()
        except Exception as e:
            log("REC_FAIL %r" % (e,))
            emit("error", reply="我的耳朵打不开，可能要看一下麦克风权限。")
            return 1
        try:
            text = (recognize() or "").strip()
        except Exception as e:
            log("ASR_FAIL %r" % (e,))
            text = ""
        if not text:
            empties += 1
            emit("empty")
            if empties >= quiet_stop:
                break
            continue
        empties = 0
        log("talk heard=" + text)
        if re.search(r"(别说了|停一下|停停|歇会儿|不聊了)", text):
            reply = "行，我先闭嘴。"
            emit("done", heard=text, reply=reply, mood=0)
            break
        fast = instant_answer(text)
        if fast:
            remember(text, fast)
            emit("done", heard=text, reply=fast, mood=0, turn=n + 1)
            continue
        try:
            raw = ask_glm(text, timeout=22)
        except Exception as e:
            log("LLM_FAIL %r" % (e,))
            emit("error", heard=text, reply="脑子这会儿没连上，等下再聊。")
            break
        mood, reply = split_mood(raw)
        if not reply:
            reply = "嗯，我在听。"
        remember(text, reply)
        emit("done", heard=text, reply=reply, mood=mood, turn=n + 1,
             act=_LAST_ACT.get("act", ""), mount=_LAST_ACT.get("mount", 0))
        write_state("done", heard=text, reply=reply, mood=mood)
    emit("bye")
    return 0


def selftest():
    """不碰麦克风、不联网的自检：句子切分、情绪摘出、本地秒答、模型链顺序、记忆条数。"""
    ok = True
    parts = split_sentences("早上好呀。今天几号？我先算一下，12 乘 13 等于 156。")
    print("S1 分句", parts, "PASS" if len(parts) == 3 else "FAIL")
    ok = ok and len(parts) == 3
    mood, body = split_mood("3\n今天有点累，不想动。")
    print("S2 情绪", mood, body[:6], "PASS" if mood == 3 and body else "FAIL")
    ok = ok and mood == 3
    print("S3 时间秒答", instant_answer("现在几点"), "PASS" if instant_answer("现在几点") else "FAIL")
    ok = ok and bool(instant_answer("现在几点"))
    print("S4 算数秒答", instant_answer("12 乘 13 等于多少"), "PASS" if "156" in (instant_answer("12 乘 13 等于多少") or "") else "FAIL")
    ok = ok and "156" in (instant_answer("12 乘 13 等于多少") or "")
    print("S5 模型链", MODEL_CHAIN, "PASS" if MODEL_CHAIN == ("glm-4-flash", "glm-4.7-flash", "glm-4-air") else "FAIL")
    ok = ok and MODEL_CHAIN[0] == "glm-4-flash"
    m = load_mem()
    print("S6 记忆条数", len(m.get("turns", [])), "PASS" if len(m.get("turns", [])) <= HISTORY_KEEP else "FAIL")
    ok = ok and len(m.get("turns", [])) <= HISTORY_KEEP
    a7, mo7, b7 = split_act("2\n今天风挺大，出门加件衣服。\n[[act:wave]]\n[[mount:3]]")
    print("S7 动作标签", a7, mo7, b7[:8], "PASS" if a7 == "wave" and mo7 == 3 and "act" not in b7 else "FAIL")
    ok = ok and a7 == "wave" and mo7 == 3 and "act" not in b7
    a8, mo8, b8 = split_act("【act：Dance】随便跳一下。")
    print("S8 宽松写法", a8, mo8, "PASS" if a8 == "dance" and "act" not in b8 else "FAIL")
    ok = ok and a8 == "dance"
    print("SUMMARY", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def do_probe():
    out = {}
    try:
        import vosk
        out["vosk"] = "ok"
    except Exception as e:
        out["vosk"] = "fail %r" % (e,)
    out["model"] = os.path.isdir(MODEL_DIR)
    try:
        import sounddevice as sd
        out["sounddevice"] = "ok"
    except Exception as e:
        out["sounddevice"] = "fail %r" % (e,)
    try:
        import edge_tts
        out["edge_tts"] = "ok"
    except Exception as e:
        out["edge_tts"] = "fail %r" % (e,)
    try:
        import miniaudio
        out["miniaudio"] = "ok"
    except Exception as e:
        out["miniaudio"] = "fail %r" % (e,)
    try:
        out["key"] = len(open(KEY_FILE, "r", encoding="utf-8").read().strip())
    except Exception as e:
        out["key"] = "fail %r" % (e,)
    out["mem"] = os.path.exists(MEM_FILE)
    print(json.dumps(out, ensure_ascii=False))
    return 0


def main():
    if len(sys.argv) < 2:
        print("usage: voice.py chat|listen|say|ask|translate|explain|sum|probe")
        return 2
    cmd = sys.argv[1]
    args = sys.argv[2:]
    try:
        if cmd == "chat":
            return do_chat()
        if cmd == "listen":
            return do_listen()
        if cmd == "wake":
            return do_wake()
        if cmd == "talk":
            return do_talk()
        if cmd == "selftest":
            return selftest()
        if cmd == "stop":
            _STOP["v"] = True
            return 0
        if cmd == "say":
            speak(" ".join(args) if args else "你好，我是道。")
            return 0
        if cmd == "ask":
            return do_ask(args)
        if cmd == "translate":
            return do_side(args, P_TRANSLATE, mood=7, kind="translate")
        if cmd == "explain":
            return do_side(args, P_EXPLAIN, mood=7, kind="explain")
        if cmd == "sum":
            return do_side(args, P_SUM, mood=8, kind="sum")
        if cmd == "story":
            return do_side(args, P_STORY, mood=1, kind="story")
        if cmd == "joke":
            return do_side(args, P_JOKE, mood=1, kind="joke")
        if cmd == "novel":
            return do_side(args, P_NOVEL, mood=6, kind="novel")
        if cmd == "probe":
            return do_probe()
        return 2
    except Exception as e:
        log("MAIN_FAIL %r" % (e,))
        log(traceback.format_exc())
        return 1


if __name__ == "__main__":
    sys.exit(main())
