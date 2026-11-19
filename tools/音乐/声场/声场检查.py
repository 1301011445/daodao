# 声场检查：给一首成品量「是不是真立体声、单声道下会不会掉能量」
# 2026-11-19 第22类「立体声与声场」落地脚本
# 只用标准库（本机 python 没有 numpy）：wave + struct + math
# 用法：python 声场检查.py <wav 路径> [--step N]
# 输出末行固定为 SF|相关=…|侧中比=…|判定=…

import sys, wave, struct, math

def read_wav(path):
    w = wave.open(path, 'rb')
    ch = w.getnchannels()
    sr = w.getframerate()
    sw = w.getsampwidth()
    n = w.getnframes()
    raw = w.readframes(n)
    w.close()
    if sw != 2:
        raise SystemExit("只支持 16bit PCM，当前 sampwidth=%d" % sw)
    if ch != 2:
        # 单声道没法谈声场，直接报出来
        return ch, sr, n, None
    data = struct.unpack('<%dh' % (n * 2), raw)
    left = data[0::2]
    right = data[1::2]
    return ch, sr, n, (left, right)

def analyze(left, right, sr, step=400):
    # 每 step 个采样取一帧，180 秒 44.1k 全量算太慢
    ls = left[::step]
    rs = right[::step]
    N = len(ls)
    sl = sum(ls); sr_ = sum(rs)
    ml = sl / N; mr = sr_ / N
    # 相关系数（Pearson）
    cov = 0.0; vl = 0.0; vr = 0.0
    for a, b in zip(ls, rs):
        da = a - ml; db = b - mr
        cov += da * db; vl += da * da; vr += db * db
    corr = 0.0 if (vl <= 0 or vr <= 0) else cov / math.sqrt(vl * vr)
    # 中/侧能量：M=(L+R)/2, S=(L-R)/2
    em = 0.0; es = 0.0
    for a, b in zip(ls, rs):
        m = (a + b) * 0.5; s = (a - b) * 0.5
        em += m * m; es += s * s
    mid_rms = math.sqrt(em / N); side_rms = math.sqrt(es / N)
    ratio_db = -999.0 if side_rms <= 0 else 20 * math.log10(side_rms / max(mid_rms, 1e-9))
    return corr, mid_rms, side_rms, ratio_db

def main():
    if len(sys.argv) < 2:
        raise SystemExit("用法: python 声场检查.py <wav> [--step N]")
    path = sys.argv[1]
    step = 400
    if '--step' in sys.argv:
        step = int(sys.argv[sys.argv.index('--step') + 1])
    ch, sr, n, pair = read_wav(path)
    dur = n / sr
    print("文件: %s" % path)
    print("声道=%d 采样率=%d 帧数=%d 时长=%.2f 秒" % (ch, sr, n, dur))
    if pair is None:
        print("SF|相关=0.00|侧中比=-999dB|判定=单声道（没有声场可言）")
        return
    left, right = pair
    corr, mid, side, ratio = analyze(left, right, sr, step)
    # 判定口径（见 乐谱学习_第22类_立体声与声场.md）：
    # 相关 <0.999 才算左右真有差别；相关 >=0.999 视为双声道复制单声道（假立体声）
    if corr >= 0.999:
        verdict = "假立体声（左右几乎一模一样，只是复制了两份）"
    elif ratio <= -30:
        verdict = "几乎全中置（侧声道太弱，听着仍像单声道）"
    elif corr < 0.3:
        verdict = "过宽（相关低于 +0.3，单声道下会掉能量）"
    else:
        verdict = "真立体声且单声道安全（相关 %+.2f）" % corr
    print("相关系数=%+.3f  中置RMS=%.1f  侧RMS=%.1f  侧中比=%+.1f dB" % (corr, mid, side, ratio))
    print("SF|相关=%+.3f|侧中比=%+.1fdB|判定=%s" % (corr, ratio, verdict))

if __name__ == '__main__':
    main()
