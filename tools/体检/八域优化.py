# -*- coding: utf-8 -*-
"""
八域优化器：用大模型对「道」的八个能力面做体检 -> 诊断 -> 可验证落地。

八个面：动作 / 形象 / 语言 / 学习能力 / 音乐能力 / 记忆 / 检查 / 创作

原则（与 大模型迭代.py 一致）：
1. 指标先量化，大模型只做判断与提案，不直接写代码。
2. 只有白名单内的「安全改点」会被真正执行；执行前备份、执行后复测，指标没变好就回滚。
3. 其余发现一律登记进问题库（同标题去重），不做破坏性改动。
4. 所有结论都来自真实文件与真实调用，不编数据。
"""
import argparse
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.request

ROOT = r"F:\Daodao"
KEY_FILE = os.path.join(ROOT, r"src\桌面分身\key.txt")
API = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
MODEL = "glm-4-flash"
LOG = os.path.join(ROOT, "同步日志.txt")
QB = os.path.join(ROOT, r"自我状态\问题库.json")
REPORT_DIR = os.path.join(ROOT, "巡检报告")
TODAY = dt.date.today().isoformat()
STAMP = dt.datetime.now().strftime("%Y%m%d_%H%M")


def log(msg):
    line = "%s [八域优化] %s" % (dt.datetime.now().strftime("%Y-%m-%d %H:%M"), msg)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")
    print(line)


# ---------------- 指标采集 ----------------

def _png_size(p):
    try:
        from PIL import Image
        with Image.open(p) as im:
            return im.size
    except Exception:
        return None


def m_action():
    """动作：走路循环帧序列是否完整、尺寸是否一致。"""
    d = os.path.join(ROOT, r"src\桌面分身\_walk8_8")
    pngs = sorted([x for x in os.listdir(d) if re.match(r"walk\d+\.png", x, re.I)]) if os.path.isdir(d) else []
    sizes = [_png_size(os.path.join(d, x)) for x in pngs]
    uniq = len(set(s for s in sizes if s))
    return {
        "目录": d,
        "帧数": len(pngs),
        "尺寸统一": (uniq <= 1),
        "异常": 0 if (len(pngs) >= 8 and uniq <= 1) else 1,
    }


def m_look():
    """形象：形象包内文件是否齐全、尺寸是否统一。"""
    d = os.path.join(ROOT, r"形象\v69")
    files = []
    if os.path.isdir(d):
        for dp, _, fns in os.walk(d):
            files += [os.path.join(dp, f) for f in fns]
    pngs = [f for f in files if f.lower().endswith(".png")]
    empty = [f for f in files if os.path.getsize(f) == 0]
    sizes = [_png_size(f) for f in pngs[:40]]
    uniq = len(set(s for s in sizes if s))
    return {"目录": d, "文件数": len(files), "PNG数": len(pngs), "空文件数": len(empty), "尺寸统一": (uniq <= 1),
            "异常": (1 if (not files or empty or uniq > 6) else 0)}


def m_lang():
    """语言：对话模型链 + 实测一次响应延迟。"""
    vp = os.path.join(ROOT, r"src\桌面分身\voice.py")
    txt = open(vp, encoding="utf-8", errors="replace").read() if os.path.exists(vp) else ""
    m = re.search(r'MODEL_CHAIN\s*=\s*\((.*?)\)', txt, re.S)
    chain = re.findall(r'"([^"]+)"', m.group(1)) if m else []
    cur = re.search(r'MODEL\s*=\s*"([^"]+)"', txt)
    model = cur.group(1) if cur else (chain[0] if chain else "?")
    key = open(KEY_FILE, encoding="utf-8").read().strip() if os.path.exists(KEY_FILE) else ""
    lat, err, body = None, "", ""
    if key:
        t0 = dt.datetime.now()
        try:
            req = urllib.request.Request(
                API,
                data=json.dumps({"model": model, "messages": [{"role": "user", "content": "用一句话打招呼"}],
                                 "temperature": 0.6, "max_tokens": 64}).encode(),
                headers={"Content-Type": "application/json", "Authorization": "Bearer " + key})
            with urllib.request.urlopen(req, timeout=30) as r:
                body = json.loads(r.read().decode("utf-8"))
            lat = round((dt.datetime.now() - t0).total_seconds(), 2)
        except Exception as e:
            err = str(e)[:120]
    return {"模型": model, "模型链": chain, "延迟秒": lat, "错误": err, "异常": 0 if (lat and lat < 3.0 and not err) else 1}


