# 程序版本：v0.1 | 2026-11-22 | 一次性：登记 Q-090/Q-091 + 待优化 22/23 + 经验库
import io, json, datetime

T = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')

# 问题库
P = r'F:\Daodao\自我状态\问题库.json'
d = json.load(io.open(P, encoding='utf-8'))
ids = [q['id'] for q in d['问题']]
new = [
 dict(id='Q-090', 标题='点过一次「唱歌」以后再也打不开歌单，歌也点不动（面板状态机漏清引用）',
      来源='用户反馈', 严重度='P1', 状态='solved',
      发现时间='2026-11-22 14:05', 解决时间=T,
      解决说明=('根因两处叠在一起：①stopMusic() 里 remove 了面板却没把 win 置空，musicPanel() 见 win 还非空就只调 stopMusic 直接 return → 面板永久打不开；'
                '②playSong() 起手先调 stopMusic()，点歌的同时把面板一起关掉，于是点完一首就再没入口。'
                '改成三条独立动作：stopAudio() 只管停声音、closePanel() 只管销毁面板并把 win=null，musicPanel 用 closePanel；点歌改走 stopAudio；'
                '另加行高亮 paintRows()（在放的那首显示「♪ 播放中」，播完自动复位）。自测 10 项全过。'),
      scored=True,
      复现='【人工】手机端点「唱歌」→ 选《归途》→ 按 × 关掉 → 再点「唱歌」：歌单应重新弹出；再点另一首应换歌；点正在放的那首应变回「再点一下停」'),
 dict(id='Q-091', 标题='「跟它说话」改成按住说、松手发（对话时长按时间算）',
      来源='用户要求', 严重度='P2', 状态='solved',
      发现时间='2026-11-22 14:05', 解决时间=T,
      解决说明=('原实现是轻点开、再点停的开关式，用户要「按多久说多久」。改为 pointerdown 即开录、按住期间按钮实时显示已按秒数（🔴 说…1.4s），'
                'pointerup 结束并交原生识别；不足 0.35 秒当误触只提示不硬发；pointercancel 或手指滑出后松手走 document 兜底，按 cancel 处理不算这句；'
                '按钮加 touch-action:none 防系统长按菜单吃事件。'),
      scored=False,
      复现='【人工】按住「跟它说话」约 2 秒再松手：按钮应先变红显示秒数，松手后提示「这一句 2.x 秒，发出去了」；轻点一下应提示按太短'),
]
for q in new:
    if q['id'] not in ids:
        d['问题'].append(q)
        print('追加', q['id'])
io.open(P, 'w', encoding='utf-8').write(json.dumps(d, ensure_ascii=False, indent=1))

# 待优化
p = r'F:\Daodao\待优化.txt'
s = io.open(p, encoding='utf-8').read()
if '22.' not in s:
    s = s.rstrip('\n') + '\n22. 按住说话的 0.35 秒误触阈值是拍出来的，要真机手感校准（太快说不完、太慢像卡住）。\n'
    s += '23. 原生 MediaPlayer 如果「成功但静音」（音量被调 0 或走了错音频流）页面没有任何办法知道；需要下一版加一次「播完是否真出过声」的自检或音量读取。\n'
    io.open(p, 'w', encoding='utf-8').write(s)
    print('待优化 +22/23')

# 经验库
p = r'F:\Daodao\经验库.md'
s = io.open(p, encoding='utf-8').read()
s = s.rstrip('\n') + '\n\n## %s 弹出层「关不掉也打不开」多半是引用没清\n' % T
s += '- 现象：点一次功能键以后，第二次怎么点都没反应，功能本身也没报错。\n'
s += '- 根因：关闭函数 remove 了 DOM 节点，却把 JS 里那个 `win` 变量留着；开面板时用 `if (win) return` 判重，于是永远认为「已经开着」。\n'
s += '- 定法：把「停业务」「销毁 UI」「清状态」拆成三个函数，销毁 UI 时一定把引用置空；判重只看引用，不看 DOM 在不在。\n'
s += '- 附带：切换类操作别顺手把面板一起关掉——用户点歌是想接着点第二首，不是想退出。\n'
io.open(p, 'w', encoding='utf-8').write(s)
print('经验库 +1 条')
