# -*- coding: utf-8 -*-
"""形象尺寸自检：核对桌面端素材与画布常量的匹配情况。
规则（来自 src/桌面分身/pet.cs）：
  W=380 H=205，脚底 footY=cy+68=195，正面立绘 targetH=188
  姿势/八帧走路图是 152 高，按原始像素 1:1 贴
发现"素材会超出画布/被裁"的项就落一条问题记录，不自动改代码。
"""
import os, struct, json, datetime

BUNDLE = r"F:\Daodao\src\桌面分身\_bundle"
OUT_DIR = r"F:\Daodao\巡检报告"
QB = r"F:\Daodao\自我状态\问题库.json"

W, H, FOOT_Y, TARGET_H = 380, 205, 195, 188
ART_H = 152           # pose / walk8 / swordfly 的显示高度
TOP_LIMIT = 6         # 头顶至少留 6 像素


def png_size(p):
    with open(p, "rb") as f:
        head = f.read(24)
    if head[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    return struct.unpack(">II", head[16:24])


def main():
    rows, bad = [], []
    if not os.path.isdir(BUNDLE):
        print("BUNDLE 不存在")
        return 2
    for name in sorted(os.listdir(BUNDLE)):
        if not name.lower().endswith(".png"):
            continue
        wh = png_size(os.path.join(BUNDLE, name))
        if not wh:
            continue
        w, h = wh
        if name.startswith(("pose_", "walk8_", "swordfly")):
            draw_h = ART_H
            kind = "姿势"
        elif name.startswith(("face_", "expr_")):
            draw_h = TARGET_H
            kind = "立绘/表情(缩略到 256 后按 %d 贴)" % TARGET_H
            # 缩略图固定 256 高，实际显示高度由 targetH 决定
            h = 256
        else:
            continue
        base_w = draw_h * (w / float(h))
        top = FOOT_Y - draw_h
        over = (top < TOP_LIMIT) or (base_w > W - 8)
        rows.append((name, w, h, round(base_w, 1), draw_h, top, "越界" if over else "ok"))
        if over:
            bad.append(name)

    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M")
    out = os.path.join(OUT_DIR, "形象尺寸自检_%s.txt" % ts)
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write("形象尺寸自检 %s\n画布 %dx%d 脚底 y=%d 立绘显示高=%d 姿势图高=%d\n\n"
                % (ts, W, H, FOOT_Y, TARGET_H, ART_H))
        f.write("%-24s %-11s %-6s %-9s %-7s %-6s %s\n" % ("file", "原图", "显示h", "显示w", "y范围", "顶部", "判定"))
        for n, w, h, bw, dh, top, st in rows:
            f.write("%-24s %-11s %-6d %-9.1f %-7s %-6d %s\n"
                    % (n, "%dx%d" % (w, h), dh, bw, "%d..%d" % (top, FOOT_Y), top, st))
        f.write("\n越界 %d 项\n" % len(bad))

    if bad:
        try:
            with open(QB, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {"items": []}
        items = data.get("items", [])
        key = "Q-012"
        hit = [i for i in items if str(i.get("id", "")).upper().startswith(key)]
        if not hit:
            items.append({
                "id": key, "title": "形象素材显示尺寸越出画布",
                "status": "open", "scored": False,
                "detail": "形象尺寸自检发现 %d 项素材按当前常量贴出画布：%s" % (len(bad), "、".join(bad[:6])),
                "found_at": ts, "report": out,
            })
            data["items"] = items
            with open(QB, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

    print(open(out, encoding="utf-8").read().splitlines()[-1])
    print("报告:", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
