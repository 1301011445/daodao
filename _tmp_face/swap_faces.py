import os, shutil
b = r'F:\Daodao\src\桌面分身\_bundle'
bak = r'F:\Daodao\_tmp_face\old_faces'
os.makedirs(bak, exist_ok=True)

pairs = [('out_06.png', 'face_6.png'), ('out_07.png', 'face_7.png'),
         ('out_08.png', 'face_8.png'), ('out_11.png', 'face_11.png')]
for src, dst in pairs:
    s = os.path.join(r'F:\Daodao\_tmp_face', src)
    d = os.path.join(b, dst)
    if os.path.exists(d):
        shutil.copy2(d, os.path.join(bak, dst))
    shutil.copy2(s, d)
    print('替换', dst, os.path.getsize(d), '字节')

# 名字表：第 9 行（索引 8）小机器人 -> 机械少年
np = os.path.join(b, 'names.txt')
raw = open(np, 'rb').read()
bom = raw.startswith(b'\xef\xbb\xbf')
lines = raw.decode('utf-8-sig').split('\n')
print('改前行数', len(lines))
for i, l in enumerate(lines):
    if l.strip() == '小机器人':
        lines[i] = '机械少年'
        print('names 第', i + 1, '行改名')
open(np, 'wb').write((b'\xef\xbb\xbf' if bom else b'') + '\n'.join(lines).encode('utf-8'))
print('names 前 14 行:', [x for x in lines[:14]])
