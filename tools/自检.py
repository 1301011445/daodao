# -*- coding: utf-8 -*-
# 程序版本：v0.1 | 2026-11-22 | 基线建档（此前无版本头）
"""道 双端自检 v1
电脑端（exe 8848 HTTP 接口）+ 手机端（apk 包内资源与桥接接口）+ 版本链（源码/包/页面/线上/账本）
用法：python 自检.py [--quiet]
输出：F:\Daodao\能力检查\<日期>.md 追加一段；发现问题会尝试登记进问题库。
"""
import io, json, os, re, subprocess, sys, time, urllib.request, datetime

BASE = r"F:\Daodao"
PY = sys.executable
SEVENZ = r"E:\Tools\7-Zip\7z.exe"
NODE = r"C:\Users\LDY\AppData\Local\Doubao\User Data\sandbox_runtime\bases\fa694f517e5995233c80a9a8db5212c2\node\node.exe"
PAGES = {
    "清单页": r"C:\Users\LDY\Doubao\chats\2026-11-11\new-chat\vermanifest\index.html",
    "落地页": r"C:\Users\LDY\Doubao\chats\2026-11-11\new-chat\道落地页\道_落地页_v069.html",
}
ONLINE = {
    "清单页": "https://4mf81m04wehh3.doubao.link/app/app_17hpue26uuw",
    "落地页": "https://4mf81m04wehh3.doubao.link/app/app_17jdxkgf27q",
}
rows = []   # (检查项, 结果 PASS/FAIL/WARN, 说明)


def add(name, ok, msg, warn=False):
    rows.append((name, "WARN" if (ok and warn) else ("PASS" if ok else "FAIL"), msg))
    return ok


def http(url, timeout=8, data=None):
    t0 = time.time()
    try:
        r = urllib.request.urlopen(
            urllib.request.Request(url, data=data), timeout=timeout)
        body = r.read()
        return body, time.time() - t0, None
    except Exception as e:
        return b"", time.time() - t0, str(e)[:80]


def read(p):
    try:
        return io.open(p, encoding="utf-8", errors="ignore").read()
    except Exception:
        return ""


# ============ 一、电脑端 ============
def check_pc():
    b, dt, err = http("http://127.0.0.1:8848/ping")
    ok = b.startswith(b"OK")
    add("电脑 /ping", ok, ("%s %.0fms" % (b.decode("utf-8", "ignore")[:40], dt * 1000)) if ok else ("连不上：%s" % err))

    for path, key, label in [("/stat", "lie=", "/stat"), ("/ver", "", "/ver")]:
        b, dt, err = http("http://127.0.0.1:8848" + path)
        good = bool(b) and (not key or key in b.decode("utf-8", "ignore"))
        add("电脑 " + label, good, (b.decode("utf-8", "ignore")[:90] if b else "空：" + str(err)))

    # TTS 出声链路（合成 mp3 字节数 + 耗时）
    b, dt, err = http("http://127.0.0.1:8848/tts?t=" + urllib.parse.quote("自检一句话"), timeout=20)
    add("电脑 /tts 出声", len(b) > 2048, "%d 字节 %.2fs%s" % (len(b), dt, "" if len(b) > 2048 else "（" + str(err) + "）"))

    # 记忆 / 情绪 / 歌单
    b, dt, err = http("http://127.0.0.1:8848/joy")
    add("电脑 /joy", bool(b), b.decode("utf-8", "ignore")[:60] or "空")
    b, dt, err = http("http://127.0.0.1:8848/music")
    add("电脑 /music", bool(b), b.decode("utf-8", "ignore")[:60] or "空")


