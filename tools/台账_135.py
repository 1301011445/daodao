# -*- coding: utf-8 -*-
"""v135 收尾台账：学习/发版/能力检查/应用对照表/问题库/待优化/经验库/八项(说话·翻译)/歌词学习"""
import io, json, os, sys, importlib

ROOT = r'F:\Daodao'
sys.path.insert(0, os.path.join(ROOT, 'tools'))
TODAY = '2026-11-25'


def app(rel, text, enc='utf-8'):
    p = os.path.join(ROOT, rel)
    with io.open(p, 'a', encoding=enc) as f:
        f.write(text if text.startswith('\n') else '\n' + text)
    print('APP', rel)


# ---------- 1. 学习台账 ----------
app('学习台账.txt',
    '[%s 18:45] 主攻第5类 语音链路（第二个主题：端点检测）：来源 sherpa-onnx VAD API / silero-vad utils_vad.py / NVIDIA NeMo VAD 文档；'
    '做法 新增 VadGate（32ms窗+双门限迟滞+噪声底自适应+最短语音0.25s+收尾0.45s），pet.cs 唤醒能量门改为跟噪声底走；'
    '落到 hear.py（三份同步）+ pet.cs WakeLoop；判据 V5-1~V5-7 全 PASS（端点延迟 0.456s，旧实现最坏 0.75s）；肉眼：说完半秒内就收，空调声不再把道叫醒' % TODAY)

# ---------- 2. 今日所学 ----------
app('今日所学.txt',
    '%s | 语音端点检测：silero/sherpa 的 window/min_speech/min_silence 三参数怎么配，'
    '换成道自己的 VadGate 后收尾从 0.75s 掉到 0.456s，咔哒不再算一句话' % TODAY)

# ---------- 3. 学习排班 第5类 改已学 ----------
p = os.path.join(ROOT, '学习排班.txt')
s = io.open(p, encoding='utf-8').read()
old = '5|Whisper / sherpa-onnx / Vosk|离线语音识别、VAD 断句、唤醒词 —— 目标：听得清、断得准|待学|'
new = '5|Whisper / sherpa-onnx / Vosk|离线语音识别、VAD 断句、唤醒词 —— 目标：听得清、断得准|已学|' + TODAY
assert old in s
io.open(p, 'w', encoding='utf-8', newline='').write(s.replace(old, new, 1))
print('OK 学习排班 第5类已学')

# ---------- 4. 发版记录 ----------
app('发版记录.txt',
    '\n=== v135 语音端点检测升级（%s 18:45）===\n'
    '学习：第5类第二主题 VAD 断句（sherpa-onnx window512/min_sil0.5/min_speech0.25 + silero 参数 + NVIDIA 阈值取舍）。\n'
    '改码：hear.py 新增 VadGate（32ms 窗、双门限迟滞 400/300 随噪声底自适应、最短语音 0.25s、收尾静音 0.45s），record_with_vad 的 150ms 粗块单门限全换掉；pet.cs WakeLoop 能量门 120 定值 → wakeFloor 一阶低通 + 门限=底噪×1.7(夹120~600)。\n'
    '判据：tools\\语音\\vad_判据.py V5-1~V5-7 全 PASS（收尾延迟 0.456s、底噪200不误触、0.12s咔哒不算一句）。\n'
    '出包：exe 13702144（APP_VER=135，BUILD_OK proc=1 res=214）；apk 29065505（vc135/vn1.35、HTML_VER=135）。\n'
    '发页：清单页/落地页 data-ver 130→135、短链换新，线上抽查两页均回 135。\n' % TODAY)

# ---------- 5. 版本账本 ----------
lp = os.path.join(ROOT, '自我状态', '版本账本.json')
d = json.load(io.open(lp, encoding='utf-8'))
d['current'] = 135
d.setdefault('notes', {})['135'] = 'hear.py VadGate 端点检测 + pet.cs 唤醒门自适应；判据 V5-1~V5-7 PASS'
json.dump(d, io.open(lp, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print('OK 版本账本 current=135')

# ---------- 6. 待优化 ----------
app('待优化.txt',
    '107|手机端轻点说话没接自有 VAD（走系统录音+云端识别）|P2|待改|把 hear.py 的 VadGate 参数搬到 dao.html 的录音段，或让手机走电脑 8848 的 /hear\n'
    '108|VAD 还是 rms+频带替身，没上 silero_vad.onnx 真模型|P1|待改|接 sherpa-onnx 的 onnx VAD，先拿「人声 vs 电视人声」两个样本量误判率\n'
    '109|首字延迟 P6 仍测不出（本机无 ffmpeg/解码器）|P3|待改|装 ffmpeg 后量 TTS 帧头到出声的毫秒数')

# ---------- 7. 经验库 ----------
app('经验库.md',
    '%s | 主题：语音端点检测从单门限升级到 silero/sherpa 档位 | 学到：window 512(32ms)、min_speech 250ms、min_silence 0.45~0.5s、双门限迟滞、噪声底自适应 | '
    '来源：csukuangfj.github.io sherpa VAD API / snakers4 silero-vad utils_vad.py / NVIDIA NeMo VAD 文档 | '
    '改动：hear.py VadGate + pet.cs WakeLoop wakeFloor（v135） | 效果：端点延迟 0.456s（旧最坏 0.75s），V5-1~V5-7 全 PASS | '
    '标签：#语音 #动作 #打包 | 状态：已用 | 提交：0c80bb2' % TODAY)

# ---------- 8. 八项·说话 ----------
app('我说的话.txt',
    '说慢点我听得清，说快点我也跟得上，反正你喊我一声我就回头。')

# ---------- 9. 八项·翻译（知识库 3 条中英） ----------
app('知识库.txt',
    '中：我听你说完了再答，不抢话。｜英：I let you finish before I answer.\n'
    '中：屋里再吵，我也分得出是不是你在叫我。｜英：Even in a noisy room, I can tell when it is you calling me.\n'
    '中：说完了停半秒，我就知道该我开口了。｜英：A half-second pause tells me it is my turn to speak.')

# ---------- 10. 问题库登记 ----------
try:
    qk = importlib.import_module('问题库')
    outs = []
    outs.append(qk.register('VAD 仍是 rms+频带替身，没上 silero_vad.onnx 真模型',
                            来源='v135 学习落地', 严重度='P1',
                            说明='替换身对风扇够用，对电视里的人声不够；下一步接 sherpa-onnx onnx VAD 并量误判率',
                            key='vad:model'))
    outs.append(qk.register('手机端轻点说话未接自有 VAD', 来源='v135 学习落地', 严重度='P2',
                            说明='dao.html 走系统录音+云端识别，端点由系统给；要统一得走 /hear 或搬 VadGate 参数',
                            key='vad:mobile'))
    outs.append(qk.register('首字延迟 P6 无法测量（缺解码器）', 来源='v135 学习落地', 严重度='P3',
                            说明='本机没有 ffmpeg/sox，TTS 帧头到出声量不出；先装 ffmpeg 再量',
                            key='speech:firstbyte'))
    print('QK', outs)
except Exception as e:
    print('QK FAIL', repr(e))

print('BOOKKEEPING_OK')
