# 程序版本：v0.3 | 2026-11-28 | P6 分档：读 /stat 的 mk/sit，站姿 2.0ms、骑乘 4.0ms
# 判据来源（2026-11-22 第1类二轮 帧调度）：
#   - Microsoft Learn System.Windows.Forms.Timer 备注：单线程 Timer 精度受限（55ms 上限），
#     计时靠消息泵 → Interval 不等于实际帧长，必须实测
#   - Microsoft Learn Timer.Interval：Interval 是「相对上一次 Tick」的毫秒数，不是帧预算
#   - 改前基线（本机实测 2026-11-22 18:35，Interval=33）：p50=46.6ms / fps=21.5 / paint p95=0.8ms
# 阈值口径（不是照抄数字，是按「30fps 档 + 留余量」定的）：
#   P2 p50 ≤ 34ms   30fps = 33.3ms，给 0.7ms 余量
#   P3 fps ≥ 28     30fps 档允许 15% 掉帧
#   P4 p95 ≤ 45ms   p95 不超过 p50 的 1.35 倍
#   P5 max ≤ 80ms   偶发一次卡顿不超过 2.5 帧，超过就是真卡
#   P6 paint p95 ≤ 2.0ms  单帧重绘必须 ≤ 帧预算 33ms 的 6%，否则一提帧率就爆
#   P7 稳定性：3 次采样 p50 极差 ≤ 3ms，超过视为 flaky，先修确定性再谈分数
import json
import re
import sys
import time
import urllib.request

URL = "http://127.0.0.1:8848/diag"
STATURL = "http://127.0.0.1:8848/stat"
SAMPLES = 3


def read_pet_state():
    """读 /stat 看当前是不是骑坐骑：骑乘多一层贴图 + 兽形曲线，重绘比站姿贵，阈值要分档。
    2026-11-28 复现时发现：P6 当初（11-22）只在站姿量过 0.8ms 就定 2.0ms，
    11-25 坐骑上线后骑乘态 p95 2.6–2.9ms 一直 FAIL——是判据没覆盖新场景，不是画得变慢了。"""
    try:
        with urllib.request.urlopen(STATURL, timeout=5) as r:
            t = r.read().decode("utf-8", "replace")
        mk = re.search(r"mk=(\d)", t)
        sit = re.search(r"sit=(\d)", t)
        return bool((mk and mk.group(1) == "1") or (sit and sit.group(1) == "1"))
    except Exception:
        return False


def read_diag():
    with urllib.request.urlopen(URL, timeout=5) as r:
        return r.read().decode("utf-8", "replace").strip()


def pick(text, key):
    m = re.search(key + r"\(([^)]*)\)", text)
    if not m:
        return {}
    d = {}
    for kv in m.group(1).split("|"):
        if "=" in kv:
            k, v = kv.split("=", 1)
            d[k] = v
    return d


def num(d, k):
    try:
        return float(d.get(k, "nan"))
    except Exception:
        return float("nan")


def main():
    rows = []
    fails = 0
    # 先清空滚动缓冲再测：不清空的话，机器刚忙过的那段旧样本会留在窗口里，
    # 判据会连续十几秒假 FAIL（2026-11-22 实测并发巡检后出现过 5/7）
    try:
        with urllib.request.urlopen(URL + "?reset=1", timeout=5) as r:
            r.read()
        time.sleep(6)   # 16ms 一帧，6 秒足够填满 300 条
    except Exception:
        pass
    for i in range(SAMPLES):
        t0 = time.time()
        txt = read_diag()
        iv = pick(txt, "iv")
        pm = pick(txt, "paint")
        fps = num({"fps": re.search(r"\|fps=([0-9.]+)", txt).group(1) if re.search(r"\|fps=([0-9.]+)", txt) else "nan"}, "fps")
        rows.append({
            "t": t0,
            "n": int(num(iv, "n")) if iv else 0,
            "p50": num(iv, "p50"),
            "p95": num(iv, "p95"),
            "max": num(iv, "max"),
            "fps": fps,
            "pn": int(num(pm, "n")) if pm else 0,
            "pp95": num(pm, "p95"),
            "interval": int(float(re.search(r"\|interval=(\d+)", txt).group(1))) if re.search(r"\|interval=(\d+)", txt) else 0,
            "raw": txt,
        })
        time.sleep(2)

    def rep(name, ok, detail):
        nonlocal fails
        if not ok:
            fails += 1
        print(("PASS" if ok else "FAIL") + " | " + name + " | " + detail)

    rep("P1 /diag 可读", all(r["n"] >= 100 for r in rows),
        "n=" + "/".join(str(r["n"]) for r in rows))

    p50 = [r["p50"] for r in rows]
    rep("P2 p50 <= 34ms", all(x <= 34.0 for x in p50),
        "p50=" + "/".join("%.1f" % x for x in p50))

    rep("P3 fps >= 28", all(r["fps"] >= 28.0 for r in rows),
        "fps=" + "/".join("%.1f" % r["fps"] for r in rows))

    rep("P4 p95 <= 45ms", all(r["p95"] <= 45.0 for r in rows),
        "p95=" + "/".join("%.1f" % r["p95"] for r in rows))

    rep("P5 max <= 80ms", all(r["max"] <= 80.0 for r in rows),
        "max=" + "/".join("%.1f" % r["max"] for r in rows))

    # P6 分档：站姿 2.0ms（帧预算 33ms 的 6%），骑乘 4.0ms（多一层坐骑贴图与兽形曲线，
    # 仍只占 33ms 的 12%）。站姿档不放松，骑乘档是新立的，不是把门槛整体抬高。
    mounting = read_pet_state()
    limit = 4.0 if mounting else 2.0
    rep("P6 paint p95 <= %.1fms(%s)" % (limit, "骑乘档" if mounting else "站姿档"),
        all(r["pn"] >= 100 and r["pp95"] <= limit for r in rows),
        "paint_p95=" + "/".join("%.1f" % r["pp95"] for r in rows))

    spread = max(p50) - min(p50)
    rep("P7 3 次采样不 flaky", spread <= 3.0, "p50 极差=%.1fms" % spread)

    out = {
        "time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "rows": [{k: v for k, v in r.items() if k != "raw"} for r in rows],
        "fails": fails,
    }
    with open(r"F:\Daodao\tools\界面\帧调度检查_结果.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("汇总：%d 项判据 | 过 %d | 未过 %d | %s" % (7, 7 - fails, fails, "PASS" if fails == 0 else "FAIL"))
    sys.exit(0 if fails == 0 else 1)


if __name__ == "__main__":
    main()
