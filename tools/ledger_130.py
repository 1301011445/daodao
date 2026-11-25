# -*- coding: utf-8 -*-
"""v130 台账"""
import json, os

rec = ('2026-11-25 v130 语音/对话/实时语音更新 + 坐骑自主\n'
       '  · 对话：MODEL_CHAIN 真接进请求（flash→4.7-flash→air，退一次等 0.4s*n）；本机秒答（几点/日期/算数）\n'
       '  · 语音：整段合成改成逐句合成播（首句 TTS_FIRST≈1.5~2.0s），按标点给 0.10~0.22s 停顿；'
       '放音每 40ms 查停止标记可随时掐断\n'
       '  · 实时：voice.py talk 多轮连续对话（听完即想，说「别说了」退出，连续两轮听不清自己收麦），'
       '桌面菜单「连着聊几句：不用每次点」接上\n'
       '  · 坐骑：mountAuto 默认开——每次启动六成概率自己挑一只、四成不骑；点按钮即接管，长按 600ms 交还给道\n'
       '  apk 17,087,029 https://aka.doubaocdn.com/s/kCZwQFUyD4，exe 13,681,664 https://aka.doubaocdn.com/s/RrFpjWijzq，'
       '两页 data-ver=130\r\n')
p = r'F:\Daodao\发版记录.txt'
s = open(p, encoding='utf-8').read()
if 'v130 语音' not in s:
    open(p, 'a', encoding='utf-8').write(rec)
print('发版记录 OK')

led = r'F:\Daodao\自我状态\版本账本.json'
d = json.load(open(led, encoding='utf-8'))
d.setdefault('versions', []).append({
    'ver': 130, 'date': '2026-11-25', 'title': '语音/对话/实时语音升级 + 坐骑自主',
    'apk': 17087029, 'apk_link': 'https://aka.doubaocdn.com/s/kCZwQFUyD4',
    'exe': 13681664, 'exe_link': 'https://aka.doubaocdn.com/s/RrFpjWijzq',
})
d['current'] = 130
json.dump(d, open(led, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print('版本账本 current=130')

chk = r'F:\Daodao\能力检查\2026-11-25.md'
s = open(chk, encoding='utf-8').read() if os.path.exists(chk) else '# 2026-11-25\n'
if 'v130' not in s:
    s += ('\n## v130 语音 / 对话 / 实时语音 + 坐骑自主（2026-11-25）\n'
          '- 对话程序：MODEL_CHAIN 之前只定义没使用（429 就整轮失败），现在真按 flash→4.7-flash→air 退，'
          '失败间隔 0.4s*i；新增 instant_answer（几点/几号/星期/四则），本机 0 网络\n'
          '- 语音程序：edges-tts 由整段改逐句，split_sentences 先句末标点再逗号再硬切（max 34 字），'
          '句间停顿 。0.20 ！0.22 ？0.22 ；0.18 ，0.10；放音 _play_interruptible 每 40ms 查 _STOP\n'
          '- 实时语音：voice.py talk 多轮；测试 voice.py selftest 6/6 PASS（分句/情绪/时间/算数/模型链/记忆）；'
          'tts 实测首句 1.48~2.01s；ask 实测 1.6s 返回「在陪主人聊天。」；listen 实测 rms 7249、text 空（管线通）\n'
          '- 桌面：pet.cs 新增 TalkLoop 读 talk 的 JSON 行，气泡只显示不再重复念（避免两边抢麦）\n'
          '- 坐骑：mountAuto 默认 true，启动 60% 概率自己挑 1~5、40% 不骑；setMountArt 置 false 表示用户接管；'
          'DaoOverlay.setMountAuto 静态入口 + DaoBridge.setMountAuto；页面长按 600ms 交还\n'
          '- 踩坑：DaoBridge 里没有 dao 字段，必须走 DaoOverlay 的 sLive 静态入口；'
          '内部类不能有 static 数组成员（v127 已记）\n')
    open(chk, 'w', encoding='utf-8').write(s)
print('能力检查 OK')
