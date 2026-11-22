# 程序版本：v0.1 | 2026-11-22 | 一次性：给 apk 构建链两个脚本补版本头并登记入档
"""给 F:\\Daodao\\src\\_apk\\build.ps1 和 F:\\Daodao\\tools\\add_dex.py 补版本头，写入 程序版本记录.json。
BOM 必须留在第 0 字节，故用 utf-8-sig 重写。已带头的跳过。
"""
import io, os, json

REC = r'F:\Daodao\tools\程序版本记录.json'
DATE = '2026-11-22'

TARGETS = [
    dict(name='build.ps1', path=r'F:\Daodao\src\_apk\build.ps1',
         use='手机端 apk 打包（aapt2→javac→d8→塞 dex→zipalign→签名）',
         change='塞 dex 改走 add_dex.py 并硬校验；素材目录清掉 .bak 备份',
         ver='v0.1'),
    dict(name='add_dex.py', path=r'F:\Daodao\tools\add_dex.py',
         use='往 base.apk 塞 classes.dex 并自检（替掉 7z 改名失败会出假包的路）',
         change='新建：纯 Python 重写 zip，写完校验 dex 存在且 >1000 字节',
         ver='v0.1'),
]


def ensure_header(path, ver, change):
    b = io.open(path, 'rb').read()
    text = b.decode('utf-8-sig')
    if text.startswith('# 程序版本：'):
        first = text.split('\n', 1)[0]
        return 'SKIP ' + first
    hdr = '# 程序版本：%s | %s | %s\n' % (ver, DATE, change)
    io.open(path, 'w', encoding='utf-8-sig', newline='\n').write(hdr + text)
    return 'ADDED'


d = json.load(io.open(REC, encoding='utf-8'))
names = [it['名称'] for it in d['程序']]
for t in TARGETS:
    r = ensure_header(t['path'], t['ver'], t['change'])
    print(t['name'], r)
    if t['name'] in names:
        it = [x for x in d['程序'] if x['名称'] == t['name']][0]
        it['版本'] = t['ver']; it['日期'] = DATE
        it['改动'] = t['change']; it['文件修改日'] = DATE; it['已插版本头'] = True
    else:
        d['程序'].append(dict(名称=t['name'], 路径=t['path'], 版本=t['ver'], 日期=DATE,
                              用途=t['use'], 改动=t['change'], 文件修改日=DATE, 已插版本头=True))

io.open(REC, 'w', encoding='utf-8').write(json.dumps(d, ensure_ascii=False, indent=1))
print('记录条目数 =', len(d['程序']))
