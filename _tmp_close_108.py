# 程序版本：v0.1 | 2026-11-22 | 一次性：发版记录纠偏（v0.108 已发页）+ 待优化 21/24 收口 + 经验库补一条
import io
# 1) 发版记录：纠「未发页」
P = r'F:\Daodao\发版记录.txt'
s = io.open(P, encoding='utf-8').read()
s = s.replace('[2026-11-22 16:25] v0.108 两端同步出包（未发页）',
              '[2026-11-22 16:25] v0.108 两端同步出包（当轮未发页，同日晚已发页，见下条）', 1)
tail = '''
[2026-11-22 16:35] v0.108 线上发布完成（补上一条的「未做」）
- 上传 CDN 得新短链：exe https://aka.doubaocdn.com/s/xO5UTb6CuK、apk https://aka.doubaocdn.com/s/70iIWhFa90；真下载逐字节核对 9,933,824 / 8,183,886，sha256 与本地一致
- 两页已发到 108：清单页 app_17hpue26uuw（data-ver=108，正文当前版本号=108）、落地页 app_17jdxkgf27q（data-ver=108），两页短链同一条
- 云侧核验：线上包校验.sh PASS 5/5（短链真下得到、apk 内 HTML_VER=108、落地页 9 个资源全 200）；发布版本卡 108 已写
- 云侧 线上期望值.conf 同步改到 EXP_VER=108 / EXP_EXE=9933824 / EXP_APK=8183886（此前还停在 107）
- 本地新增 tools\\两端自用体检.py（17 项真用一遍：记事本增删一轮、曲库、更新链体积、apk 内容、PROGVER），真跑 17/17 PASS，报告 F:\\Daodao\\巡检报告\\两端自用_20261122_1635.md
- 定时：定时任务受套餐限制只能有 1 条（已满），改为把两端体检写进 E:\\Daodao\\每日任务说明.md（v17，第 7–9 条），随「道 每天同步体检」每天 08:38 / 18:24 两轮一起跑
'''
s = s.rstrip('\n') + '\n' + tail
io.open(P, 'w', encoding='utf-8').write(s)
print('发版记录 OK')

# 2) 待优化 21/24 收口
P2 = r'F:\Daodao\待优化.txt'
t = io.open(P2, encoding='utf-8').read()
t = t.replace('21. 手机端音乐修复只有本地包，线上仍 v107；真机出声确认后再定是否升 0.108 发两页+短链。',
              '21. [已办 16:35] 0.108 两页+短链已发，云侧校验 PASS 5/5；手机端真机出声仍待用户装包确认（Q-089）。')
t = t.replace('24. 线上还停在 v107（两页 data-ver=107、exe 9,865,728 / apk 8,179,826），本地 0.108 已出包待发；发版时要同步改 线上期望值.conf 的 EXP_VER/EXP_EXE/EXP_APK。',
              '24. [已办 16:35] 线上已 108；云侧 线上期望值.conf 已改 EXP_VER=108 / EXP_EXE=9933824 / EXP_APK=8183886，线上包校验.sh 与 发布版本卡.sh 均 PASS。')
io.open(P2, 'w', encoding='utf-8').write(t)
print('待优化 OK')

# 3) 经验库补两条
P3 = r'F:\Daodao\经验库.md'
e = io.open(P3, encoding='utf-8').read()
add = '''
## 2026-11-22 · 更新链怎么验才靠得住
- CDN 短链（aka.doubaocdn.com/s/xxx）对 HEAD 回 404，别用 HEAD 判活；用 `Range: bytes=0-1023` 取一小段，读 `Content-Range` 的总字节数，再和本地包体比对。
- 「发全了」要三条同时成立：清单页 data-ver == APP_VER、data-exe/apk 短链总字节 == 本地包体、落地页 data-ver 同号。只对一条就报"已更新"最容易漏。
- 定时任务套餐只给 1 条；加需求不要硬建第二条，改 E:\\Daodao\\每日任务说明.md（任务 query 里写死要先读它）更稳，也不会丢原有流程。
'''
if '更新链怎么验才靠得住' not in e:
    e = e.rstrip('\n') + '\n' + add
    io.open(P3, 'w', encoding='utf-8').write(e)
print('经验库 OK')
