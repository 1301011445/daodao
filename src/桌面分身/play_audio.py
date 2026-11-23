# -*- coding: utf-8 -*-
"""播放一句合成好的语音：mp3/wav 都行。

两个模式（对外还是一句命令，exe 不用改）：
  1) 常驻：第一次调用时后台起一个常驻进程，imports/声卡/滤镜只付一次
  2) 客户端：之后每句只把文件路径发给常驻进程，秒接，不重开进程

这台机器上 miniaudio 1.73 解 mp3 报 -7，主路径走 soundfile。
对外吐给主程序对嘴型：
  DEC=<毫秒>   音频真实长度
  START        真正出声那一刻
"""
import os
import socket
import sys
import threading

HOST = "127.0.0.1"
PORT = 8917
_server_ready = threading.Event()


def decode(path):
    import numpy as np
    try:
        import soundfile as sf
        x, sr = sf.read(path, dtype="float32", always_2d=False)
        return x if x.ndim == 2 else x.reshape(-1, 1), int(sr)
    except Exception:
        import miniaudio
        d = miniaudio.decode_file(path, output_format=miniaudio.SampleFormat.FLOAT32)
        a = np.frombuffer(d.samples, dtype=np.float32).copy()
        ch = int(d.nchannels)
        return (a.reshape(-1, ch) if ch > 1 else a.reshape(-1, 1)), int(d.sample_rate)


def soften(pcm, sr):
    try:
        from 人声滤镜_biquad import apply_chain
        x = pcm[:, 0] if pcm.shape[1] > 1 else pcm.reshape(-1)
        return apply_chain(x, sr).reshape(-1, 1)
    except Exception:
        return pcm


def serve():
    import numpy as np
    import sounddevice as sd
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((HOST, PORT))
    srv.listen(4)
    _server_ready.set()
    while True:
        conn, _ = srv.accept()
        try:
            data = b""
            while not data.endswith(b"\n"):
                chunk = conn.recv(4096)
                if not chunk:
                    break
                data += chunk
            path = data.decode("utf-8", "replace").strip()
            if not path:
                conn.sendall(b"ERR empty\n")
                continue
            if path == "__PING__":
                conn.sendall(b"END\n")
                continue
            pcm, sr = decode(path)
            ms = int(len(pcm) / sr * 1000)
            pcm = soften(pcm, sr)
            conn.sendall(("DEC=%d\nSTART\n" % ms).encode("utf-8"))
            sd.play(np.clip(pcm, -1, 1), sr, blocking=False)
            sd.wait()
            conn.sendall(b"END\n")
        except Exception as e:
            try:
                conn.sendall(("ERR %r\nEND\n" % (e,)).encode("utf-8"))
            except Exception:
                pass
        finally:
            try:
                conn.close()
            except Exception:
                pass


def spawn_server():
    import subprocess
    kwargs = dict(stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL)
    if os.name == "nt":
        kwargs["creationflags"] = 0x00000008 | 0x00000200   # DETACHED_PROCESS | NEW_PROCESS_GROUP
    subprocess.Popen([sys.executable, "-X", "utf8", os.path.abspath(__file__), "--serve"], **kwargs)


def talk(path, timeout=5.0):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    s.connect((HOST, PORT))
    s.settimeout(None)
    s.sendall((path + "\n").encode("utf-8"))
    buf = b""
    while b"END" not in buf:
        chunk = s.recv(4096)
        if not chunk:
            break
        buf += chunk
    s.close()
    return buf.decode("utf-8", "replace")


def main():
    if len(sys.argv) < 2:
        print("USAGE: play_audio.py <file.mp3|file.wav>")
        sys.exit(1)
    if sys.argv[1] == "--serve":
        serve()
        return
    path = sys.argv[1]
    out = ""
    import time
    for attempt in range(3):
        try:
            out = talk(path)
            break
        except Exception:
            if attempt == 0:
                spawn_server()
                time.sleep(0.7)
            else:
                time.sleep(0.4)
    if not out:
        # 常驻进程起不来就退回老办法：自己解码自己播
        import numpy as np
        import sounddevice as sd
        pcm, sr = decode(path)
        print("DEC=%d" % int(len(pcm) / sr * 1000), flush=True)
        pcm = soften(pcm, sr)
        sd.play(np.clip(pcm, -1, 1), sr, blocking=False)
        print("START", flush=True)
        sd.wait()
        print("PLAYED")
        return
    for line in out.splitlines():
        if line.strip():
            print(line.strip(), flush=True)


if __name__ == "__main__":
    main()
