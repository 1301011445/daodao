# -*- coding: utf-8 -*-
"""v133：让大模型自己给动作标签，窗口照着做
· voice.py 系统提示里加一条规矩：正文后另起一行 [[act:xxx]]，可选 [[mount:n]]
· 解析后从正文里删掉（念出来不会夹标签），连同 mood 一起打进 JSON
· pet.cs 的 TalkLoop 读到 act/mount 就调 StartAct / 换动作
判据 J1~J8
"""
import os

VOICE = [r'F:\Daodao\voice.py', r'F:\Daodao\src\桌面分身\voice.py', r'F:\Daodao\src\桌面分身\_bundle\voice.py']
PET = r'F:\Daodao\src\桌面分身\pet.cs'
done = []


def rep(s, old, new, tag):
    if old not in s:
        raise SystemExit('MISS ' + tag)
    done.append(tag)
    return s.replace(old, new, 1)


# ================= voice.py =================
s = open(VOICE[0], encoding='utf-8').read()

s = rep(s, '''MOOD_RULE = """
回复第一行只写一个情绪号（1开心 2生气 3难过 4惊讶 5犯困 6困 7疑惑 8得意，没有情绪就写 0），
从第二行开始才是要说的话。情绪号这一行不要带任何别的字。
"""''',
        '''MOOD_RULE = """
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
"""''', 'ACT_RULE')

s = rep(s, '''    msgs = [{"role": "system", "content": SYSTEM_PROMPT + MOOD_RULE}]''',
        '''    msgs = [{"role": "system", "content": SYSTEM_PROMPT + MOOD_RULE + ACT_RULE}]''', '提示接入')

s = rep(s, '''# ---------------- 说 ----------------''',
        '''# ---------------- v133：动作标签 ----------------
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

    body = re.sub(r"[\\[【]{1,2}\\s*act\\s*[:：]\\s*([A-Za-z]+)\\s*[\\]】]{1,2}", _a, raw, flags=re.I)
    body = re.sub(r"[\\[【]{1,2}\\s*mount\\s*[:：]\\s*([0-5])\\s*[\\]】]{1,2}", _m, body, flags=re.I)
    body = re.sub(r"^\\s*[\\[【]{1,2}\\s*(act|mount)\\s*[:：].*?[\\]】]{1,2}\\s*$", "", body, flags=re.I | re.M)
    return act, mount, body.strip()


# ---------------- 说 ----------------''', 'split_act')

s = rep(s, '''def ask_glm(text, timeout=24, want_model=False):
    txt, model = _post(build_messages(text), temperature=0.7, max_tokens=160,
                       timeout=timeout, want_model=True)
    return (txt, model) if want_model else txt''',
        '''def ask_glm(text, timeout=24, want_model=False):
    txt, model = _post(build_messages(text), temperature=0.7, max_tokens=200,
                       timeout=timeout, want_model=True)
    act, mount, body = split_act(txt)
    _LAST_ACT["act"] = act
    _LAST_ACT["mount"] = mount
    if not body:
        body = txt
    return (body, model) if want_model else body''', 'ask_glm 解析')

s = rep(s, '''def emit(state, heard="", reply="", mood=0):
    """把一轮结果以一行 JSON 打到 stdout，给道的窗口读。"""
    print(json.dumps({"state": state, "heard": heard, "reply": reply, "mood": mood},
                     ensure_ascii=False), flush=True)''',
        '''def emit(state, heard="", reply="", mood=0, act="", mount=0):
    """把一轮结果以一行 JSON 打到 stdout，给道的窗口读。"""
    print(json.dumps({"state": state, "heard": heard, "reply": reply, "mood": mood,
                      "act": act, "mount": mount},
                     ensure_ascii=False), flush=True)''', 'emit 带动作')

