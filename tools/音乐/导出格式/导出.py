# -*- coding: utf-8 -*-
"""导出格式：把渲染出来的 wav 变成《导出标准.md》要求的四件套。

用法：
    python 导出.py <输入.wav> [--name 歌名]

做的事（顺序固定，先母带后转码）：
  1. 读源 wav，拿到它真实的 sr / 声道（不猜、不写死常量——上次 90 秒/180 秒错案就是写死 44100 造成的）
  2. 升到 44.1 kHz、16 bit，写成 <歌名>_44k单声道.wav（源是双声道时才出 _44k立体声.wav）
     - 22050 → 44100 用 2 倍整数补点 + 三点平滑
     - 单声道源绝不复制两份冒充立体声（2026-11-19 修正，之前那版就是假宽度）
  3. 若本机有 ffmpeg（PATH 或 E:\\Tools\\ffmpeg\\bin\\ffmpeg.exe），再出
     <歌名>_192k.m4a（AAC 192k + faststart）与 <歌名>_320k.mp3（ID3v2.3）
  4. 没有 ffmpeg 就只出 wav，并明确打印"编码未做"，不假装完成
"""
import math, os, shutil, struct, subprocess, sys, wave

TARGET_SR = 44100


def read_wav(path):
    with wave.open(path, 'rb') as w:
        ch, sr, sw, n = w.getnchannels(), w.getframerate(), w.getsampwidth(), w.getnframes()
        raw = w.readframes(n)
    if sw != 2:
        raise SystemExit('只支持 16bit wav，当前 %d 字节/样本' % sw)
    s = struct.unpack('<%dh' % (len(raw) // 2), raw)
    if ch > 1:                                  # 多声道取平均，只留作单声道备用
        frames = len(s) // ch
        s = tuple(sum(s[i * ch:(i + 1) * ch]) // ch for i in range(frames))
    return list(s), sr, ch


def upsample(x, sr):
    """整数倍/非整数倍都走线性插值；22050→44100 时退化成 2 倍补点 + 三点平滑。"""
    if sr == TARGET_SR:
        return x
    ratio = TARGET_SR / float(sr)
    n_out = int(len(x) * ratio)
    out = []
    for i in range(n_out):
        pos = i / ratio
        a = int(pos)
        b = min(a + 1, len(x) - 1)
        f = pos - a
        v = x[a] * (1 - f) + x[b] * f
        out.append(v)
    # 三点平滑，压掉补点带来的高频毛刺（[1,2,1]/4）
    sm = [out[0]]
    for i in range(1, len(out) - 1):
        sm.append((out[i - 1] + 2 * out[i] + out[i + 1]) / 4.0)
    sm.append(out[-1])
    return [int(max(-32768, min(32767, v))) for v in sm]


def write_mono(path, s):
    with wave.open(path, 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(TARGET_SR)
        w.writeframes(b''.join(struct.pack('<h', v) for v in s))


def write_stereo(path, s):
    # 只有源本来就是双声道时才走这里；单声道不许复制两份冒充立体声
    with wave.open(path, 'wb') as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(TARGET_SR)
        w.writeframes(b''.join(struct.pack('<hh', v, v) for v in s))


def find_ffmpeg():
    p = shutil.which('ffmpeg')
    if p:
        return p
    for c in (r'E:\Tools\ffmpeg\bin\ffmpeg.exe', r'G:\Tools\ffmpeg\bin\ffmpeg.exe'):
        if os.path.exists(c):
            return c
    return None


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    src = sys.argv[1]
    name = os.path.splitext(os.path.basename(src))[0]
    if '--name' in sys.argv:
        name = sys.argv[sys.argv.index('--name') + 1]

    s, sr, sch = read_wav(src)
    sec = len(s) / float(sr)
    print('源：%d Hz %d 声道 %.2f 秒' % (sr, sch, sec))
    if not (170 <= sec <= 200):
        print('  ! 时长 %.1f 秒不在 170–200 秒口径内，仍按现状导出，请在账本里记为不合格' % sec)

    up = upsample(s, sr)
    out_dir = os.path.dirname(os.path.abspath(src))
    if sch <= 1:
        # 2026-11-19 修正：以前这里把单声道复制成两条一样的轨冒充立体声，
        # 声场检查量出来侧声道 RMS=0（相关 +1.000），属《导出标准》明文禁止的假宽度。
        # 现在源是单声道就老实出单声道；想要真立体声得在编配阶段左右分轨，不能靠导出补。
        wav_out = os.path.join(out_dir, name + '_44k单声道.wav')
        write_mono(wav_out, up)
        print('① 44.1k/16bit 单声道 WAV：%s（%.2f MB）' % (wav_out, os.path.getsize(wav_out) / 1048576.0))
        print('   说明：源为单声道，按红线不造假宽度（真立体声须在编配时分左右轨）')
        wav44 = wav_out
    else:
        wav44 = os.path.join(out_dir, name + '_44k立体声.wav')
        write_stereo(wav44, up)
        print('① 44.1k/16bit 立体声 WAV：%s（%.2f MB）' % (wav44, os.path.getsize(wav44) / 1048576.0))

    ff = find_ffmpeg()
    if not ff:
        print('② ③ 编码未做：本机没有 ffmpeg（PATH 与 E:/G: 均未找到），M4A/MP3 需在云主机转码')
        return
    m4a = os.path.join(out_dir, name + '_192k.m4a')
    mp3 = os.path.join(out_dir, name + '_320k.mp3')
    meta = ['-metadata', 'title=' + name, '-metadata', 'artist=道', '-metadata', 'album=道·音乐']
    subprocess.run([ff, '-y', '-loglevel', 'error', '-i', wav44, '-c:a', 'aac', '-b:a', '192k',
                    '-movflags', '+faststart'] + meta + [m4a], check=True)
    subprocess.run([ff, '-y', '-loglevel', 'error', '-i', wav44, '-c:a', 'libmp3lame', '-b:a', '320k',
                    '-id3v2_version', '3'] + meta + [mp3], check=True)
    print('② AAC 192k：%s（%.2f MB）' % (m4a, os.path.getsize(m4a) / 1048576.0))
    print('③ MP3 320k：%s（%.2f MB）' % (mp3, os.path.getsize(mp3) / 1048576.0))


if __name__ == '__main__':
    main()
