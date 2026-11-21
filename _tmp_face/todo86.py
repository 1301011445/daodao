# -*- coding: utf-8 -*-
import io, datetime
now = datetime.datetime.now().strftime("%Y-%m-%d")
todo = """
%s | 语音首字延迟（手机端） | P0 | open | 电脑端 TTS 0.01s 正常；手机端真机首字延迟一直没有实测数字，需在真机上取样（按下说话→首字出声的毫秒数），拿到再谈换引擎
%s | 录音链路分块上传 | P1 | open | 边说边传（1.5s 一片、静音处下刀、2 路并发 ASR、全失败回退整段）方案与补丁已写好，未落到 DaoBridge.java
%s | v0.86 真机验证 | P1 | open | 人物消失只在浏览器 file:// 验过；需用户装 v0.86 后看一眼人物在不在、走路还跳不跳
""" % (now, now, now)
io.open(r"F:\Daodao\待优化.txt", "a", encoding="utf-8").write(todo)
print("待优化已追加 3 条")
io.open(r"F:\Daodao\经验库.md", "a", encoding="utf-8").write(
    "→ 更新：%s 本地已提交 37dc8a6；远端仍拒（账号 suspended，Q-050），未推送\n" % now)
print("经验库补记提交")
