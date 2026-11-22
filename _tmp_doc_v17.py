# 程序版本：v0.1 | 2026-11-22 | 一次性：每日任务说明 v16→v17，加「两端自用体检 + 更新链三条」
import io, re
P = r'E:\Daodao\每日任务说明.md'
s = io.open(P, encoding='utf-8').read()

s = s.replace('# 道 · 每日定时任务说明（v16，2026-11-22 更新）',
              '# 道 · 每日定时任务说明（v17，2026-11-22 更新）', 1)

anchor = '## 第三步的硬要求'
assert anchor in s
add = '''7. 再跑一遍「两端自用体检」：`E:\\Python313\\python.exe F:\\Daodao\\tools\\两端自用体检.py`。它和 `自检.py` 分工不同——自检只看"通不通"，这个脚本是**真的动手用一遍**：记事本走 `op=add → list → del` 一轮真增删（自检条目跑完自己删掉，不许留垃圾）、曲库 `/music` 列一遍、线上清单页 `data-ver` 与两条短链的**总字节数**是否等于本地 `道.exe` / `道.apk`（短链不支持 HEAD，用 Range 取一段读 Content-Range）、落地页版本号、apk 内 `HTML_VER`/`versionCode`/dex 桥接/三首 adp/有没有混进 `.bak`、手机端按住说话与歌单状态机的标记、程序版本档案 `PROGVER`。
8. 报告落 `F:\\Daodao\\巡检报告\\两端自用_YYYYMMDD_HHMM.md`，末行 `SELFTEST|n=…|pass=…|fail=…`。有 FAIL 按上面同一套规则登记问题库（来源写「两端自用体检」），能当场修的就修，修不了写清卡在哪一步。
9. 「检查更新」单独核三条，缺一条都不算发全：① 线上清单页 `data-ver` == `pet.cs` 的 `APP_VER`；② 清单页 `data-exe` / `data-apk` 指向的短链总字节 == 本地两个包体；③ 落地页 `data-ver` 同号。任一不等，就是"发了一半"（最常见：包传了但页面没更，或页面更了但短链还是旧的），必须当轮补齐，不许汇报"已更新"。

'''
s = s.replace(anchor, add + anchor, 1)
io.open(P, 'w', encoding='utf-8').write(s)
print('每日任务说明 -> v17，已加第 7-9 条；总行数', s.count('\n'))
