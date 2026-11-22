# 程序版本：v0.1 | 2026-11-22 | 一次性：把 两端自用体检.py 登记进程序版本档案
import io, json
P = r'F:\Daodao\tools\程序版本记录.json'
d = json.load(io.open(P, encoding='utf-8'))
if not any(x['名称'] == '两端自用体检.py' for x in d['程序']):
    d['程序'].append(dict(名称='两端自用体检.py', 路径=r'F:\Daodao\tools\两端自用体检.py', 版本='v0.1',
                          日期='2026-11-22', 用途='定时把两端真用一遍：记事本增删、曲库、更新链体积、apk 内容、PROGVER',
                          改动='新建：17 项检查，报告写 巡检报告\\两端自用_*.md，FAIL 退出码 1',
                          文件修改日='2026-11-22', 已插版本头=True))
    io.open(P, 'w', encoding='utf-8').write(json.dumps(d, ensure_ascii=False, indent=1))
    print('已登记，共', len(d['程序']))
else:
    print('已存在')
