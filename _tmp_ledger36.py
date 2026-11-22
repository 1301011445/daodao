# 程序版本：v0.1 | 2026-11-22 | 一次性：写台账（第36类许嵩 + 形象评审/Q-083）+ 补判据 L12/L13
import io, json, datetime, os

T = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')

# 1) 音乐判据总表追加 L12 / L13
p = r'F:\Daodao\音乐判据总表.md'
s = io.open(p, encoding='utf-8').read()
if 'L12' not in s:
    s += '\n\n## L12 / L13（第36类 许嵩式国风流行，2026-11-22 新增）\n\n'
    s += '- **L12 副歌首句含具体物象**：副歌第一句 ≥1 个具体名词（桥/雪/月/灯/船/窗/雨/街/灶/车…），抽象词（寂寞、忧伤、思念、孤独）不得单独撑起首句。\n'
    s += '- **L13 民族音色标签唯一**：全曲标志性民族乐器只允许 1 件；该件在主歌段电平比副歌低 ≥6 dB（主歌藏、副歌全开）。\n'
    s += '- 配套：L11（副歌相邻句字数相等且 ≤9 字、至少转韵一次）已有；第14类副歌音区差 ≥7 半音；第21类末段升 key +1~+2。\n'
    s += '- 学习来源与拆解见 `乐谱学习_第36类_许嵩式国风流行.md`。\n'
    io.open(p, 'w', encoding='utf-8').write(s)
    print('判据总表 +L12/L13')

# 2) 学习排班补第 36 类
p = r'F:\Daodao\学习排班.txt'
s = io.open(p, encoding='utf-8').read()
if '第36类' not in s and '36|' not in s:
    s = s.rstrip('\n') + '\n36|许嵩式国风流行（旋律独立性、意象咬合、单标签民族音色）|F:\\Daodao\\乐谱学习_第36类_许嵩式国风流行.md + 判据 L12/L13|已学|2026-11-22|只进判据不写新歌；待用三首老歌真跑 L12 排序\n'
    io.open(p, 'w', encoding='utf-8').write(s)
    print('学习排班 +36')

# 3) 学习台账追加
p = r'F:\Daodao\学习台账.txt'
s = io.open(p, encoding='utf-8').read()
s = s.rstrip('\n') + '\n' + T + ' | 第36类 许嵩式国风流行 | 来源：酷狗艺人百科（生平/专辑序列）、抖音百科《不如吃茶去》专辑鉴赏（古筝+笛+吉他/尺八+电鼓+失真吉他、旋律可抽离编配）、中华网（词不堆砌词藻、国风是舒适区）、原创力文档（古风脉络 2007 断桥残雪起）| 拆 6 条手艺 → 判据 L12（副歌首句含具体物象）、L13（民族音色标签唯一且主歌低 6dB）| 落地：音乐判据总表已加两条；曲风库待加「许嵩式国风流行」轮换 | 没做：不写新歌、没做抽伴奏自动判据 |\n'
io.open(p, 'w', encoding='utf-8').write(s)
print('学习台账 +1 条')

# 4) 学习复现台账
p = r'F:\Daodao\学习复现台账.txt'
s = io.open(p, encoding='utf-8').read()
s = s.rstrip('\n') + '\n2026-11-22|第36类|F:\\Daodao\\tools\\形象\\评审.py --frames（形象侧）+ 旋律和声贴合/高点分布为复用|L12/L13 已入判据表待真跑；形象 A9 25 帧 PASS（表情互差22.9、走路下半身纵84px横92px、头顶带0.10%）\n'
io.open(p, 'w', encoding='utf-8').write(s)
print('复现台账 +1 条')

# 5) 曲风库与轮换表加一条题材/曲风
p = r'F:\Daodao\曲风库与轮换表.md'
s = io.open(p, encoding='utf-8').read()
if '许嵩式' not in s:
    s = s.rstrip('\n') + '\n\n- **许嵩式国风流行（2026-11-22 入库）**：半文半白；五声骨架＋一处偏音；标志乐器只认古筝或笛；主歌 2 层、副歌 4 层；副歌首句 ≤9 字且带具体物象。与「古风」「戏曲腔」错开轮换，不连着用。\n'
    io.open(p, 'w', encoding='utf-8').write(s)
    print('曲风库 +许嵩式')

# 6) 问题库：Q-080 solved、Q-083 补进展
p = r'F:\Daodao\自我状态\问题库.json'
d = json.load(io.open(p, encoding='utf-8'))
for q in d['问题']:
    if q['id'] == 'Q-080':
        q['状态'] = 'solved'
        q['解决时间'] = T
        q['解决说明'] = ('已建 tools\\形象\\评审.py：①素材模式扫品红/边带/透明处残留色；②--frames 模式评审 exe 渲染帧。'
                        '真跑 E:\\Daodao 25 帧：表情 12 张最大互差 22.9 灰度级、平均 13.6；走路 8 帧下半身差异纵向 84px/横向 92px、头顶带仅 0.10% → A1-A5 全 PASS（A9|frames=25|PASS）。'
                        '第一版用整张 alpha 量步幅，因帧内带不透明场景全画布满 alpha 而误报 FAIL，已改「相对中位帧差分」。')
        q['scored'] = True
    if q['id'] == 'Q-083':
        q['解决说明'] = (q['解决说明'] + '｜2026-11-22 13:55 量化：角色 sprite（apk 内 walk8.png 1536x384）品红 0、边带 0；'
                        '问题在内嵌 86 张 webp：34 张在 alpha<40 的边带有品红，共 5718 px，另有 462,692 个「alpha=0 但 RGB 仍亮」的像素（缩放插值时渗出即紫晕）。'
                        '已改 dao.html 加 SPR()：绘制前 alpha<6 归零 RGB、6≤alpha<40 且偏紫则把绿抬到 (R+B)/2，6 处 drawImage 全包一层；'
                        '按同一规则离线复算：边带品红 5718→0。真机观感待新包确认。')
        q['停滞天数'] = 0
io.open(p, 'w', encoding='utf-8').write(json.dumps(d, ensure_ascii=False, indent=1))
print('问题库 Q-080 solved / Q-083 补进展')

# 7) 程序版本记录：登记 形象\评审.py
p = r'F:\Daodao\tools\程序版本记录.json'
d = json.load(io.open(p, encoding='utf-8'))
if not any(x['名称'] == '评审.py' for x in d['程序']):
    d['程序'].append(dict(名称='评审.py', 路径=r'F:\Daodao\tools\形象\评审.py', 版本='v0.1', 日期='2026-11-22',
                          用途='形象素材品红/边带体检 + exe 渲染帧 A9 评审', 改动='新建：素材 4 条判据 + 渲染帧 A1-A5（表情差异、步幅、头顶带）',
                          文件修改日='2026-11-22', 已插版本头=True))
    io.open(p, 'w', encoding='utf-8').write(json.dumps(d, ensure_ascii=False, indent=1))
    print('版本档案 +评审.py，共', len(d['程序']))
