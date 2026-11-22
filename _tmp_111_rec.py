# 一次性：把 0.111 那条记录里的 apk 链接/摘要改成重打包后的值，并补一段「自查出来的三个坑」
import io

P = r'F:\Daodao\发版记录.txt'
s = io.open(P, encoding='utf-8').read()
s = s.replace('sha256_8b66c4bfd814f9e8', 'sha256_77bd8f0786c51b0')
s = s.replace('https://aka.doubaocdn.com/s/oU3jGP8N7b', 'https://aka.doubaocdn.com/s/B12kqwOPN6')

tail_note = '''- 重打包自查出三个会上手机就死的坑，已修并重出包（apk 字节不变 8,196,174，摘要改 77bd8f0786c51b0，链接改 s/B12kqwOPN6）：
  ① layout() 里 lp 从来没 new，第一次挂窗口必 NPE 把服务带崩；顺手把 lp.type（TYPE_APPLICATION_OVERLAY / 老机 TYPE_PHONE）和 gravity 显式设上
  ② 用 startForegroundService 叫起来的服务，哪怕这次 A_STOP 是来关门的，也必须在 5 秒内先 startForeground，否则系统按「没按时转前台」判崩
  ③ onDestroy 里调 hideView() 会顺手 notify 一条通知，服务都死了还留一条僵尸通知；改为只拆窗口 removeView()
'''
if '重打包自查出三个' not in s:
    s = s.rstrip('\n') + '\n' + tail_note
io.open(P, 'w', encoding='utf-8').write(s)
print('ok')
