# -*- coding: utf-8 -*-
import io, sys, importlib

spec = r'E:\Daodao\每日任务说明.md'
s = io.open(spec, encoding='utf-8').read()
s = s.replace('# 道 · 每日定时任务说明（v14，2026-11-22 更新）',
              '# 道 · 每日定时任务说明（v15，2026-11-22 更新）', 1)
if '## 程序版本记录' not in s:
    s = s.rstrip('\n') + '''

---

## 程序版本记录（2026-11-22 新增，v15）

用户 2026-11-22：**「各项程序都要定期优化更新，最好有版本记录」**。

### 一、谁算"程序"

`F:\\Daodao\\tools\\程序版本记录.json` 里的 **24 个常驻程序**才算（自检、版本机制、版本奖惩、愉悦值检查、纠错体检、学习复现日历、能力激励、回忆、问题库、复现补录、inspect_dao、道自动流水线、归档、判据检查、触控热区检查、口型时序、口型判据检查、响度体检、check_features、check_and_feed、daily_sync、build_exe、send_mail、rotate_icon）。

`tools` 目录里大量 `_xxx.py` 是一次性临时件，**不入档、不追版本**；清理时按第 21 条处理。

### 二、每个程序必须有版本头

文件第 1 行（.py 在编码声明之后）必须是一行：

`# 程序版本：vX.Y | 日期 | 一句话改动`

### 三、改动必须升版（这是硬规则）

改任何常驻程序，改完立刻：

`python F:\\Daodao\\tools\\程序版本检查.py --bump <文件名> --note "改了什么"`

不升版就改文件，检查会报 WARN「改了没升版」，不算完成。

### 四、定期优化

- 体检轮固定跑一次 `程序版本检查.py`（约 0.1s），PASS 才算巡检合格。
- 某程序 **30 天没动过**，检查会列进"该轮到优化"，当天挑一项真改（不是改注释凑数）。
- 一次只优化 1–2 个程序，改完必须能跑通并留证据。

### 五、建档当天的一次性说明

2026-11-22 建档时给 24 个文件都写了版本头，所以它们当天全被"碰过"，30 天计时从今天起算；这不代表它们都被优化过，`改动` 一栏写的是真实内容（v0.1=基线建档，v0.2=当天真改过的那两个）。
'''
io.open(spec, 'w', encoding='utf-8').write(s)
print('说明升 v15，追加「程序版本记录」一节')

def app(p, t):
    with io.open(p, 'a', encoding='utf-8') as f:
        f.write(t.rstrip('\n') + '\n')

app(r'F:\Daodao\能力检查\2026-11-22.md', '''
### 12:52 追加（程序版本记录机制，用户「各项程序都要定期优化更新」）

- 清点：`tools` 下 180+ 个脚本，真正常驻的 **24 个**（其余是 `_xxx` 一次性件）。给这 24 个都插了版本头，并建 `tools\\程序版本记录.json` / `.md`。
- 新工具 `tools\\程序版本检查.py`：
  - 检查模式：缺版本头 / 头版本与记录不符 = FAIL；文件改过但记录没升版 = WARN；30 天没动 = 列"该轮到优化"。
  - 升版模式：`--bump <文件> --note "…"`，自动把 v0.2 升到 v0.3 并写记录。
- 真跑：`PROGVER|n=24|缺头或错版=0|未升版=0|待优化轮换=0|PASS`，退出码 0。
- 建档时踩了个坑：PowerShell 脚本的 BOM 被新插的版本头挤到第二行，`check_features.ps1` 直接 ParserError（MissingEndCurlyBrace）。修法是版本头必须落在 BOM 之后第一行、以 utf-8-sig 重写；复测 27/27 正常、退出码 0。已记 Q-084 并当场关闭。
- 说明文件升 **v15**，新增「程序版本记录」一节（谁算程序、版本头格式、改动必须 --bump、30 天轮换、建档当天的一次性说明）。
''')

app(r'F:\Daodao\同步日志.txt', '2026-11-22 12:52  程序版本记录机制落地：24 个常驻程序插版本头 + 程序版本记录.json/md + 程序版本检查.py（PROGVER PASS）；修 ps1 BOM 被挤错位导致 check_features 解析失败（Q-084 关闭）；说明升 v15')
app(r'F:\Daodao\经验库.md', '2026-11-22 | 主题：给上百个脚本上版本账 | 学到：只给"常驻程序"建档（24 个），一次性件不入档；版本头必须保持编码声明/BOM 位置，否则 ps1 直接解析失败 | 来源：自查 tools 目录清单 | 改动：新增 tools\\程序版本记录.{json,md}、程序版本检查.py（含 --bump）、程序版本_建档.py、程序版本_修PS1.py；24 个程序加版本头 | 效果：PROGVER 24/0/0/0 PASS；check_features 27/27 复测通过 | 标签：#巡检 #版本 #工具链 | 状态：已用 | 提交：未提交（工具与说明文件，待随源码提交）')

sys.path.insert(0, r'F:\Daodao\tools')
qb = importlib.import_module('问题库')
qb.register('给 ps1 插版本头把 BOM 挤到第二行，check_features.ps1 解析失败',
            来源='程序版本_建档.py', 严重度='P3',
           说明='版本头插在首行、BOM 落到第二行，PowerShell 报 MissingEndCurlyBrace；改为版本头放 BOM 之后、以 utf-8-sig 重写全部 6 个 ps1', key='tool:bom')
qb.close('Q-084', note='6 个 ps1 全部以 utf-8-sig 重写、版本头置首行；复测 check_features.ps1 27/27 正常、EXIT=0', 复现='powershell -File F:\\Daodao\\tools\\check_features.ps1 应输出「正常 27 项，缺 0 项」，EXIT=0')
print('done')
