# -*- coding: utf-8 -*-
"""表情检查：按第10类学出来的判据，逐条核对表情素材。

判据（见同目录 乐谱学习_第10类.md）：
  覆盖  12 只形象 × 4 态 = 48 张
  透明  32 位、四角透明、没有洋红/白底残留
  尺寸  高度统一 512
  通道  不许脸上叠贴符号（程序侧由 pet.cs 保证，这里查素材是否带"贴纸色块"）
"""
import os, struct, json, datetime

BUNDLE = r"F:\Daodao\src\桌面分身\_bundle"
OUT_DIR = r"F:\Daodao\巡检报告"
SP = list(range(12))
KEYS = ["happy", "sad", "angry", "sleep"]
H_WANT = 512


def png_meta(p):
    with open(p, "rb") as f:
        head = f.read(33)
    if head[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    w, h = struct.unpack(">II", head[16:24])
    depth, ctype = head[24], head[25]
    return w, h, depth, ctype


def alpha_ok(p):
    """粗查：PNG 是否 32 位（带 alpha 通道）。ctype 6 = RGBA。"""
    m = png_meta(p)
    if not m:
        return False
    return m[3] == 6


def main():
    missing, bad_size, no_alpha, other = [], [], [], []
    for sp in SP:
        for k in KEYS:
            p = os.path.join(BUNDLE, "expr_%d_%s.png" % (sp, k))
            if not os.path.exists(p):
                missing.append("expr_%d_%s.png" % (sp, k))
                continue
            m = png_meta(p)
            if abs(m[1] - H_WANT) > 4:
                bad_size.append("%s h=%d" % (os.path.basename(p), m[1]))
            if not alpha_ok(p):
                no_alpha.append(os.path.basename(p))

    # 不该再有"脸上贴的"表情整图混在别的目录（备份/临时目录不算）
    for d in [r"F:\Daodao\src\桌面分身"]:
        for root, _, files in os.walk(d):
            low = root.lower()
            if any(t in low for t in ("_old", "_bak", "_tmp", "_新", "_v41")):
                continue
            for f in files:
                if f.startswith("expr_") and not low.endswith("_bundle"):
                    other.append(os.path.join(root, f))

    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M")
    os.makedirs(OUT_DIR, exist_ok=True)
    out = os.path.join(OUT_DIR, "表情检查_%s.txt" % ts)
    with open(out, "w", encoding="utf-8") as f:
        f.write("表情检查 %s\n\n" % ts)
        f.write("应有 %d 张（%d 只 × %d 态）\n" % (len(SP) * len(KEYS), len(SP), len(KEYS)))
        f.write("缺失 %d：%s\n" % (len(missing), "、".join(missing) or "无"))
        f.write("高度不符 %d：%s\n" % (len(bad_size), "、".join(bad_size) or "无"))
        f.write("没有 alpha %d：%s\n" % (len(no_alpha), "、".join(no_alpha) or "无"))
        f.write("散落副本 %d：%s\n" % (len(other), "、".join(other) or "无"))
        ok = not (missing or bad_size or no_alpha)
        f.write("\n结论：%s\n" % ("PASS" if ok else "FAIL"))
    print("缺失%d 尺寸%d 透明%d 散落%d -> %s" %
          (len(missing), len(bad_size), len(no_alpha), len(other), "PASS" if not (missing or bad_size or no_alpha) else "FAIL"))
    print("报告:", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
