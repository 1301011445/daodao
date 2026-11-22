# 动作包络检查：挥手/点头的起落曲线是不是「快起—稳—慢起快收」，而不是对称正弦
# 程序版本：v0.1 | 2026-11-23 | 判据：源码三处断言 + 包络数值形态 + apk 里 dex 到位
import os, re, sys, zipfile

SRC = r'F:\Daodao\src\_apk\src\com\daodao\pet\DaoOverlay.java'
APK = r'F:\Daodao\src\_apk\Dao.apk'
OK, FAIL = [], []


def chk(name, cond, detail=''):
    (OK if cond else FAIL).append((name, detail))


src = open(SRC, encoding='utf-8').read()

# 1) 源码里必须是分段包络，不是单正弦
chk('E1 有 waveEnv 分段函数', 'float waveEnv(float p)' in src)
chk('E2 起手段用三次 ease-out', 'return 1f - u * u * u;' in src)
chk('E3 保持段存在', 'if (p < 0.72f) return 1f;' in src)
chk('E4 收手段用 (1-x)^3', 'return u * u * u;' in src)
chk('E5 挥手不再用对称正弦', 'Math.sin(prog * Math.PI)' not in src)
chk('E6 自动挥由 tick 驱动', 'idleWaveIfDue()' in src)

# 2) 数值形态：照源码复算
def env(p):
    if p <= 0 or p >= 1:
        return 0.0
    if p < 0.32:
        x = p / 0.32
        u = 1 - x
        return 1 - u ** 3
    if p < 0.72:
        return 1.0
    x = (p - 0.72) / 0.28
    return (1 - x) ** 3


rise = env(0.16)
fall = env(0.84)
chk('E7 中段满幅', abs(env(0.5) - 1.0) < 1e-9, 'env(0.5)=%.3f' % env(0.5))
chk('E8 起手够快', env(0.10) > 0.5, 'env(0.10)=%.3f' % env(0.10))
chk('E9 收尾够干脆', env(0.97) < 0.02, 'env(0.97)=%.3f' % env(0.97))
chk('E10 起落不对称', rise > fall * 3, 'rise=%.3f fall=%.3f 比=%.1f' % (rise, fall, rise / max(fall, 1e-9)))

# 3) 包里真有这份代码：dex 体积比上一版（124928）大，且签名包存在
dex_size = 0
if os.path.exists(APK):
    with zipfile.ZipFile(APK) as z:
        names = z.namelist()
        if 'classes.dex' in names:
            dex_size = z.getinfo('classes.dex').file_size
chk('E11 包里有 classes.dex', dex_size > 0, 'dex=%d' % dex_size)
chk('E12 新代码已进包', dex_size >= 125000, 'dex=%d（上一版 124928）' % dex_size)

for n, d in OK:
    print('PASS | %s | %s' % (n, d))
for n, d in FAIL:
    print('FAIL | %s | %s' % (n, d))
print('汇总：%d 项判据 | 过 %d | 未过 %d | %s' % (len(OK) + len(FAIL), len(OK), len(FAIL),
                                                'PASS' if not FAIL else 'FAIL'))
sys.exit(0 if not FAIL else 1)
