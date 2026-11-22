# -*- coding: utf-8 -*-
import sys, io
sys.path.insert(0, r"F:\Daodao\tools")
import importlib.util
spec = importlib.util.spec_from_file_location("wtk", r"F:\Daodao\tools\问题库.py")
wtk = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wtk)

items = [
    ("0.112 已出包但线上页面与短链仍是 111（五处不同号）", "P1",
     "两页 data-ver 112 / 短链体积对上 / 线上抽查完毕才算同号；本轮只做到本地双端 112"),
    ("响度体检没覆盖三首成品母带（只扫到临时 wav，全部不达标）", "P0",
     "先把母带导到 F:\\Daodao\\音频母带 固定目录，再跑 响度体检.py；成品不给判分不许出片"),
    ("判据没按单元/结构/成品三层拆开（现在 L1-L13 混在一起判）", "P1",
     "拆法：单元层=单句落音与时值；结构层=段落关系与转韵；成品层=响度/时长/音色数"),
    ("真 60fps 做不到：BeginInvoke 每帧过消息泵，UI 有活就丢帧（现 34.5fps）", "P2",
     "第一步：把重绘抽到独立呈现线程（或 Direct2D/合成层），UI 线程只收状态"),
    ("口型层仍空：口型时序.py 要音频参数、口型判据要 timeline.json，两端都没接", "P0",
     "第一步：单通道振幅包络 + 5 帧平滑出 timeline.json，先让嘴按音量动，再上 viseme"),
    ("自检.py 无网络超时，整轮卡死 7 分钟以上（本轮被迫手工 kill）", "P1",
     "给所有线上抓取加 timeout=15s 与 3 次重试，失败降级读账本，不阻塞整轮"),
]

ok = 0
for title, sev, note in items:
    try:
        r = wtk.register(title, 来源="2026-11-22 傍晚轮", 严重度=sev, 说明=note)
        print("REG_OK", title, "->", r)
        ok += 1
    except Exception as e:
        print("REG_FAIL", title, repr(e))
print("REGISTERED", ok, "of", len(items))
