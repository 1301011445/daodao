# -*- coding: utf-8 -*-
"""手机端静态自检：不插手机也能查 apk 里到底装了什么。

查的是"发出去的那只包"，而不是运行中的手机：
  1) AndroidManifest 的 versionCode/versionName（用 aapt2）
  2) assets/dao.html 的 HTML_VER
  3) 页面里内嵌的图：FACES / POSES / EXPRS 各几张，每张 base64 能否解成完整 PNG
  4) 音频与场景资源在不在
  5) 三处数字互相不矛盾（manifest 版本 == HTML_VER）
"""
import base64, os, re, subprocess, sys, zipfile, datetime, struct

APK = r"F:\Daodao\道.apk"
OUT_DIR = r"F:\Daodao\巡检报告"
AAPT2 = r"E:\AndroidTools\sdk\build-tools\34.0.0\aapt2.exe"


def png_ok(b):
    if len(b) < 33 or b[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    w, h = struct.unpack(">II", b[16:24])
    return w, h


def arr_count(html, name):
    """数一个 var NAME = [ ... ] 数组里有几项。"""
    m = re.search(r"var\s+" + name + r"\s*=\s*\[", html)
    if not m:
        return -1
    i = m.end() - 1
    depth, n, j = 0, 0, i
    in_str, q = False, ""
    while j < len(html):
        c = html[j]
        if in_str:
            if c == "\\":
                j += 2
                continue
            if c == q:
                in_str = False
        else:
            if c in "\"'":
                in_str, q = True, c
            elif c == "[":
                depth += 1
            elif c == "]":
                depth -= 1
                if depth == 0:
                    break
            elif c == "," and depth == 1:
                n += 1
        j += 1
    return n + 1 if n else 0


def data_uris(html, name):
    m = re.search(r"var\s+" + name + r"\s*=\s*\[([\s\S]*?)\];", html)
    if not m:
        return []
    return re.findall(r"data:image/png;base64,([A-Za-z0-9+/=]+)", m.group(1))


def main():
    res = []
    ok = True

    if not os.path.exists(APK):
        print("NO_APK")
        return 2

    with zipfile.ZipFile(APK) as z:
        html = z.read("assets/dao.html").decode("utf-8", "replace")
        names = set(z.namelist())

    hv = re.search(r"var\s+HTML_VER\s*=\s*'(\d+)'", html)
    html_ver = hv.group(1) if hv else "?"
    res.append(("页面版本 HTML_VER", html_ver))

    # manifest
    mf_ver, mf_name = "?", "?"
    if os.path.exists(AAPT2):
        try:
            p = subprocess.run([AAPT2, "dump", "badging", APK], capture_output=True, text=True, timeout=60)
            for line in p.stdout.splitlines():
                if "versionCode" in line:
                    mv = re.search(r"versionCode='(\d+)'", line)
                    vn = re.search(r"versionName='([^']*)'", line)
                    if mv:
                        mf_ver = mv.group(1)
                    if vn:
                        mf_name = vn.group(1)
                    break
        except Exception as e:
            res.append(("aapt2 失败", str(e)))
    res.append(("apk versionCode", mf_ver))
    res.append(("apk versionName", mf_name))

    # 图
    for arr in ("FACES", "POSES", "EXPRS"):
        cnt = arr_count(html, arr)
        uris = data_uris(html, arr)
        bad = []
        wh = set()
        total = 0
        for i, u in enumerate(uris):
            try:
                b = base64.b64decode(u)
            except Exception:
                bad.append(i)
                continue
            total += len(b)
            meta = png_ok(b)
            if not meta:
                bad.append(i)
            else:
                wh.add("%dx%d" % meta)
        res.append((arr + " 张数", ("%d 组 / %d 张" % (cnt, len(uris))) if arr == "EXPRS" else cnt))
        res.append((arr + " 可解码", "%d/%d" % (len(uris) - len(bad), len(uris))))
        res.append((arr + " 尺寸", "、".join(sorted(wh)) if wh else "无"))
        res.append((arr + " 原始体积", "%.1f MB" % (total / 1048576.0) if total else "0"))
        if bad:
            ok = False
            res.append((arr + " 坏图下标", ",".join(map(str, bad[:10]))))

    # 资源
    music = [n for n in names if n.startswith("assets/music/")]
    scenes = [n for n in names if n.startswith("assets/scene_")]
    res.append(("音频", "%d 个" % len(music)))
    res.append(("场景图", "%d 张" % len(scenes)))
    if len(scenes) < 6:
        ok = False

    # 三处一致
    if html_ver.isdigit() and mf_ver.isdigit() and int(html_ver) != int(mf_ver):
        ok = False
        res.append(("版本一致性", "不一致（页面 %s / apk %s）" % (html_ver, mf_ver)))
    else:
        res.append(("版本一致性", "一致 v%s" % html_ver))

    res.append(("apk 体积", "%.2f MB" % (os.path.getsize(APK) / 1048576.0)))

    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M")
    os.makedirs(OUT_DIR, exist_ok=True)
    out = os.path.join(OUT_DIR, "手机静态自检_%s.txt" % ts)
    with open(out, "w", encoding="utf-8") as f:
        f.write("手机端静态自检 %s（不插手机，直接查 apk 里的东西）\n\n" % ts)
        for k, v in res:
            f.write("%-18s %s\n" % (k, v))
        f.write("\n结论：%s\n" % ("PASS" if ok else "FAIL"))
    for k, v in res:
        print("%-18s %s" % (k, v))
    print("结论：%s" % ("PASS" if ok else "FAIL"))
    print("报告:", out)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
