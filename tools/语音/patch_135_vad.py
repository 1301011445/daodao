# -*- coding: utf-8 -*-
"""v135 第5类（Whisper / sherpa-onnx / Vosk）落地：VAD 断句改成 silero 式状态机
- 32ms 窗（512 样本 @16k），不再 150ms 粗块
- 双门限迟滞 + 自适应噪声底（阈值跟底噪走，换机器不用手调）
- min_speech 0.25s：咔哒/键盘声不再算"说了一句"
- 收尾静音 0.45s（sherpa 默认 0.5，本地实测 0.45 更跟嘴）
"""
import io, os, shutil, sys

ROOT = r'F:\Daodao'
TARGETS = [
    os.path.join(ROOT, 'hear.py'),
    os.path.join(ROOT, 'src', '桌面分身', 'hear.py'),
    os.path.join(ROOT, 'src', '桌面分身', '_bundle', 'hear.py'),
]

CONSTS = '''VAD_MIN = 95         # 这个机器底噪 rms 大约 54，门槛压到 95 才不会把正常说话当静音

# 2026-11-25 第5类（Whisper / sherpa-onnx / Vosk）落地：VAD 断句参数
# 来源 snakers4/silero-vad utils_vad.py（threshold 0.5 / min_speech 250ms / min_silence 100ms / speech_pad）
# 与 sherpa-onnx VAD API（window 512 样本、min_silence 0.5s、min_speech 0.25s、max_speech 5s）。
VAD_WIN = 0.032      # 32ms = 512 样本 @16k，对齐 silero 的分析窗
VAD_MIN_SPEECH = 0.25  # 短于 0.25 秒不算一句话（挡住咔哒、键盘、碰麦）
VAD_STOP_SIL = 0.45     # 说完后静音这么久就收尾（比原来 0.6 少 0.15 秒）
VAD_ON_RMS = 400.0      # 入声门限下限
VAD_OFF_RMS = 300.0     # 出声门限下限（迟滞：进来用高门、出去用低门，边界不抖）
VAD_ON_LOW = 4.0        # 300~3400Hz 能量占比：人声 7~10%，底噪 2~3%
VAD_OFF_LOW = 3.0
'''

GATE = '''
class VadGate(object):
    """2026-11-25 落地：silero/sherpa 式端点检测（双门限 + 自适应噪声底 + 最短语音）。

    与 silero-vad 的对应关系：
    - threshold 0.5 这类置信门限 -> 这里用 rms + 频带占比两路替身（没有神经网络也得有同等语义）
    - min_speech_duration 250ms -> VAD_MIN_SPEECH，挡住咔哒
    - min_silence_duration -> VAD_STOP_SIL，决定"说完了"多快收尾
    - 双门限迟滞，等价于 sherpa 的 threshold 与 neg_threshold 配对
    """

    def __init__(self, block=VAD_WIN, sil_sec=VAD_STOP_SIL, min_speech=VAD_MIN_SPEECH,
                 thresh=None):
        self.block = float(block)
        self.sil_sec = float(sil_sec)
        self.min_speech = float(min_speech)
        self.thresh = thresh
        self.floor = 0.0          # 噪声底，慢跟
        self.voiced = False
        self.spoke = False        # 已经确认听见过一句真语音
        self.sil_blocks = 0
        self.speech_blocks = 0
        self.onset_t = 0.0
        self.t = 0.0

    def on_thresh(self):
        if self.thresh is not None:
            return float(self.thresh), float(self.thresh) * 0.8
        on = max(VAD_ON_RMS, self.floor * 2.2)
        off = max(VAD_OFF_RMS, self.floor * 1.6)
        if on > 900.0:
            on = 900.0
        if off > 700.0:
            off = 700.0
        return on, off

    def feed(self, rms, low_pct=None):
        """喂一个 32ms 块，返回这次的判定。"""
        on, off = self.on_thresh()
        rms = float(rms or 0.0)
        band = True if self.thresh is not None else (low_pct is None or float(low_pct) >= VAD_ON_LOW)
        band_off = True if self.thresh is not None else (low_pct is None or float(low_pct) >= VAD_OFF_LOW)
        if self.voiced:
            still = rms >= off and band_off
        else:
            still = rms >= on and band
        self.voiced = still
        if still:
            self.sil_blocks = 0
            self.speech_blocks += 1
            if self.speech_blocks * self.block >= self.min_speech:
                if not self.spoke:
                    self.onset_t = self.t - self.speech_blocks * self.block
                self.spoke = True
        else:
            self.speech_blocks = 0
            self.sil_blocks += 1
            # 噪声底只从"不在说话"的块学，慢跟（τ≈10 块≈0.32s）
            if rms > 0:
                self.floor = rms if self.floor <= 0 else (self.floor * 0.9 + rms * 0.1)
        self.t += self.block
        return self.voiced

    def should_stop(self, elapsed=None):
        """必须真听见过一句话，且静音够久、录够 0.5 秒，才允许收尾。"""
        el = self.t if elapsed is None else elapsed
        return (self.spoke and self.sil_blocks * self.block >= self.sil_sec and el > 0.5)

'''

