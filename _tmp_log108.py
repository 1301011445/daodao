# 程序版本：v0.1 | 2026-11-22 | 一次性：发版记录写 0.108 本地出包
import io, datetime, os, hashlib

T = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
apk = r'F:\Daodao\道.apk'
exe = r'F:\Daodao\道.exe'
apk_sz = os.path.getsize(apk)
exe_sz = os.path.getsize(exe)
apk_h = hashlib.sha256(open(apk, 'rb').read()).hexdigest()[:16]
exe_h = hashlib.sha256(open(exe, 'rb').read()).hexdigest()[:16]

entry = f"""
[{T}] v0.108 两端同步出包（未发页）
- 版本：pet.cs APP_VER 107→108、dao.html HTML_VER 107→108、AndroidManifest versionCode/Name 108 / 0.108
- 手机端这轮修的：①唱歌面板状态机（stopMusic 没清 win→第二次打不开；点歌顺手关面板→点完就没入口），拆成 stopAudio/closePanel 并加行高亮；②「跟它说话」改按住说松手发，按钮实时显示秒数，<0.35s 当误触；③失败提示带字节数与截断后的原生错误；④SPR() 立绘去紫边（alpha<6 归零 RGB、alpha<200 且偏粉紫时把绿抬到 min(R,B)），86 张内嵌 webp 里 34 张边带品红 5718→0
- 电脑端这轮同步的：_bundle 99 张立绘按同规则去紫边——17 张边带 29,450 px 去紫；再对离透明 2px 内的粉边补一刀 7,835 px；评审脚本复扫：边带品红 0、透明处残留 0，仅 3 张各剩 1–2 个画稿色点
- 包体：exe {exe_sz:,} B sha256_{exe_h}；apk {apk_sz:,} B sha256_{apk_h}，versionCode=108 versionName=0.108，签名 v2/v3 通过（证书与旧包同）
- 核对：ping=OK|道|108；apk 内 HTML_VER=108、含 startHold/win=null/SPR<200、三首 adp 齐、dex 有 playPcm/assetXhr；JS 两块语法 0 错
- 未做：线上仍是 v107；两页（清单页 app_17hpue26uuw / 落地页 app_17jdxkgf27q）与短链都没动，等用户确认发版后再传 CDN 换链接
"""
p = r'F:\Daodao\发版记录.txt'
s = io.open(p, encoding='utf-8').read()
io.open(p, 'w', encoding='utf-8').write(s.rstrip('\n') + '\n' + entry)
print('发版记录已追加')

# 待优化补一条
p = r'F:\Daodao\待优化.txt'
s = io.open(p, encoding='utf-8').read()
if '24.' not in s:
    s = s.rstrip('\n') + '\n24. 线上还停在 v107（两页 data-ver=107、exe 9,865,728 / apk 8,179,826），本地 0.108 已出包待发；发版时要同步改 线上期望值.conf 的 EXP_VER/EXP_EXE/EXP_APK。\n'
    io.open(p, 'w', encoding='utf-8').write(s)
    print('待优化 +24')
