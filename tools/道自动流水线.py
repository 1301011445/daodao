# -*- coding: utf-8 -*-
# 程序版本：v0.1 | 2026-11-22 | 基线建档（此前无版本头）
"""道 · 自动流水线（2026-11-20 建｜v65 自治层）

目的：把「每次都要问人」换成「按规则自己决定、自己跑、自己记账」。
用户 2026-11-20 明确要求：更加智能化、动态化、创造化、自动化，不要老让人点允许。

一、它自己决定什么（不需要问人）
  1) 下一首写哪个题材 —— 按题材轮换池「最久未用优先」，同题材不许连写
  2) 曲库健康 —— 逐首实测 LUFS / 峰值 / 峰均比，越界就标 FAIL 并给出该做的动作
  3) 今天该先干什么 —— 按 P1问题 > 曲库越界 > 待立项 的优先级出「下一步」

二、它仍然要问人的（写死在 自治规则.md 里）
  发布/外发、删除或覆盖用户文件、改沙箱外目录、动账户与登录态。

三、输出
  F:\\Daodao\\自我状态\\下一首计划.json     —— 下一首的题材、排除项、判据清单
  F:\\Daodao\\自我状态\\自治运行.jsonl      —— 每次运行的决策与证据（追加）
  终端打印一份人看的报告
"""
import importlib.util, io, json, os, sys, datetime, glob

ROOT = r'F:\Daodao'
STATE = os.path.join(ROOT, '自我状态')
MUSIC = os.path.join(ROOT, 'tools', '音乐')
TOOLS = os.path.join(ROOT, 'tools')
AUDIO = os.path.join(TOOLS, '音频')

THEME_POOL = ['故乡', '成长', '年少', '学生生涯激励', '职场励志', '多元素融合']
THEME_RULES = {                       # 每个题材的语气与硬判据（用户定过的口径）
    '故乡':     dict(语气='深沉热爱', 预副歌='要', 时长='170–200 秒', 备注='前奏可带归途特性，但不超过 8 小节'),
    '成长':     dict(语气='婉转动人', 预副歌='要', 时长='170–200 秒', 备注='主歌讲细节、副歌讲大意'),
    '年少':     dict(语气='清亮直接', 预副歌='要', 时长='170–200 秒', 备注='必须用少年声打底'),
    '学生生涯激励': dict(语气='昂扬向上', 预副歌='要', 时长='170–200 秒', 备注='词要积极，不许苦情'),
    '职场励志': dict(语气='轻快坚定', 预副歌='要', 时长='170–200 秒', 备注='节奏轻快，副歌抬升 ≤1 半音硬跳'),
    '多元素融合': dict(语气='按题定', 预副歌='要', 时长='170–200 秒', 备注='每首至少 2 音色，允许混编'),
}

KNOWN = {                              # 已有成品的题材归属（新曲跑出来后追加到这里）
    '归途的月光': '故乡',
    '少年模样': '年少',
    '把好日子扛在肩上': '职场励志',
}


def _load(mod_name, filename, folder=AUDIO):
    spec = importlib.util.spec_from_file_location(mod_name, os.path.join(folder, filename))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def now():
    return datetime.datetime.now().strftime('%Y-%m-%d %H:%M')


def read_json(p, default):
    try:
        return json.load(io.open(p, encoding='utf-8-sig'))
    except Exception:
        return default


def write_json(p, d):
    io.open(p, 'w', encoding='utf-8').write(json.dumps(d, ensure_ascii=False, indent=2))


def theme_state():
    p = os.path.join(STATE, '题材池.json')
    d = read_json(p, None)
    if not d:
        d = dict(说明='题材轮换台账；用了就记日期，挑「最久未用」的写下一首',
                 池=THEME_POOL, 已用={k: '历史' for k, v in KNOWN.items()},
                 归属={t: [k for k, v in KNOWN.items() if v == t] for t in THEME_POOL},
                 最近使用={'故乡': '2026-11-20', '年少': '2026-11-19', '职场励志': '2026-11-18'},
                 正式曲目=list(KNOWN.keys()))
        write_json(p, d)
        return p, d
    d.setdefault('最近使用', {'故乡': '2026-11-20', '年少': '2026-11-19', '职场励志': '2026-11-18'})
    d.setdefault('正式曲目', list(KNOWN.keys()))
    d.setdefault('池', THEME_POOL)
    write_json(p, d)
    return p, d


def pick_theme(d):
    recent = d.get('最近使用', {})

    def rank(t):
        used = recent.get(t)
        return (0 if not used else 1, str(used or ''))   # 没用过的排最前，用过的按日期由早到晚

    return sorted(d['池'], key=rank)[0]


