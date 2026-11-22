# -*- coding: utf-8 -*-
import io, sys, importlib
sys.path.insert(0, r'F:\Daodao\tools')
qb = importlib.import_module('问题库')
qb.register('版本奖惩.py 指向旧引导页源与旧 app，导致「五处不一致」假报警',
            来源='版本奖惩.py', 严重度='P2',
            说明='LANDING 指 引导页_src\\index.html（data-ver 停在 69）、ONLINE 指 app_17hnj8acgs2（线上仍 62）；已改指当前落地页源与 app_17jdxkgf27q，重跑 VSTATE=OK', key='version:stale-path')
qb.close('Q-082', note='LANDING 改为 道落地页\\道_落地页_v069.html，ONLINE 改为 app_17jdxkgf27q；重跑 版本奖惩：电脑/手机/页面/线上/手机上报 = 107，VSTATE=OK', 复现='python F:\\Daodao\\tools\\版本奖惩.py，末行应为 VSTATE=OK 且五处同 107')

def app(p, t):
    with io.open(p, 'a', encoding='utf-8') as f:
        f.write(t.rstrip('\n') + '\n')

app(r'F:\Daodao\能力检查\2026-11-22.md', '''
### 12:15 追加（手机装包后重算，版本能力 45 → 92）

- 手机已装 v0.107（用户截图：左上角 v0.107、企鹅少年·手办风、90fps、与电脑已连），12:13:33 手机自检已上报 v107。
- **Q-007（真机落后，复发 1 次）已关闭**，带复现：手机看左上角版本牌 + /ping 107 + 页面 data-ver 107。
- **Q-082 新增并当场关闭**：`版本奖惩.py` 的 LANDING 还指旧 `引导页_src\\index.html`（停在 69）、ONLINE 还指旧 `app_17hnj8acgs2`（线上 62），所以天天判"五处不一致"。改指当前落地页源与 app_17jdxkgf27q，留 `.bak_20261122`。
- 重跑结果：`电脑 v107 · 手机 v107 · 页面 v107 · 线上 v107`，结算 +1 版本一致，`VSTATE=OK`；`版本机制.py` 不再报"五处不一致"。
- 仍欠：零验证版本 7 个（0.57–0.62、0.85）未补证据。
''')

app(r'F:\Daodao\同步日志.txt', '2026-11-22 12:16  手机装 v0.107 完成（截图证据），12:13:33 上报；Q-007 关闭；修 版本奖惩.py 旧落地页/旧 app 路径（留 .bak_20261122），重跑五处 107、VSTATE=OK')
app(r'F:\Daodao\经验库.md', '2026-11-22 | 主题：版本巡检假报警怎么来的 | 学到：巡检脚本自己指向旧页面/旧 app，会把"一致"判成"不一致"，每天白扣协调分 | 来源：tools\\版本奖惩.py L33-L34 | 改动：LANDING→道落地页\\道_落地页_v069.html、ONLINE→app_17jdxkgf27q（留 .bak_20261122） | 效果：VSTATE=OK，五处同为 107 | 标签：#版本 #巡检 #打包 | 状态：已用 | 提交：未提交（工具脚本改动，待下次源码提交一并带）')
print('done')
