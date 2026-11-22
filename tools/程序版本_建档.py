# -*- coding: utf-8 -*-
"""给常驻程序建立版本头 + 版本记录（一次性建档，之后由 程序版本检查.py 管）"""
import io, os, json, datetime

ROOT = r'F:\Daodao\tools'
OUT_MD = os.path.join(ROOT, '程序版本记录.md')
OUT_JSON = os.path.join(ROOT, '程序版本记录.json')

# 常驻程序白名单（一次性 _xxx 临时件不算）
WL = [
    ('自检.py', os.path.join(ROOT, '自检.py'), '双端+版本链全量体检'),
    ('版本机制.py', os.path.join(ROOT, '版本机制.py'), '六项发版机制'),
    ('版本奖惩.py', os.path.join(ROOT, '版本奖惩.py'), '版本一致/真用结算'),
    ('愉悦值检查.py', os.path.join(ROOT, '愉悦值检查.py'), '愉悦值与问题库巡检'),
    ('纠错体检.py', os.path.join(ROOT, '纠错体检.py'), '复现用例比例'),
    ('学习复现日历.py', os.path.join(ROOT, '学习复现日历.py'), '1/3/7/21 天复现'),
    ('能力激励.py', os.path.join(ROOT, '能力激励.py'), '十项能力结算'),
    ('回忆.py', os.path.join(ROOT, '回忆.py'), '回忆台账'),
    ('问题库.py', os.path.join(ROOT, '问题库.py'), '问题登记/关闭'),
    ('复现补录.py', os.path.join(ROOT, '复现补录.py'), '历史问题复现补录'),
    ('inspect_dao.py', os.path.join(ROOT, 'inspect_dao.py'), '总巡检报告'),
    ('道自动流水线.py', os.path.join(ROOT, '道自动流水线.py'), '每日流水线'),
    ('归档.py', os.path.join(ROOT, '音乐', '学习归档', '归档.py'), '学习归档校验'),
    ('判据检查.py', os.path.join(ROOT, '音乐', '判据检查', '判据检查.py'), '词曲判据 L1-L4'),
    ('触控热区检查.py', os.path.join(ROOT, '界面', '触控热区检查.py'), '44/48/24 三档热区'),
    ('口型时序.py', os.path.join(ROOT, '音频', '口型时序.py'), '音频→24fps 口型时间轴'),
    ('口型判据检查.py', os.path.join(ROOT, '音频', '口型判据检查.py'), '口型 5 条判据'),
    ('响度体检.py', os.path.join(ROOT, '音频', '响度体检.py'), 'LUFS/dBTP 体检'),
    ('check_features.ps1', os.path.join(ROOT, 'check_features.ps1'), '27 项功能体检'),
    ('check_and_feed.ps1', os.path.join(ROOT, 'check_and_feed.ps1'), '巡检+反馈+邮件'),
    ('daily_sync.ps1', os.path.join(ROOT, 'daily_sync.ps1'), '每日同步'),
    ('build_exe.ps1', os.path.join(ROOT, 'build_exe.ps1'), 'exe 编译部署'),
    ('send_mail.ps1', os.path.join(ROOT, 'send_mail.ps1'), '发邮件'),
    ('rotate_icon.ps1', os.path.join(ROOT, 'rotate_icon.ps1'), '图标轮换'),
]

# 今天真改过、要记 v0.2 的
TODAY_CHANGES = {
    '愉悦值检查.py': '修正误报：台账累计超上限属正常，只比「现值 vs 裁剪结果」',
    '版本奖惩.py': '修正路径：LANDING/ONLINE 改指当前落地页与 app_17jdxkgf27q',
}

TODAY = datetime.date.today().isoformat()


def insert_header(path, ver, note):
    raw = io.open(path, encoding='utf-8', errors='ignore').read()
    if '程序版本：' in raw.split('\n\n')[0][:400] or raw.lstrip().startswith('# 程序版本：'):
        return False, raw
    line = '# 程序版本：%s | %s | %s' % (ver, TODAY, note)
    lines = raw.split('\n')
    # 编码声明必须在第 1、2 行，所以插在它后面
    idx = 0
    for i in range(min(2, len(lines))):
        if 'coding' in lines[i]:
            idx = i + 1
    lines.insert(idx, line)
    io.open(path, 'w', encoding='utf-8').write('\n'.join(lines))
    return True, '\n'.join(lines)


rec = {'说明': '常驻程序的版本档案：每改一次必须升版并填改动；一次性 _xxx 临时件不入档', '程序': []}
md = ['# 道 · 程序版本记录', '',
      '规则：常驻程序改动必须升一版并写改动说明；改了不升版由 `程序版本检查.py` 报 WARN。',
      '', '| 程序 | 版本 | 建档/更新 | 用途 | 改动 | 文件改时间 |', '|---|---|---|---|---|---|']

for name, path, use in WL:
    if not os.path.exists(path):
        print('缺文件：', path)
        continue
    mt = datetime.date.fromtimestamp(os.path.getmtime(path)).isoformat()
    if name in TODAY_CHANGES:
        ver, note = 'v0.2', TODAY_CHANGES[name]
    else:
        ver, note = 'v0.1', '基线建档（此前无版本头）'
    ok, _ = insert_header(path, ver, note)
    rec['程序'].append({'名称': name, '路径': path, '版本': ver, '日期': TODAY,
                        '用途': use, '改动': note, '文件修改日': mt,
                        '已插版本头': ok})
    md.append('| %s | %s | %s | %s | %s | %s |' % (name, ver, TODAY, use, note, mt))

io.open(OUT_JSON, 'w', encoding='utf-8').write(json.dumps(rec, ensure_ascii=False, indent=1))
io.open(OUT_MD, 'w', encoding='utf-8').write('\n'.join(md) + '\n')
print('建档 %d 个程序；新插版本头 %d 个' % (len(rec['程序']), sum(1 for p in rec['程序'] if p['已插版本头'])))
