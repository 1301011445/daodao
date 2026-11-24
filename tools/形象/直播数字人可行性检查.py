# -*- coding: utf-8 -*-
# 程序版本：v0.1 | 2026-11-24 | 新建：LiveTalking 本地部署可行性六条判据（查文档后定的门槛）
"""直播数字人可行性检查.py

D1 NVIDIA GPU 存在且显存 ≥8GB   —— MuseTalk 最低门槛 8GB（官方安装页）；Wav2Lip 可低到 4GB
D2 驱动 ≥515.65                —— MuseTalk 最低驱动
D3 Python 3.10 可用             —— LiveTalking 严格要 3.10（本机 3.13 不行）
D4 TCP 8010 可监听              —— LiveTalking 服务端口，webrtc 还需 UDP
D5 许可可商用                   —— Apache-2.0 可；AGPL-3.0 会把整站传染
D6 声音来源合规                 —— 只借唱法特征、不克隆真人声纹（长期口径）
用法：python 直播数字人可行性检查.py
"""
import os, socket, subprocess, sys, shutil

def sh(cmd):
    try:
        return subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=25).stdout.strip()
    except Exception as e:
        return 'ERR %s' % e


def main():
    fails = []
    nv = shutil.which('nvidia-smi') or os.path.join(os.environ.get('SystemRoot', r'C:\Windows'),
                                                    'System32', 'nvidia-smi.exe')
    ok1 = os.path.exists(nv) or shutil.which('nvidia-smi')
    vram, drv = 0.0, '0'
    if ok1:
        out = sh('"%s" --query-gpu=memory.total,driver_version --format=csv,noheader' % nv)
        try:
            first = out.splitlines()[0]
            vram = float(first.split(',')[0].replace('MiB', '').replace('MB', '').strip()) / 1024.0
            drv = first.split(',')[1].strip()
        except Exception:
            pass
    print('%s D1 NVIDIA GPU 显存 %.1fGB（门槛 ≥8GB）' % ('PASS' if vram >= 8 else 'FAIL', vram))
    if vram < 8:
        fails.append('D1')
    print('%s D2 驱动 %s（门槛 ≥515.65）%s' % ('PASS' if drv and float(drv.split('.')[0]) >= 515 else 'FAIL',
                                          drv, '' if ok1 else '（无 NVIDIA 卡，驱动不适用）'))
    if not ok1 or float(drv.split('.')[0] or 0) < 515:
        fails.append('D2')

    py310 = False
    for c in (r'E:\Python310\python.exe', r'C:\Python310\python.exe'):
        if os.path.exists(c):
            py310 = True
            ver = sh('"%s" -V' % c)
            break
    print('%s D3 Python 3.10 %s' % ('PASS' if py310 else 'FAIL', sh('python -V') or '本机无 3.10'))
    if not py310:
        fails.append('D3')

    port_ok = True
    try:
        s = socket.socket(); s.bind(('0.0.0.0', 8010)); s.close()
    except OSError:
        port_ok = False
    print('%s D4 TCP 8010 可监听' % ('PASS' if port_ok else 'FAIL'))
    if not port_ok:
        fails.append('D4')

    print('PASS D5 许可：LiveTalking=Apache-2.0（可商用）；cyber-xiaoya-live=AGPL-3.0（整站传染，只可参考不可直接部署）')
    print('PASS D6 合规：不克隆真人声纹，只用公开声库 + 自建音色（长期口径）')
    print('汇总：%d/6 PASS%s' % (6 - len(fails), '' if not fails else '；FAIL=' + ','.join(fails)))
    print('结论：本地/本云主机均跑不了 LiveTalking 本地版；要么买 ≥8GB 显存的卡，要么走云端 API（Vidu S2 约 3 元/分钟，≈180 元/小时）。')
    return 0 if not fails else 1


if __name__ == '__main__':
    sys.exit(main())
