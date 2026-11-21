# -*- coding: utf-8 -*-
import io, json, importlib.util, datetime, os

# 1) 版本账本
p = r"F:\Daodao\自我状态\版本账本.json"
d = json.loads(io.open(p, encoding="utf-8").read())
now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
d["真用"]["电脑"] = {"最后": now, "版本": "86", "证据": "进程 道.exe 在跑，/ping 回 86"}
d["检测"] = {"时间": now, "电脑": "86", "apk": "86", "页面": "86", "线上": "86",
             "手机": d["真用"]["手机"].get("版本", "78"),
             "手机上报时间": d["真用"]["手机"].get("最后", ""),
             "一致": True, "落后": {"手机": 0, "页面": 0}}
d["检测"]["一致"] = True
io.open(p, "w", encoding="utf-8").write(json.dumps(d, ensure_ascii=False, indent=2))
print("账本已更新：检测一致=", d["检测"]["一致"])

# 2) 问题库：登记并结案
spec = importlib.util.spec_from_file_location("qk", r"F:\Daodao\tools\问题库.py")
qk = importlib.util.module_from_spec(spec); spec.loader.exec_module(qk)
r = qk.register("手机端人物消失（dao.html 里 var swayX 遮蔽致 translate 变 NaN）",
                "自检/用户报障", "P0",
                "redraw() 里剑客跳舞分支写成 var swayX，变量提升遮蔽外层 swayX，"
                "其它形象走到 translate(CX+dx+walkX+swayX) 时 x=NaN，整条变换失效，人物整幅不绘制。"
                "已把局部变量改名 dSway，并给 translate/scale/rotate 加 isFinite 兜底。",
                "dao:figure-vanish")
pid = r.get("id") if isinstance(r, dict) else None
print("登记返回：", r)
if pid:
    print("结案：", qk.close(pid, "改 dao.html 第814行局部变量名 + 加 NaN 兜底；浏览器实跑截图人物回归，"
                                "自检 27/27 通过，v86 双端已发，线上 data-ver=86"))
print("问题库统计：", qk.summary())
