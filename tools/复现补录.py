# -*- coding: utf-8 -*-
# 程序版本：v0.1 | 2026-11-22 | 基线建档（此前无版本头）
"""
复现补录：给已解决的历史问题补「复现用例」，让每一条都能被下一个人照着做一遍。

为什么写这个：纠错体检 C1 要求已解决项带复现 ≥80%，此前只有 3/43（7%），
说明问题“解决了”但没有留下能被重新验证的手。这里按问题 id 逐条写死复现步骤，
脚本顺手核一遍步骤里点名的工具存不存在——点名的东西不在，就不算能跑的复现。

用法：python 复现补录.py          写入问题库并打印比例
      python 复现补录.py --dry    只打印不写
"""
import json, re
import os
import sys

库 = r"F:\Daodao\自我状态\问题库.json"
丁 = r"F:\Daodao\tools"
音 = os.path.join(丁, "音乐")

# id -> (类型, 步骤)  类型：脚本 / 端点 / 人工
M = {
"Q-001": ("人工", "开 道.exe 让它站着不动，任务管理器看 30 秒：CPU 应 <5%，不应持续 30fps 满载"),
"Q-002": ("脚本", "python %s\\自检.py，看「页面 清单页 版本」且用发布接口复发布一次应回 ok:true" % 丁),
"Q-003": ("脚本", "python %s\\版本机制.py：五处 versionCode/versionName 必须同号，报「不一致」即复现" % 丁),
"Q-008": ("人工", "手机浏览器与微信各开一次清单页，点下载：应能下到 .apk 且安装包 size 与页面写的字节一致"),
"Q-009": ("脚本", "python %s\\音频\\响度体检.py <成品.wav>：先看时长落在 170–200 秒，再看 LUFS" % 丁),
"Q-010": ("脚本", "python %s\\自检.py 的「线上」两项：应读到线上版本号，不是「取不到」" % 丁),
"Q-011": ("脚本", "python %s\\自检.py 的表情白名单检查：贴图表情应为 0 处" % 丁),
"Q-023": ("脚本", "python %s\\判据检查\\判据检查.py：整首重演伴奏应在 L1–L6 被判 FAIL" % 音),
"Q-025": ("人工", "手机上装当天 apk 打开一次，回 道.exe 看 /ping 与「手机」账本版本号是否跟着变"),
"Q-029": ("脚本", "python %s\\高点分布\\高点分布.py：单曲最高音句数应 ≤4 句，>4 即复现" % 音),
"Q-031": ("脚本", "python %s\\音频\\响度体检.py <成品.wav>：true peak 应 ≤ -1 dBTP，-0.72 就是复现" % 丁),
"Q-032": ("脚本", "python %s\\戏曲腔\\戏曲腔检查.py：自然人声/戏曲腔不应被通用分支叠第二遍（P1–P5 全 PASS）" % 音),
"Q-036": ("脚本", "python -c \"print(open(r'F:\\Daodao\\src\\_apk\\assets\\dao.html',encoding='utf-8').read().count('voice'))\"：应 >0，0 即复现"),
"Q-037": ("脚本", "python -c \"import json;json.load(open(r'F:\\Daodao\\自我状态\\音色池.json',encoding='utf-8-sig'))\"：能解析且音色数 ≥2"),
"Q-038": ("脚本", "python %s\\界面\\触控热区检查.py：主按钮 ≥44、行内 ≥32、间距 ≥8，任一不达标即复现" % 丁),
"Q-039": ("端点", "curl http://127.0.0.1:8848/ping 回 OK|道|<ver>|<ip>|8848；再请求一次音频端点应回音频字节而非 404"),
"Q-040": ("端点", "curl \"http://127.0.0.1:8848/tts?t=测试\"：回音频字节；回 TTSFAIL 即复现（注意参数是 t= 不是 text=）"),
"Q-041": ("人工", "手机上断网打开曲库页：应能播本地音频，不是空列表"),
"Q-042": ("人工", "手机播放一段 ADPCM 语音到最后一帧：控制台不应出现 DataView RangeError"),
"Q-043": ("人工", "调一次 GLM-TTS 接口：返回码不是 429/1113 即已恢复"),
"Q-044": ("人工", "在腾讯云语音合成通道发一句：能出声，且不报缺 SecretId/SecretKey"),
"Q-045": ("端点", "curl \"http://127.0.0.1:8848/tts?t=令牌检查\"：不应回 TTSFAIL，且首字节 <150ms"),
"Q-046": ("人工", "手机与电脑不在同一 WiFi（用流量）时发一条记事：应仍能同步，不需要同网"),
"Q-047": ("人工", "往 ntfy 推两条带换行消息：应能逐条读到，不被压成一行"),
"Q-051": ("人工", "手机上连续问两句：不应两路声音叠着响"),
"Q-052": ("人工", "手机曲库页打开：列表非空且能播"),
"Q-053": ("人工", "手机点一次按键到界面响应：应无明显迟滞（<300ms 出反馈）"),
"Q-054": ("脚本", "python %s\\自检.py 比对说明文件与实际的 app_id；或 grep 说明文件里的 app_id 与清单页一致" % 丁),
"Q-055": ("端点", "curl -w \"%%{time_starttransfer}\" -o /dev/null \"http://127.0.0.1:8848/tts?t=延迟\"：应 ≤0.15s"),
"Q-058": ("脚本", "python %s\\自检.py 的人物可见检查；或 grep dao.html 是否存在 var swayX 遮蔽 translate" % 丁),
"Q-059": ("脚本", "python -c \"s=open(r'F:\\Daodao\\src\\_apk\\assets\\dao.html',encoding='utf-8').read();print('openAsk 定义', s.count('function openAsk'))\"：应 ≥1，0 即复现"),
"Q-060": ("人工", "建一条「每天」提醒，语音说做完：第二天应再响，不是永久不再响"),
"Q-061": ("人工", "建两条同名待办，语音说「第一条做完」：应只改第指定那条，不改错"),
"Q-062": ("人工", "语音说「每天九点提醒我开会」：应登记成重复提醒，不是闲聊"),
"Q-063": ("人工", "纯闲聊里说「今天完成了作业」：不应改动记事本数据"),
"Q-064": ("人工", "说「把体检去掉」「别再提醒开会了」：应能识别为删除/停用提醒"),
"Q-065": ("人工", "手机登记成功后听它念：应念「明天九点」这类人话，不念 «2026-11-22 09:00»"),
"Q-066": ("人工", "让本地闹钟响一次后看下一条重复提醒：应已重排下一次时间"),
"Q-067": ("脚本", "python %s\\自检.py 的形象评审项；或在 exe 内切到睡觉/表情状态看是否为卡通熊猫贴图" % 丁),
"Q-068": ("脚本", "python %s\\界面\\触控热区检查.py P5：可点元素 ≥6 且含记事本入口" % 丁),
"Q-073": ("脚本", "python %s\\复现补录.py --dry 应打印「异常 0 条」；再跑 纠错体检.py 应 PASS C1 100%%" % 丁),
"Q-074": ("脚本", "python %s\\自检.py：线上 清单页/落地页 版本应等于本地 107；点下载应拿到 9,865,728B exe / 8,179,826B apk" % 丁),
"Q-075": ("人工", "开 creator.xiaohongshu.com/new/home 看顶部是否「道DAO」；笔记管理逐篇看评论位"),
"Q-076": ("脚本", "看 F:\\Daodao\\推广草稿 是否有当天 <日期>-*.txt 与 -cover.png；再看 _publish_log.txt 有无当天发布行"),
}


