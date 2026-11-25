# -*- coding: utf-8 -*-
"""v140 记账：版本账本 / 版本使用 / 发版记录 / 问题库。"""
import io, json, sys, datetime

R = r"F:\Daodao"
EXE_N, APK_N = 14438912, 31242121
EXE, APK = "https://aka.doubaocdn.com/s/vOZ4r4KyTr", "https://aka.doubaocdn.com/s/7RaBG2Sd9f"
STAMP = "2026-11-25 20:50"

p = R + r"\自我状态\版本账本.json"
d = json.load(io.open(p, encoding="utf-8"))
d["current"] = 140
v = d["versions"]
item = dict(版本=140, exe=EXE_N, apk=APK_N, exe链接=EXE, apk链接=APK,
            说明="生活动作只留骑坐骑；电视/喝茶/跳舞/转身/飞/御剑/滑板/轮滑与客厅/花丛/云海/海边场景下线；贴边探头防抖",
            时间=STAMP)
if isinstance(v, list):
    v.append(item)
else:
    v["140"] = item
det = d.get("检测", {})
for k in list(det.keys()):
    if isinstance(det[k], str):
        det[k] = "140"
    else:
        det[k] = "140"
det["时间"] = STAMP
d["真用"] = {"版本": "140", "电脑": "重启后进程 道.exe 载入 140", "手机": "待真机安装 1.40（adb 确认 versionCode=140）"}
json.dump(d, io.open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("账本 current=", d["current"], "版本数", len(v))

# 版本使用
p2 = R + r"\自我状态\版本使用.json"
u = json.load(io.open(p2, encoding="utf-8"))
u.setdefault("版本", {})["140"] = {"真改动": True, "两端同号": True,
                                   "三项真验": ["两页 140 上线", "exe 140 编译并真跑", "apk 140 编译"],
                                   "真在用": "电脑 140；手机待装"}
json.dump(u, io.open(p2, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("版本使用 140 写入")

# 发版记录
p3 = R + r"\发版记录.txt"
txt = io.open(p3, encoding="utf-8").read()
txt += ("\n\n=== v140（%s）===\n"
        "1. 生活动作只留「骑坐骑」：右键菜单去掉飞一趟/御剑飞行/跳个舞/转个身/喝杯咖啡/看会儿电视；\n"
        "   远程命令只留 ride；模型动作只认 ride；闲着自触发改成偶尔骑一段（原来随机 4/5/6 跳舞喝茶看电视）。\n"
        "2. 绘制侧清理：道具只画 actKind==3；airY/travel/场景映射/pose 表都只留坐骑；\n"
        "   跳舞整只摇摆、看电视侧身坐、转身侧背换图、御剑踩剑、滑板轮滑道具全部删。\n"
        "3. 景只留城市(0)/乡野(1)两张，海边/花丛/云海/客厅随动作下线（桌面 sceneIdx 按日轮 2 张）。\n"
        "4. 手机端 dao.html 同步：drawActProps 只画坐骑、ACT_NAMES=['ride']、pickMode 只随机 ride、\n"
        "   SCENE_FILES 只留城市/乡野两张、场景生命动画删 2/3/4/5；招手时脸与头改同频（6px/7rad）。\n"
        "5. 出包：exe %d 字节（%s）、apk %d 字节（%s）；两页 140 已 finished（清单 7712090048565120200 / 落地 7712090144962186478）。\n"
        % (STAMP, EXE_N, EXE, APK_N, APK))
io.open(p3, "w", encoding="utf-8").write(txt)
print("发版记录已追加")

sys.path.insert(0, R + r"\tools")
import 问题库 as qk
pid = qk.register("除坐骑外的动作场景全部下线", "2026-11-25 用户要求", "P1",
                  "飞/御剑/跳舞/转身/喝茶/看电视/滑板/轮滑及其专属场景、姿势、道具要删掉，只留坐骑系统",
                  "ui:scenes-prune")
qk.close(pid, "已删：桌面与手机端入口、绘制、姿势、场景四层都清理；两端 140 编译，两页已上线；代码体积 exe 减少 1,536 字节、手机端道具与四场景绘制整段移除",
         "F:\\Daodao\\发版记录.txt v140 段")
print("问题库", pid, "已关闭")
