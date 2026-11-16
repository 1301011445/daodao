import os, shutil
b = r'F:\Daodao\src\桌面分身\_bundle'
bak = r'F:\Daodao\_tmp_face\old_faces'

pairs = [('out_00.png', 'face_0.png'), ('out_01.png', 'face_1.png'),
         ('out_02.png', 'face_2.png'), ('out_03.png', 'face_3.png')]
for src, dst in pairs:
    s = os.path.join(r'F:\Daodao\_tmp_face', src)
    d = os.path.join(b, dst)
    if os.path.exists(d):
        shutil.copy2(d, os.path.join(bak, dst))
    shutil.copy2(s, d)
    print('替换', dst, os.path.getsize(d), '字节')

np = os.path.join(b, 'names.txt')
raw = open(np, 'rb').read()
bom = raw.startswith(b'\xef\xbb\xbf')
lines = raw.decode('utf-8-sig').split('\n')
ren = {'橘猫': '橘猫少年', '白兔': '白兔少女', '小狐狸': '狐狸少女', '熊猫': '熊猫少女'}
for i, l in enumerate(lines):
    k = l.strip()
    if k in ren:
        lines[i] = ren[k]
        print('names 第', i + 1, '行:', k, '->', ren[k])
open(np, 'wb').write((b'\xef\xbb\xbf' if bom else b'') + '\n'.join(lines).encode('utf-8'))
print('names 前 14 行:', lines[:14])