# ============ 二、手机端（看包，不看真机） ============
def check_apk():
    apk = os.path.join(BASE, "道.apk")
    if not os.path.exists(apk):
        return add("apk 存在", False, "F:\\Daodao\\道.apk 不在")
    add("apk 存在", True, "%d 字节" % os.path.getsize(apk))

    tmp = os.path.join(os.environ["TEMP"], "dao_selftest")
    os.makedirs(tmp, exist_ok=True)
    for target in ("classes.dex", "assets/dao.html"):
        subprocess.run([SEVENZ, "e", apk, target, "-o" + tmp, "-y"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # 桥接接口对齐：JS 调的每个原生方法都得在 dex 里
    html = read(os.path.join(tmp, "dao.html")).replace("\u0000", "")
    if not html:
        return add("apk 内 dao.html", False, "抽不出 dao.html")
    ver = re.findall(r"HTML_VER\s*=\s*['\"]?(\d+)", html)
    add("apk 内 HTML_VER", bool(ver), ver[0] if ver else "没写版本号")

    called = sorted(set(re.findall(r"DaoNative\.([A-Za-z_][A-Za-z0-9_]*)", html)))
    dexp = os.path.join(tmp, "classes.dex")
    dex = ""
    if os.path.exists(dexp):
        dex = "".join(re.findall(r"[A-Za-z_][A-Za-z0-9_]{2,}", io.open(dexp, "rb").read().decode("latin-1", "ignore")))
    miss = [c for c in called if dex and c not in dex]
    add("手机 桥接方法齐全", not miss, "%d 个方法%s" % (len(called), "" if not miss else "，缺：" + ",".join(miss[:6])))

    # 曲库资源
    music = []
    try:
        out = subprocess.run([SEVENZ, "l", apk], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        music = [l.split()[-1] for l in out.stdout.decode("utf-8", "ignore").splitlines()
                 if "music" in l and l.strip().endswith(".adp")]
    except Exception:
        pass
    add("手机 曲库在包里", len(music) == 3, "%d 首：%s" % (len(music), ",".join(os.path.basename(m.replace(chr(92), "/")) for m in music)))
    wavs = [l.split()[-1] for l in subprocess.run([SEVENZ, "l", apk], stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL).stdout.decode("utf-8", "ignore").splitlines()
            if "music" in l and l.strip().endswith(".wav")]
    add("手机 包里无废 wav", len(wavs) == 0, "多余 wav %d 个%s" % (len(wavs), "" if not wavs else "：" + ",".join(os.path.basename(w.replace(chr(92), "/")) for w in wavs)), warn=False)

    # JS 语法
    blocks = re.findall(r"<script[^>]*>([\s\S]*?)</script>", html)
    bad = 0
    for i, s in enumerate(blocks):
        p = os.path.join(tmp, "s%d.js" % i)
        io.open(p, "w", encoding="utf-8").write(s)
        if os.path.exists(NODE):
            r = subprocess.run([NODE, "--check", p], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if r.returncode != 0:
                bad += 1
    add("手机 页面 JS 语法", bad == 0, "脚本 %d 段，语法错 %d" % (len(blocks), bad))

    # 关键能力是否还在页面里
    for label, key in [("语音入口(轻点说话)", "function startListen"), ("流式对话", "chatStream"),
                       ("分句合成", "sayEnqueue" if "sayEnqueue" in html else "daoPlaySong"),
                       ("唱歌", "playSongAsset"), ("气泡贴头顶", "bubble.style.bottom")]:
        add("手机 " + label, key in html, "找到" if key in html else "页面里没找到 " + key)


# ============ 三、版本链 ============
def check_chain():
    apk_ver = ""
    tmp = os.path.join(os.environ["TEMP"], "dao_selftest")
    mf = os.path.join(tmp, "AndroidManifest.xml")
    if os.path.exists(os.path.join(BASE, "src", "_apk", "AndroidManifest.xml")):
        m = read(os.path.join(BASE, "src", "_apk", "AndroidManifest.xml"))
        v = re.findall(r'android:versionCode="(\d+)"', m)
        apk_ver = v[0] if v else ""
        add("源码 清单版本", bool(v), "versionCode=%s" % apk_ver)

    src_html_ver = ""
    p = os.path.join(BASE, "src", "_apk", "assets", "dao.html")
    v = re.findall(r"HTML_VER\s*=\s*['\"]?(\d+)", read(p))
    src_html_ver = v[0] if v else ""
    add("源码 dao.html 版本", bool(v), src_html_ver)

    pet = read(os.path.join(BASE, "src", "桌面分身", "pet.cs"))
    v = re.findall(r"APP_VER = (\d+)", pet)
    add("源码 exe 版本", bool(v), v[0] if v else "没找到")

    vers = {}
    for name, path in PAGES.items():
        t = read(path)
        v = re.findall(r'data-ver="(\d+)"', t)
        vers[name] = v[0] if v else ""
        add("页面 %s 版本" % name, bool(v), vers[name] or "缺 data-ver")
        b, dt, err = http(ONLINE[name], timeout=15)
        ov = re.findall(rb'data-ver="(\d+)"', b)
        add("线上 %s 版本" % name, bool(ov) and (not vers[name] or ov[0].decode() == vers[name]),
            "线上 %s / 本地 %s" % (ov[0].decode() if ov else "读不到", vers[name]))

    led = os.path.join(BASE, "自我状态", "版本账本.json")
    try:
        d = json.load(io.open(led, encoding="utf-8"))
        add("账本 可读", True, "真用=%s 检测=%s" % (d.get("真用"), d.get("检测", {}).get("一致")))
    except Exception as e:
        add("账本 可读", False, str(e)[:60])


# ============ 四、延迟抽样（各段真实耗时） ============
def check_latency():
    import urllib.parse as up
    b, dt, err = http("http://127.0.0.1:8848/tts?t=" + up.quote("你好呀，今天怎么样"), timeout=20)
    add("延迟 电脑TTS", len(b) > 2048, "%.2fs" % dt)
    t0 = time.time()
    try:
        d = json.dumps({"model": "glm-4-flash", "temperature": 0.7, "max_tokens": 130, "stream": True,
                        "messages": [{"role": "user", "content": "自检：说一句话"}]}).encode()
        req = urllib.request.Request("https://open.bigmodel.cn/api/paas/v4/chat/completions", d,
                                     {"Authorization": "Bearer e753a789a9fe4821b46d6558346b6dd8.P5ASHghZ3RX0tPJ9",
                                      "Content-Type": "application/json"})
        first = None
        for line in urllib.request.urlopen(req, timeout=25):
            s = line.decode("utf-8", "ignore").strip()
            if s.startswith("data:") and '"content"' in s and first is None:
                first = time.time() - t0
                break
        add("延迟 LLM首字", first is not None and first < 3, "%.2fs" % (first or -1))
    except Exception as e:
        add("延迟 LLM首字", False, str(e)[:60])


def register_problems(fails):
    if not fails:
        return 0
    n = 0
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("wtk", os.path.join(BASE, "tools", "问题库.py"))
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        for name, msg in fails:
            try:
                m.register("自检失败：" + name, "双端自检", "中", msg, "selftest-" + re.sub(r"\W", "", name))
                n += 1
            except Exception:
                pass
    except Exception:
        pass
    return n


def main():
    urllib.parse = __import__("urllib.parse", fromlist=["parse"])
    check_pc()
    check_apk()
    check_chain()
    check_latency()

    fails = [(n, m) for n, s, m in rows if s == "FAIL"]
    warns = [(n, m) for n, s, m in rows if s == "WARN"]
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = ["", "## %s 双端自检" % now,
             "通过 %d / 失败 %d / 提醒 %d" % (len(rows) - len(fails) - len(warns), len(fails), len(warns))]
    for n, s, m in rows:
        mark = {"PASS": "OK", "FAIL": "!!", "WARN": "~"}[s]
        lines.append("- [%s] %s：%s" % (mark, n, m))
    out = os.path.join(BASE, "能力检查", datetime.date.today().isoformat() + ".md")
    io.open(out, "a", encoding="utf-8").write("\n".join(lines) + "\n")

    reg = register_problems(fails)
    print("\n".join(lines))
    print("登记问题 %d 条 -> %s" % (reg, out))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
