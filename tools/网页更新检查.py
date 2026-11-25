# -*- coding: utf-8 -*-
"""网页更新检查（2026-11-26 新增，用户要求：网页没更新要扣分，没检查到也要扣分）
判据：
 W0 本轮检查距上次检查 ≤26 小时（超过=漏检，扣分）
 W1 清单页线上 data-ver == 版本账本 current
 W2 落地页线上 data-ver == current 且 vbadge 与短链一致
 W3 线上短链 == 账本里最新一版的 exe/apk 直链
 W4 线上正文里的「当前版本号」数字 == current（文案不能留旧数字）
 W5 本地两页文件 mtime 距今 ≤3 天
任何一条 FAIL 就记一次扣分（网页未更新 -2 / 漏检 -2），写进 自我状态\网页扣分.json。
"""
import io, json, os, re, sys, time, urllib.request, datetime
R = r"F:\Daodao"
REC = os.path.join(R, r"自我状态\网页更新记录.json")
PEN = os.path.join(R, r"自我状态\网页扣分.json")
LEDGER = os.path.join(R, r"自我状态\版本账本.json")
P1 = os.path.join(R, r"..\..\..\..\..\Users\LDY\Doubao\chats\2026-11-11\new-chat\vermanifest\index.html")
URL1 = "https://4mf81m04wehh3.doubao.link/app/app_17hpue26uuw"
URL2 = "https://4mf81m04wehh3.doubao.link/app/app_17jdxkgf27q"
f1 = r"C:\Users\LDY\Doubao\chats\2026-11-11\new-chat\vermanifest\index.html"
f2 = r"C:\Users\LDY\Doubao\chats\2026-11-11\new-chat\道落地页\道_落地页_v069.html"

def get(url):
    try:
        return urllib.request.urlopen(url, timeout=8).read().decode("utf-8", "ignore")
    except Exception as e:
        return "FETCH_ERR:" + str(e)

led = json.load(io.open(LEDGER, encoding="utf-8"))
cur = str(led.get("current", ""))
last = None
if os.path.exists(REC):
    try:
        recs = json.load(io.open(REC, encoding="utf-8"))
        if recs: last = recs[-1]
    except Exception: recs = []
else:
    recs = []
now = datetime.datetime.now()
now_s = now.strftime("%Y-%m-%d %H:%M")

rows, pen = [], 0
def add(code, ok, detail):
    global pen
    rows.append((code, ok, detail))

if last and last.get("时间"):
    try:
        gap = (now - datetime.datetime.strptime(last["时间"], "%Y-%m-%d %H:%M")).total_seconds()/3600
        add("W0", gap <= 26, f"距上次检查 {gap:.1f} 小时（阈值 26）")
    except Exception:
        add("W0", False, "上次检查时间读不出来")
else:
    add("W0", False, "没有历史检查记录（本轮补上，记一次漏检）")

t1 = get(URL1); t2 = get(URL2)
m = re.search(r'data-ver="(\d+)"', t1)
add("W1", bool(m) and m.group(1) == cur, f"清单页线上 data-ver={m.group(1) if m else '取不到'}，账本 current={cur}")

m2 = re.search(r'data-ver="(\d+)"', t2)
vb = re.search(r'class="vbadge"[^>]*>\s*v([0-9.]+)', t2)
bv = (vb.group(1) or vb.group(2)) if vb else None
want_badge = "1." + str(cur)[1:] if len(str(cur)) >= 3 else "1.0." + str(cur)
bv_ok = bool(bv) and bv == want_badge
add("W2", bool(m2) and m2.group(1) == cur and bv_ok,
    f"落地页线上 data-ver={m2.group(1) if m2 else '取不到'}，角标={bv or '取不到'}（应为 {want_badge}）")

ver = (led.get("versions") or [{}])[-1]
add("W3", (ver.get("exe_link","") and ver.get("exe_link") in t2 and ver.get("apk_link","") in t2),
    f"线上短链 exe={ver.get('exe_link','-')} apk={ver.get('apk_link','-')}，命中={'是' if (ver.get('exe_link','') in t2) else '否'}")

num = re.search(r"当前版本号：(\d+)", t1)
add("W4", bool(num) and num.group(1) == cur, f"清单页正文写的「当前版本号」={num.group(1) if num else '没有这句'}")

ages = []
for p in (f1, f2):
    ages.append(None if not os.path.exists(p) else round((time.time()-os.path.getmtime(p))/86400, 1))
add("W5", all(a is not None and a <= 3 for a in ages), f"本地两页文件 {ages} 天前改过（阈值 3）")

print("== 网页更新检查（v%s）==" % cur)
for c, ok, d in rows:
    print(("PASS " if ok else "FAIL ") + c + " " + d)
bad = [c for c, ok, _ in rows if not ok]
for c in bad:
    pen += 2 if c == "W0" else 2
if bad:
    recs.append({"时间": now_s, "版本": cur, "结论": "FAIL", "不过": bad, "扣分": pen})
    pl = []
    if os.path.exists(PEN):
        try: pl = json.load(io.open(PEN, encoding="utf-8"))
        except Exception: pl = []
    pl.append({"时间": now_s, "原因": "网页没更新或没检查", "项": bad, "扣": pen})
    io.open(PEN, "w", encoding="utf-8").write(json.dumps(pl, ensure_ascii=False, indent=2))
else:
    recs.append({"时间": now_s, "版本": cur, "结论": "PASS", "扣分": 0})
io.open(REC, "w", encoding="utf-8").write(json.dumps(recs, ensure_ascii=False, indent=2))
print(f"SUMMARY|{len(rows)-len(bad)}/{len(rows)}|扣分={pen}")
sys.exit(0 if not bad else 3)