OLD_SIG = '''def record_with_vad(max_sec, out_wav, fs=None, block=0.15, sil_sec=0.6, thresh=None,
                    live_rec=None):'''
NEW_SIG = '''def record_with_vad(max_sec, out_wav, fs=None, block=VAD_WIN, sil_sec=VAD_STOP_SIL, thresh=None,
                    live_rec=None):'''

OLD_INIT = '''    sil_blocks = 0
    need_sil = max(1, int(sil_sec / block))
    elapsed = 0.0'''
NEW_INIT = '''    gate = VadGate(block=block, sil_sec=sil_sec, thresh=thresh)
    sil_blocks = 0
    need_sil = max(1, int(sil_sec / block))
    elapsed = 0.0'''

OLD_DECIDE = '''            if thresh is not None:
                voiced = rms_raw >= thresh
            else:
                voiced = (rms_raw > 400.0 and low_pct >= 4.0) or rms_raw > 1200.0
            if voiced:
                sil_blocks = 0
                spoke = True
                if rms_raw > speech_peak:
                    speech_peak = rms_raw
            else:
                sil_blocks += 1'''
NEW_DECIDE = '''            # 2026-11-25：判定交给 VadGate（双门限 + 噪声底 + 最短语音），
            # 不再是"400 与 4% 的单门限，响一下就算说过话"
            voiced = gate.feed(rms_raw, low_pct)
            sil_blocks = gate.sil_blocks
            spoke = gate.spoke
            if voiced and rms_raw > speech_peak:
                speech_peak = rms_raw'''

OLD_STOP = '''            if spoke and sil_blocks >= need_sil and elapsed > 0.5:
                break'''
NEW_STOP = '''            if gate.should_stop(elapsed):
                break'''


def patch(path):
    s = io.open(path, encoding='utf-8').read()
    if 'VadGate' in s:
        print('SKIP already patched', path)
        return False
    assert 'VAD_MIN = 95' in s, path
    s = s.replace('VAD_MIN = 95         # 这个机器底噪 rms 大约 54，门槛压到 95 才不会把正常说话当静音',
                  CONSTS.strip('\n'), 1)
    assert OLD_SIG in s, path
    s = s.replace(OLD_SIG, NEW_SIG, 1)
    assert 'def record_with_vad' in s
    s = s.replace('def record_with_vad(', GATE.lstrip('\n') + '\ndef record_with_vad(', 1)
    assert OLD_INIT in s, path
    s = s.replace(OLD_INIT, NEW_INIT, 1)
    assert OLD_DECIDE in s, path
    s = s.replace(OLD_DECIDE, NEW_DECIDE, 1)
    assert OLD_STOP in s, path
    s = s.replace(OLD_STOP, NEW_STOP, 1)
    bak = path + '.bak_135'
    if not os.path.exists(bak):
        shutil.copy2(path, bak)
    io.open(path, 'w', encoding='utf-8', newline='\n').write(s)
    print('OK', path)
    return True


changed = 0
for t in TARGETS:
    if patch(t):
        changed += 1
print('CHANGED', changed)