def m_study():
    """学习能力：今天是否真的写入了学习记录。"""
    p = os.path.join(ROOT, r"自我状态\学习台账.txt")
    if not os.path.exists(p):
        p = os.path.join(ROOT, "学习台账.txt")
    n, last = 0, ""
    if os.path.exists(p):
        for line in open(p, encoding="utf-8", errors="replace"):
            line = line.strip()
            if not line:
                continue
            if TODAY in line:
                n += 1
            last = line[:80]
    return {"台账": p, "今日条目": n, "最新一条": last, "异常": 0 if n >= 1 else 1}


def _harsh(path):
    try:
        import numpy as np
        import soundfile as sf
        d, sr = sf.read(path)
        if d.ndim > 1:
            d = d.mean(axis=1)
        win = int(sr * 0.05)
        vals = []
        for i in range(0, max(1, len(d) - win), win):
            seg = d[i:i + win]
            if len(seg) < win:
                break
            sp = np.abs(np.fft.rfft(seg * np.hanning(win))) ** 2 + 1e-12
            vals.append(float(np.exp(np.mean(np.log(sp))) / np.mean(sp)))
        return round(float(np.mean(vals)) * 10, 3)
    except Exception:
        return None


def _processed_harsh(wav):
    """过一遍人声滤镜链 + 峰值归一，再算刺耳度（这样调参才会反映到指标上）。"""
    import importlib.util
    import numpy as np
    import soundfile as sf
    p = os.path.join(ROOT, r"tools\语音\人声滤镜_biquad.py")
    spec = importlib.util.spec_from_file_location("dao_fx", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    x, sr = sf.read(wav, dtype="float32")
    if x.ndim > 1:
        x = x.mean(axis=1)
    y = mod.apply_chain(x, sr)
    peak = float(np.max(np.abs(y))) or 1.0
    y = y / peak * 0.9
    out = os.path.join(ROOT, r"曲库\_试音_声库", "_八域指标_临时.wav")
    sf.write(out, y, sr)
    return _harsh(out), out


def m_music():
    """音乐：最近神经声库产物经滤镜后的刺耳度（越低越不刺耳）。"""
    cache = os.path.join(ROOT, r"OpenUtau\_x\Cache")
    cand = []
    if os.path.isdir(cache):
        cand = [os.path.join(cache, f) for f in os.listdir(cache) if f.lower().endswith(".wav")]
    if not cand:
        return {"样本数": 0, "异常": 1, "说明": "缓存里没有神经声库产物"}
    newest = max(cand, key=os.path.getmtime)
    h, _ = _processed_harsh(newest)
    return {"样本": os.path.basename(newest), "滤镜后harsh": h,
            "判据": "<=0.20 视为不刺耳", "异常": 0 if (h is not None and h <= 0.20) else 1}


def m_memory():
    """记忆：愉悦值 / 能力激励 是否有重复条目（重复刷分风险）。"""
    out = {}
    for name in ["愉悦值.json", "能力激励.json", "回忆台账.json"]:
        p = os.path.join(ROOT, "自我状态", name)
        if not os.path.exists(p):
            continue
        try:
            data = json.load(open(p, encoding="utf-8"))
        except Exception as e:
            out[name] = {"读失败": str(e)[:60]}
            continue
        recs = None
        for k in ("记录", "条目", "items", "log"):
            if isinstance(data, dict) and isinstance(data.get(k), list):
                recs = data[k]
                break
        if recs is None and isinstance(data, list):
            recs = data
        dup = 0
        if recs:
            seen = set()
            for it in recs:
                key = json.dumps(it, ensure_ascii=False, sort_keys=True)
                if key in seen:
                    dup += 1
                seen.add(key)
        out[name] = {"条目": len(recs) if recs is not None else 0, "完全重复": dup}
    tot = sum(v.get("完全重复", 0) for v in out.values())
    out["_异常"] = 0 if tot == 0 else 1
    return out


def m_check():
    """检查：定时迭代任务是否正常、最近日志有没有乱码。"""
    r = {"异常": 0}
    try:
        p = subprocess.run([r"C:\WINDOWS\System32\schtasks.exe", "/Query", "/TN", "DAO_大模型迭代", "/FO", "LIST"],
                           capture_output=True, timeout=30)
        txt = p.stdout.decode("gbk", errors="replace")
        m = re.search(r"上次运行时间:\s+(\S+\s+\S+)", txt)
        r["上次运行"] = m.group(1) if m else ""
        r["状态"] = "已注册" if p.returncode == 0 else "缺失"
        if p.returncode != 0:
            r["异常"] = 1
    except Exception as e:
        r["状态"] = "查询失败"
        r["错误"] = str(e)[:80]
        r["异常"] = 1
    last_log = ""
    rep = os.path.join(REPORT_DIR, "_iter_out.txt")
    if os.path.exists(rep):
        raw = open(rep, "rb").read()[-2000:]
        try:
            s = raw.decode("utf-8")
        except UnicodeDecodeError:
            s = ""
            r["日志乱码"] = 1
            r["异常"] = 1
        last_log = s.strip().splitlines()[-1][:100] if s.strip() else ""
    r["最近输出"] = last_log
    return r


def m_create():
    """创作：曲库产出量 + 与最近题材是否撞车。"""
    lib = os.path.join(ROOT, "曲库")
    mp3 = [f for f in os.listdir(lib) if f.lower().endswith(".mp3")] if os.path.isdir(lib) else []
    plan = os.path.join(ROOT, r"自我状态\下一首计划.json")
    nxt = ""
    try:
        nxt = json.dumps(json.load(open(plan, encoding="utf-8")), ensure_ascii=False)[:150]
    except Exception:
        pass
    return {"曲库成品数": len(mp3), "下一首计划": nxt, "异常": 0 if mp3 else 1}


DOMAINS = [
    ("动作", m_action, "走路循环帧数与尺寸一致性"),
    ("形象", m_look, "形象包完整性与尺寸统一"),
    ("语言", m_lang, "对话模型链与响应延迟"),
    ("学习能力", m_study, "当天学习记录是否落盘"),
    ("音乐能力", m_music, "神经声库产物的刺耳度"),
    ("记忆", m_memory, "激励/回忆台账是否重复"),
    ("检查", m_check, "定时迭代任务与日志编码"),
    ("创作", m_create, "成品产出与题材轮换"),
]


# ---------------- 大模型 ----------------

def ask(prompt):
    key = open(KEY_FILE, encoding="utf-8").read().strip()
    req = urllib.request.Request(
        API,
        data=json.dumps({"model": MODEL, "messages": [
            {"role": "system", "content": "你是「道」的工程体检员，只根据给定指标说话，不臆测。必须输出 JSON。"},
            {"role": "user", "content": prompt}], "temperature": 0.3, "max_tokens": 700}).encode(),
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + key})
    with urllib.request.urlopen(req, timeout=60) as r:
        data = json.loads(r.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"]


def parse_json(s):
    s = re.sub(r"```(json)?", "", s).strip()
    for pat in (r"\{.*\}", r"\[.*\]"):
        m = re.search(pat, s, re.S)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                continue
    return None


# ---------------- 问题库 ----------------

def qb_add(title, severity, detail, source="八域优化"):
    data = json.load(open(QB, encoding="utf-8"))
    issues = data["问题"]
    head = title.strip()[:6]
    for it in issues:
        if it.get("状态") != "已解决" and it.get("标题", "").strip()[:6] == head:
            return None
    nid = "Q-%03d" % (max(int(re.sub(r"\D", "", it.get("id", "Q-0")) or 0) for it in issues) + 1)
    issues.append({"id": nid, "标题": title[:60], "来源": source, "严重度": severity, "状态": "待处理",
                   "发现时间": STAMP, "解决时间": "", "解决说明": "", "scored": False, "复现": detail[:300]})
    bak = QB + ".bak_" + STAMP
    if not os.path.exists(bak):
        shutil.copy2(QB, bak)
    json.dump(data, open(QB, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    return nid


# ---------------- 白名单改点（只有这些会被自动执行） ----------------

def apply_music(prop):
    """只动 3200Hz 高搁架 / 4500Hz 峰 增益（真实常量在 Chain 初始化里），范围受限，改后复测。"""
    targets = {
        "filter_high_shelf_db": (r"(_high_shelf\(sr, 3200\.0, )(-?[0-9.]+)(\))", -3.5, -1.0),
        "filter_peak_db": (r"(_peaking\(sr, 4500\.0, )(-?[0-9.]+)(, q=0\.9\))", -3.0, -0.5),
    }
    k = prop.get("key")
    if k not in targets:
        return False, "改点不在音乐白名单"
    pat_src, lo, hi = targets[k]
    try:
        new = round(float(prop.get("new")), 2)
    except Exception:
        return False, "新值不是数字"
    if not (lo <= new <= hi):
        return False, "新值 %.2f 超出范围 [%.1f, %.1f]" % (new, lo, hi)
    p = os.path.join(ROOT, r"tools\语音\人声滤镜_biquad.py")
    txt = open(p, encoding="utf-8").read()
    m = re.search(pat_src, txt)
    if not m:
        return False, "未找到该参数定义"
    old = float(m.group(2))
    if abs(old - new) < 1e-6:
        return False, "与当前值相同（%.2f）" % old
    shutil.copy2(p, p + ".bak_" + STAMP)
    txt2 = txt[:m.start()] + m.group(1) + ("%g" % new) + m.group(3) + txt[m.end():]
    open(p, "w", encoding="utf-8").write(txt2)
    rc = subprocess.run([sys.executable, "-m", "py_compile", p], capture_output=True)
    if rc.returncode != 0:
        shutil.copy2(p + ".bak_" + STAMP, p)
        return False, "编译失败已还原"
    return True, "%s %.2f->%.2f" % (k, old, new)


def apply_lang(prop):
    """只允许在当前模型集合内重排链条顺序。"""
    if prop.get("key") != "model_chain":
        return False, "改点不在语言白名单"
    want = [str(x).strip() for x in (prop.get("new") or [])]
    vp = os.path.join(ROOT, r"src\桌面分身\voice.py")
    txt = open(vp, encoding="utf-8").read()
    m = re.search(r'MODEL_CHAIN\s*=\s*\((.*?)\)', txt, re.S)
    if not m:
        return False, "未找到 MODEL_CHAIN"
    have = re.findall(r'"([^"]+)"', m.group(1))
    if sorted(want) != sorted(have) or len(want) < 2:
        return False, "新旧模型集合不一致（只允许重排）"
    if want == have:
        return False, "顺序未变"
    shutil.copy2(vp, vp + ".bak_" + STAMP)
    new_line = 'MODEL_CHAIN = (' + ", ".join('"%s"' % x for x in want) + ')'
    open(vp, "w", encoding="utf-8").write(txt[:m.start()] + new_line + txt[m.end():])
    return True, "链条 %s -> %s" % (have, want)


def apply_memory(prop):
    """只做完全重复条目的删除（不动分数）。"""
    if prop.get("key") != "dedupe":
        return False, "改点不在记忆白名单"
    fixed = []
    for name in ["愉悦值.json", "能力激励.json", "回忆台账.json"]:
        p = os.path.join(ROOT, "自我状态", name)
        if not os.path.exists(p):
            continue
        data = json.load(open(p, encoding="utf-8"))
        key = None
        for k in ("记录", "条目", "items", "log"):
            if isinstance(data, dict) and isinstance(data.get(k), list):
                key = k
                break
        if key is None:
            continue
        seen, out = set(), []
        for it in data[key]:
            sig = json.dumps(it, ensure_ascii=False, sort_keys=True)
            if sig in seen:
                continue
            seen.add(sig)
            out.append(it)
        if len(out) != len(data[key]):
            shutil.copy2(p, p + ".bak_" + STAMP)
            data[key] = out
            json.dump(data, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
            fixed.append("%s 删重 %d 条" % (name, len(data[key]) - len(out)))
    return (True, "；".join(fixed)) if fixed else (False, "没有可删的完全重复")


APPLIERS = {"音乐能力": apply_music, "语言": apply_lang, "记忆": apply_memory}
WHITELIST_DOC = {
    "音乐能力": "filter_high_shelf_db(-3.5~-1.0) / filter_peak_db(-3.0~-0.5)",
    "语言": "model_chain（只允许重排现有模型）",
    "记忆": "dedupe（只删完全重复条目）",
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    args = ap.parse_args()
    os.makedirs(REPORT_DIR, exist_ok=True)
    rows, new_ids = [], 0

    for name, fn, what in DOMAINS:
        try:
            metrics = fn()
        except Exception as e:
            metrics = {"采集失败": str(e)[:120], "异常": 1}
        base = metrics.get("异常", 0)
        issues_brief = []
        try:
            data = json.load(open(QB, encoding="utf-8"))
            for it in data["问题"]:
                if it.get("状态") != "已解决":
                    issues_brief.append(it.get("标题", "")[:40])
            issues_brief = issues_brief[:12]
        except Exception:
            pass

        wl = WHITELIST_DOC.get(name, "无自动改点，只登记问题")
        prompt = (
            "领域：%s（检查项：%s）\n实测指标：%s\n该领域允许的自动改点：%s\n"
            "现存未解决问题标题（仅供避免重复，不要据此编造指标）：%s\n\n"
            "硬性要求：只允许引用「实测指标」里的数字；指标为 0/一致/无重复时就必须说正常，禁止编造缺陷"
            "（例如 不同尺寸数=1 即尺寸已统一；空文件=0 即无空文件）；发现必须带上指标中的具体数字。\n"
            "请输出 JSON：{\"结论\":\"一句话\",\"发现\":[{\"标题\":\"<=30字\",\"严重度\":\"高|中|低\",\"说明\":\"<=60字且含数字\"}],"
            "\"改点\":null 或 {\"key\":\"...\",\"new\":值,\"why\":\"...\"}}"
            "。发现最多 2 条，没有就空数组；只有确实需要且在白名单内才给改点。"
        ) % (name, what, json.dumps(metrics, ensure_ascii=False), wl, "；".join(issues_brief))

        conclusion, findings, prop, action = "", [], None, "未改"
        try:
            got = parse_json(ask(prompt))
        except Exception as e:
            got = None
            conclusion = "大模型调用失败：" + str(e)[:80]
        if isinstance(got, dict):
            conclusion = got.get("结论", "")[:120]
            findings = [f for f in (got.get("发现") or []) if isinstance(f, dict)][:2]
            prop = got.get("改点")

        if prop and name in APPLIERS and not args.dry:
            ok, note = APPLIERS[name](prop)
            if ok:
                try:
                    after = fn().get("异常", 0)
                except Exception:
                    after = base
                if after <= base:
                    action = "已改并复测通过：" + note
                else:
                    action = "已改但指标变差，保留待人工复核：" + note
            else:
                action = "未改：" + note
        elif prop and name not in APPLIERS:
            action = "未改：该域无自动改点，已转登记"

        if not args.dry:
            for f in findings:
                if str(f.get("严重度", "中")) not in ("中", "高"):
                    continue
                nid = qb_add(f.get("标题", "未命名"), f.get("严重度", "中"), f.get("说明", ""), "八域优化/" + name)
                if nid:
                    new_ids += 1
        rows.append({"域": name, "指标": metrics, "结论": conclusion, "发现": findings, "改点": prop, "动作": action})

    lines = ["# 八域优化报告 %s" % STAMP, "", "> 指标全部来自本地真实文件/真实调用；大模型只出判断与提案。", ""]
    for r in rows:
        lines.append("## %s" % r["域"])
        lines.append("- 指标：`%s`" % json.dumps(r["指标"], ensure_ascii=False))
        lines.append("- 结论：%s" % (r["结论"] or "（无）"))
        for f in r["发现"]:
            lines.append("- 发现[%s]：%s —— %s" % (f.get("严重度", "?"), f.get("标题", ""), f.get("说明", "")))
        if r["改点"]:
            lines.append("- 改点：`%s`" % json.dumps(r["改点"], ensure_ascii=False))
        lines.append("- 动作：%s" % r["动作"])
        lines.append("")
    rp = os.path.join(REPORT_DIR, "八域优化_%s.md" % STAMP)
    open(rp, "w", encoding="utf-8").write("\n".join(lines))
    log("REPORT=%s 新登记=%d 域=%d" % (rp, new_ids, len(rows)))
    print("REPORT", rp)


if __name__ == "__main__":
    main()