def library():
    """只认「正式曲目」，历史试听/中间母带版不进体检，避免把旧文件当欠账。"""
    official = set(read_json(os.path.join(STATE, '题材池.json'), {}).get('正式曲目') or KNOWN.keys())
    rows = []
    for wav in glob.glob(os.path.join(MUSIC, '*', 'out', '*.wav')):
        name = os.path.splitext(os.path.basename(wav))[0]
        if name not in official:
            continue
        rows.append(dict(曲=name, 路径=wav, 大小=os.path.getsize(wav)))
    return sorted(rows, key=lambda r: r['曲'])


def health(loud):
    rows = []
    for item in library():
        try:
            fs, data = loud.read_wav(item['路径'])
            kw = loud.np.column_stack([loud.k_weight(data[:, c], fs) for c in range(data.shape[1])])
            lufs, _ = loud.integrated_lufs(kw, fs)
            tpdb, _, _ = loud.true_peak_db(data)
            spdb = 20 * __import__('math').log10(max(float(loud.np.max(loud.np.abs(data))), 1e-12))
            dur = data.shape[0] / float(fs)
            crest = spdb - lufs
            bad = []
            if not (-17.0 <= lufs <= -15.0):
                bad.append('LUFS 越界(%.2f，应 -16±1)' % lufs)
            if tpdb > -1.0:
                bad.append('true peak 越界(%.2f dBTP，应 <=-1.0)' % tpdb)
            if not (10.0 <= crest <= 17.0):
                bad.append('峰均比越界(%.2f dB，应 10–17)' % crest)
            if not (170.0 <= dur <= 200.0):
                bad.append('时长越界(%.2f 秒，应 170–200)' % dur)
            rows.append(dict(曲=item['曲'], 秒=round(dur, 2), LUFS=round(lufs, 2),
                             dBTP=round(tpdb, 2), 峰均比=round(crest, 2),
                             结论='PASS' if not bad else 'FAIL', 问题=bad))
        except Exception as e:
            rows.append(dict(曲=item['曲'], 结论='ERROR', 问题=[str(e)]))
    return rows


def open_p1():
    d = read_json(os.path.join(STATE, '问题库.json'), dict(问题=[]))
    out = []
    for q in d.get('问题', []):
        if q.get('状态') == 'solved':
            continue
        if str(q.get('严重度', '')).upper().startswith('P1'):
            out.append('%s %s' % (q.get('id'), q.get('标题', '')))
    return out


def append_log(rec):
    io.open(os.path.join(STATE, '自治运行.jsonl'), 'a', encoding='utf-8').write(
        json.dumps(rec, ensure_ascii=False) + '\n')


def main():
    print('══ 道 · 自动流水线 %s ══' % now())
    loud = _load('loud', '响度体检.py')

    p_theme, tstate = theme_state()
    nxt = pick_theme(tstate)

    hl = health(loud)
    bad = [r for r in hl if r['结论'] != 'PASS']
    p1 = open_p1()

    todo = []
    if p1:
        todo.append(dict(优先=1, 事项='排查未决 P1：' + '；'.join(p1), 动作='先加日志定位，再谈修'))
    if bad:
        todo.append(dict(优先=2, 事项='曲库越界 %d 首：%s' % (len(bad), '、'.join(r['曲'] for r in bad)),
                         动作='python tools\\音频\\母带校正.py <wav> 后复测'))
    todo.append(dict(优先=3, 事项='下一首题材：%s' % nxt,
                     动作='按 THEME_RULES 的语气与预副歌要求写，双音色、170–200 秒、门禁全过再归档'))

    plan = dict(生成时间=now(), 下一首=dict(题材=nxt, **THEME_RULES[nxt],
                                          排除=['同题材连写', '单音色', '无预副歌', '前奏>8小节'],
                                          必过门禁=['8字8音符', '段末末音>=1.5拍', '副歌峰-主歌峰>=7',
                                                    '音域<=16', '副歌RMS/主歌>=1.2', '170–200秒',
                                                    '≥2音色', 'LUFS -16±1', 'dBTP<=-1.0']),
                 曲库健康=hl, 待办=todo)
    write_json(os.path.join(STATE, '下一首计划.json'), plan)

    print('\n【曲库健康】')
    for r in hl:
        print('  %-14s %6s 秒  %6s LUFS  %6s dBTP  %6s dB  %s %s'
              % (r['曲'], r.get('秒'), r.get('LUFS'), r.get('dBTP'), r.get('峰均比'),
                 r['结论'], '、'.join(r.get('问题', []))))
    print('\n【下一步（自己定的顺序）】')
    for t in todo:
        print('  P%d %s → %s' % (t['优先'], t['事项'], t['动作']))
    print('\n【下一首题材】%s  语气=%s  预副歌=%s' % (nxt, THEME_RULES[nxt]['语气'], THEME_RULES[nxt]['预副歌']))
    print('已写 F:\\Daodao\\自我状态\\下一首计划.json')

    append_log(dict(t=now(), 题材=nxt, 曲库=[(r['曲'], r['结论']) for r in hl], P1=len(p1),
                    越界=len(bad)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