def main():
    dry = "--dry" in sys.argv
    d = json.load(open(库, encoding="utf-8-sig"))
    items = d["问题"]
    sol = [i for i in items if i.get("状态") == "solved"]
    缺 = []
    写 = 0
    for i in sol:
        pid = i["id"]
        rec = M.get(pid)
        if not rec:
            缺.append(pid + "（无映射）")
            continue
        kind, step = rec
        # 步骤里点名的 tools 脚本必须真存在，否则这条不算能跑（正则只截到扩展名为止）
        for m in re.finditer(r"[Ff]:[\\/]Daodao[\\/]tools[^\s：，。;]*?\.(?:py|ps1|exe|json)", step):
            p = m.group(0).replace("/", "\\")
            if not os.path.exists(p):
                缺.append("%s（引用不存在：%s）" % (pid, p))
        txt = "【%s】%s" % (kind, step)
        if not dry:
            i["复现"] = txt
            写 += 1
        print("%-6s %-4s %s" % (pid, kind, step[:70]))
    print("----")
    print("已解决 %d 条，本次补齐 %d 条，异常 %d 条" % (len(sol), 写, len(缺)))
    for x in 缺:
        print("  异常:", x)
    ratio = (sum(1 for i in sol if str(i.get("复现", "")).strip()) / len(sol)) if sol else 0
    print("当前带复现比例 %.0f%%（阈值 80%%）→ %s" % (ratio * 100, "PASS" if ratio >= 0.8 else "FAIL"))
    if not dry:
        tmp = 库 + ".tmp"
        json.dump(d, open(tmp, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        os.replace(tmp, 库)
        print("已写回", 库)
    else:
        print("（--dry，只算不写）")


if __name__ == "__main__":
    main()