s = rep(s, '''        remember(text, reply)
        emit("done", heard=text, reply=reply, mood=mood, turn=n + 1)''',
        '''        remember(text, reply)
        emit("done", heard=text, reply=reply, mood=mood, turn=n + 1,
             act=_LAST_ACT.get("act", ""), mount=_LAST_ACT.get("mount", 0))''', 'talk 打动作')

s = rep(s, '''    print("S6 记忆条数", len(m.get("turns", [])), "PASS" if len(m.get("turns", [])) <= HISTORY_KEEP else "FAIL")
    ok = ok and len(m.get("turns", [])) <= HISTORY_KEEP''',
        '''    print("S6 记忆条数", len(m.get("turns", [])), "PASS" if len(m.get("turns", [])) <= HISTORY_KEEP else "FAIL")
    ok = ok and len(m.get("turns", [])) <= HISTORY_KEEP
    a7, mo7, b7 = split_act("2\\n今天风挺大，出门加件衣服。\\n[[act:wave]]\\n[[mount:3]]")
    print("S7 动作标签", a7, mo7, b7[:8], "PASS" if a7 == "wave" and mo7 == 3 and "act" not in b7 else "FAIL")
    ok = ok and a7 == "wave" and mo7 == 3 and "act" not in b7
    a8, mo8, b8 = split_act("【act：Dance】随便跳一下。")
    print("S8 宽松写法", a8, mo8, "PASS" if a8 == "dance" and "act" not in b8 else "FAIL")
    ok = ok and a8 == "dance"''', 'selftest S7')

for p in VOICE:
    open(p, 'w', encoding='utf-8', newline='').write(s)
print('voice.py 三份已写', len(done))

# ================= pet.cs =================
pt = open(PET, encoding='utf-8').read()
pt = rep(pt, '''                string st = JsonStr(line, "state");
                string rep = JsonStr(line, "reply");
                int md = JsonInt(line, "mood");
                if (st == "bye") break;''',
           '''                string st = JsonStr(line, "state");
                string rep = JsonStr(line, "reply");
                int md = JsonInt(line, "mood");
                string act = JsonStr(line, "act");     // v133：大模型给的动作标签
                int mnt = JsonInt(line, "mount");      // v133：想骑哪只坐骑（0 不骑）
                if (st == "bye") break;
                if (act != null && act.Length > 0 && act != "none")
                {
                    string a9 = act;
                    int m9 = mnt;
                    BeginInvoke(new MethodInvoker(delegate() { ApplyLlmAct(a9, m9); }));
                }''', 'TalkLoop 读标签')

pt = rep(pt, '''    // 六个生活动作的菜单入口，都走同一个口子：定动作类型 + 给个持续时间
    void StartAct(int kind)''',
           '''    // v133：大模型说了算 —— 它给的标签直接驱动动作，不再靠关键词猜
    void ApplyLlmAct(string act, int mount)
    {
        if (act == null) return;
        string a = act.Trim().ToLower();
        int kind = 0;
        if (a == "dance") kind = 4;
        else if (a == "ride") kind = 3;
        else if (a == "fly") kind = 1;
        else if (a == "sword") kind = 2;
        else if (a == "tea") kind = 5;
        else if (a == "tv") kind = 6;
        else if (a == "turn") kind = 9;
        if (kind > 0)
        {
            actKind = kind;
            actHold = kind >= 4 ? 400 : 470;
            if (kind >= 1 && kind <= 3) walkTargetX = -999999;
            Invalidate();
        }
        // wave / nod / hop / squat 桌面端没有对应整套动作，只当一次点头应声
        else if (a == "wave" || a == "nod" || a == "hop" || a == "squat")
        {
            moodKind = 1; moodTicks = 50; Invalidate();
        }
    }

    // 六个生活动作的菜单入口，都走同一个口子：定动作类型 + 给个持续时间
    void StartAct(int kind)''', 'ApplyLlmAct')

open(PET, 'w', encoding='utf-8', newline='').write(pt)
print('PATCH_OK', len(done))
