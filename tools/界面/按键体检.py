# -*- coding: utf-8 -*-
"""按键体检：静态解析 dao.html 的 CSS，判手指点得到的尺寸。
阈值（Android Material / Apple HIG 通行下限）：
  B1 所有 button 的可点高度 >= 44px
  B2 底部工具条按钮 >= 48px（高频操作，比通用线更严）
  B3 输入框字号 >= 16px（低于 16px 移动端会自动放大页面）
  B4 文字类按钮字号 >= 14px
  B5 悬浮工具条不得压在系统手势区（要有 safe-area 处理）
用法：python 按键体检.py [html路径]
输出：PASS/FAIL 每项 + 汇总；退出码 0 全过，1 有问题。
"""
import re
import sys
import io
import json
import os

HTML = sys.argv[1] if len(sys.argv) > 1 else r"F:\Daodao\src\_apk\assets\dao.html"


def css_blocks(text):
    """取出 <style> 里的 选择器->声明体"""
    sty = re.search(r"<style[^>]*>(.*?)</style>", text, re.S)
    if not sty:
        return {}
    out = {}
    for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", sty.group(1)):
        out[m.group(1).strip().replace("\n", " ")] = m.group(2).strip()
    return out


def px(body, prop):
    m = re.search(prop + r":\s*([\d.]+)px", body)
    return float(m.group(1)) if m else None


def main():
    if not os.path.exists(HTML):
        print("FAIL 找不到 %s" % HTML)
        return 1
    text = io.open(HTML, encoding="utf-8").read()
    blocks = css_blocks(text)
    rows, fails = [], 0

    # B1 所有按钮
    base = blocks.get("button", "")
    minh = px(base, "min-height") or 0
    font = px(base, "font-size") or 0
    # 具体区块覆盖基线
    rules = []
    for sel, body in blocks.items():
        if "button" not in sel or sel == "button" or ":" in sel:
            continue                      # 跳过 :active 等伪类，避免把状态规则当成尺寸
        h = px(body, "min-height") or 0
        pad = re.search(r"padding:\s*([\d.]+)px", body)
        pad_tb = float(pad.group(1)) if pad else 0
        has_size = h > 0 or pad_tb > 0   # 只管真正控制尺寸的规则
        if not has_size:
            continue
        f = px(body, "font-size") or font
        rules.append((sel, h if h else 2 * pad_tb + f * 1.5, f))

    worst_h = min([r[1] for r in rules if r[1] > 0] or [minh])
    b1 = worst_h >= 44
    rows.append(("B1 按钮可点高度 >=44px", b1, "最矮 %.1fpx" % worst_h))

    # B2 工具条按钮
    bar = blocks.get("#bar .minis button", "")
    bar_h = px(bar, "min-height") or 0
    b2 = bar_h >= 48
    rows.append(("B2 底部工具条 >=48px", b2, "%.0fpx" % bar_h))

    # B3 输入框字号
    ask = blocks.get("#askInput", "")
    ask_f = px(ask, "font-size") or 0
    b3 = ask_f >= 16
    rows.append(("B3 输入框字号 >=16px", b3, "%.1fpx" % ask_f))

    # B4 字号
    worst_f = min([r[2] for r in rules if r[2] > 0] or [font])
    b4 = worst_f >= 14
    rows.append(("B4 按钮字号 >=14px", b4, "最小 %.1fpx" % worst_f))

    # B5 安全区
    b5 = "safe-area-inset-bottom" in text or "env(safe-area" in text
    rows.append(("B5 悬浮条避让系统手势区", b5, "safe-area 出现 %d 次" % text.count("safe-area")))

    for name, ok, ev in rows:
        print(("PASS " if ok else "FAIL ") + name.ljust(26) + " 实测 " + str(ev))
        if not ok:
            fails += 1
    print("汇总：" + ("全过" if fails == 0 else "%d 项不过" % fails))

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "按键体检.json")
    with io.open(out, "w", encoding="utf-8") as f:
        json.dump({"html": HTML, "rows": [{"项": n, "过": o, "实测": e} for n, o, e in rows],
                   "失败": fails}, f, ensure_ascii=False, indent=2)
    return 0 if fails == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
