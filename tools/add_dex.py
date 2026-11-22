# 程序版本：v0.1 | 2026-11-22 | 把 classes.dex 塞进 base.apk，塞完校验（7z 改名失败会出无 dex 假包）
"""往 aapt2 产出的 base.apk 里加 classes.dex，写完自检。失败退出码 1。

用法：python add_dex.py <base.apk> <classes.dex>
"""
import sys, zipfile, os, shutil

apk, dex = sys.argv[1], sys.argv[2]
tmp = apk + '.new'

if not os.path.exists(apk):
    sys.exit('没有 base.apk')
if not os.path.exists(dex):
    sys.exit('没有 classes.dex')

names = []
with zipfile.ZipFile(apk, 'r') as zin:
    names = zin.namelist()
    if 'classes.dex' in names:
        sys.exit('base.apk 里已经有 classes.dex，先清掉旧包')
    with zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as zout:
        for it in zin.infolist():
            if it.filename.endswith('/'):
                continue
            data = zin.read(it.filename)
            # 已经是压缩存储的保持原压缩方式，其余按 deflate
            if it.compress_type == zipfile.ZIP_STORED:
                zout.writestr(it, data, compress_type=zipfile.ZIP_STORED)
            else:
                zout.writestr(it, data, compress_type=zipfile.ZIP_DEFLATED)
        zout.write(dex, 'classes.dex', compress_type=zipfile.ZIP_DEFLATED)

os.replace(tmp, apk)

# 校验：dex 真在里面，且能读
with zipfile.ZipFile(apk, 'r') as z:
    ok = 'classes.dex' in z.namelist()
    size = z.getinfo('classes.dex').file_size if ok else 0
print('ADD_DEX_OK dex=%s size=%d apk=%d' % (ok, size, os.path.getsize(apk)))
sys.exit(0 if ok and size > 1000 else 1)
