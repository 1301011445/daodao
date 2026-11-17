# -*- coding: utf-8 -*-
import re

def read(p):
    raw = open(p, 'rb').read()
    return raw.decode('utf-8-sig'), raw.startswith(b'\xef\xbb\xbf')

def write(p, s, bom):
    open(p, 'wb').write((b'\xef\xbb\xbf' if bom else b'') + s.encode('utf-8'))

today = '2026-11-17'

# 1) 学习排班：第 4 类 Flutter 动画曲线 → 已学（用正则，容忍行尾竖线差异）
p = r'F:\Daodao\学习排班.txt'
s, bom = read(p)
pat = r'(4\|Flutter 的动画曲线与内插\|[^|\n]*\|)待学\|[^|\n]*\|?'
s2, n = re.subn(pat, r'\1已学|%s|' % today, s, count=1)
assert n == 1, '学习排班第4类未命中'
write(p, s2, bom)
print('排班：第4类 -> 已学')

# 2) 学习台账 +1
p = r'F:\Daodao\学习台账.txt'
s, bom = read(p)
if not s.endswith('\n'):
    s += '\n'
s += (today + ' | Flutter 动画曲线与内插 | 来源：flutter/flutter packages/flutter/lib/src/animation/curves.dart'
      '（Curves.easeOutCubic=Cubic(0.215,0.61,0.355,1.0)、easeOutQuint=Cubic(0.23,1.0,0.32,1.0)，'
      'Cubic.transform 是"按 x 反解 t 再取 y"，用牛顿迭代）'
      ' | 做法：把三次贝塞尔缓动实装成 BezierAxis + CubicEase + EaseOutCubic/EaseOutQuint，'
      '电脑端 pet.cs 走路 bob 的上升段与触地压缩、手机端 dao.html 二次动作 lift 全部改走这两条曲线'
      ' | 效果：触地压缩从 rawBob<0.10 的 1px 阶跃变成连续 1.2px 曲线，落地不再一跳；'
      '手机端越靠肩头的抬升越急、越接近腰部越缓\n')
write(p, s, bom)
print('台账 +1')

# 3) 经验库 +1
p = r'F:\Daodao\经验库.md'
s, bom = read(p)
if not s.endswith('\n'):
    s += '\n'
s += (today + ' | 主题：用 Flutter 真实的三次贝塞尔缓动替掉走路里的阶跃与正弦'
      ' | 学到：easeOutCubic 不是随手写个 sin，它是有确切控制点的三阶贝塞尔，'
      'Cubic.transform 的解法是按 x 牛顿迭代反解参数 t 再取 y；'
      '同一条曲线放到"触地压缩"上，能把原本 rawBob<0.10 时硬加 1px 的阶跃变成连续加压，'
      '1px 的突跳在 60fps 下也看得出来'
      ' | 来源：flutter/flutter · packages/flutter/lib/src/animation/curves.dart'
      '（Curves.easeOutCubic=Cubic(0.215,0.61,0.355,1.0)、Curves.easeOutQuint=Cubic(0.23,1.0,0.32,1.0)）'
      ' | 改动：pet.cs 新增 BezierAxis/CubicEase/EaseOutCubic/EaseOutQuint，'
      'DrawWalkFrames 的 riseBob 改 EaseOutCubic、触地压缩改 1.2f*EaseOutQuint；'
      'dao.html 新增同名 JS 版，分段绘制的 lift 改走曲线；版本 49→50'
      ' | 效果：走路落地先快压后回弹、不再阶跃跳 1px；手机端肩背抬升有加速感'
      ' | 标签：#动作 #缓动 #走路 #两端 | 状态：已用 | 提交：见当日 commit\n')
write(p, s, bom)
print('经验库 +1')

# 4) 同步日志
p = r'F:\Daodao\同步日志.txt'
s, bom = read(p)
if not s.endswith('\n'):
    s += '\n'
s += ('2026-11-17 20:05  更新轮（用户说"跑"，手动执行一轮）| '
      '第零步：12 个 Dao 计划任务 WakeToRun 全 True，RTCWAKE 交流/直流均为 0x1（启用）| '
      '第一步：daily_sync 判定两端本来就是同一版；但当时道没在运行 —— 已按第二步拉起，'
      '进程 1，ping 回 OK|道|49|192.168.2.113|8848，无待装更新，话术 59 / 知识 81 / 记忆 15 行，无崩溃日志 | '
      '第三步推进：第 14 条第 4 类 Flutter 动画曲线已学并落地 —— '
      'pet.cs 新增三次贝塞尔缓动（BezierAxis/CubicEase/EaseOutCubic/EaseOutQuint，参数照搬 '
      'Curves.easeOutCubic=0.215,0.61,0.355,1.0 与 easeOutQuint=0.23,1.0,0.32,1.0），'
      '走路上升段改 EaseOutCubic、触地压缩从"rawBob<0.10 硬加 1px"改成 1.2px 连续曲线；'
      'dao.html 加同名 JS 版，二次动作 lift 改走曲线 | '
      '自更新：APP_VER/HTML_VER/manifest 全部 49→50，exe 12,929,024 字节已编译部署（进程1），'
      'apk 3,440,483 字节 versionCode 50/50.0、签名 v1/v2/v3 全 true、包内页面 MD5 与源一致；'
      '下载页与清单页均 v50 发布 finished | '
      '第五步小红书：没做成 —— Browser Use 会话无标签页（CDP disconnected），'
      '桌面 Chrome 需 main 桌面授权，interaction.request_action 发出后用户跳过，'
      '用户又明确说不在电脑前；今日推广草稿 2026-11-17-v49.txt 已按风格规则写好但未发布，'
      '评论台账 _comment_log.txt 仍 0 行。待用户在电脑前时补做\n')
s += ('2026-11-17 20:05  当日八项（早轮已完成，本轮追加）：说话√（话术59行） 翻译√（知识81行） '
      '学习√（第3类已学；本轮再推第4类 Flutter 曲线） 自更新√（v49→v50，双端+两页） '
      '语音√（口型跟语速） 走路√（本轮 bob 再改 easeOutCubic/easeOutQuint） '
      '表情√（4/5/9/10 旧表情图停用） 图标√（icon_uk，快捷方式1处）\n')
write(p, s, bom)
print('同步日志 +2 条')
