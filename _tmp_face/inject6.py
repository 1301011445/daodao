# -*- coding: utf-8 -*-
import os, re, shutil, base64

b = r'F:\Daodao\src\桌面分身\_bundle'
bak = r'F:\Daodao\_tmp_face\old_faces'
if not os.path.isdir(bak):
    os.makedirs(bak)

pairs = [('out_04.png', 'face_4.png'), ('out_05.png', 'face_5.png'),
         ('out_09.png', 'face_9.png'), ('out_10.png', 'face_10.png')]
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
ren = {'小恐龙': '恐龙少女', '小企鹅': '企鹅少年', '魔法师': '魔法师少女'}
for i, l in enumerate(lines):
    k = l.strip()
    if k in ren:
        lines[i] = ren[k]
        print('names 第', i + 1, '行:', k, '->', ren[k])
open(np, 'wb').write((b'\xef\xbb\xbf' if bom else b'') + '\n'.join(lines).encode('utf-8'))
print('names 全部:', [x.strip() for x in lines if x.strip()])

p = r'F:\Daodao\src\_apk\assets\dao.html'
shutil.copy2(p, r'F:\Daodao\_tmp_face\dao.html.v48.bak')
raw = open(p, 'rb').read()
bom2 = raw.startswith(b'\xef\xbb\xbf')
s = raw.decode('utf-8-sig')

# 1) 名字表整表换成 14 只新名字，和 names.txt 完全一致
old_who = "  var WHO = ['橘猫','白兔','小狐狸','熊猫','小恐龙','小企鹅','蓝发少女','黑发少年','银发剑客','魔法师','古风少女','小机器人','白衫少年','青衫少女'];"
new_who = "  var WHO = ['橘猫少年','白兔少女','狐狸少女','熊猫少女','恐龙少女','企鹅少年','蓝发少女','黑发少年','银发剑客','魔法师少女','古风少女','机械少年','白衫少年','青衫少女'];"
assert s.count(old_who) == 1, 'WHO 行没找到'
s = s.replace(old_who, new_who, 1)
print('WHO 已换成 14 只新名字')

# 2) 别名表键跟着新名字走，命中哪个仍按原下标
old_alias = """    ['橘猫', '猫'], ['白兔', '兔'], ['小狐狸', '狐狸'], ['熊猫', '熊猫'], ['小恐龙', '恐龙'],
    ['小企鹅', '企鹅'], ['蓝发少女', '蓝发'], ['黑发少年', '黑发'], ['银发剑客', '剑客'],
    ['魔法师', '魔法'], ['古风少女', '古风'], ['小机器人', '机器人']"""
new_alias = """    ['橘猫少年', '猫'], ['白兔少女', '兔'], ['狐狸少女', '狐狸'], ['熊猫少女', '熊猫'], ['恐龙少女', '恐龙'],
    ['企鹅少年', '企鹅'], ['蓝发少女', '蓝发'], ['黑发少年', '黑发'], ['银发剑客', '剑客'],
    ['魔法师少女', '魔法'], ['古风少女', '古风'], ['机械少年', '机器人']"""
assert s.count(old_alias) == 1, 'ALIAS 段没找到'
s = s.replace(old_alias, new_alias, 1)
print('ALIAS 已同步新名字')

# 3) 替换 FACES 里 4/5/9/10 四张图
i = s.index('var FACES = [')
j = s.index('];', i)
seg = s[i:j]
pat = re.compile(r'"data:image/[a-z]+;base64,[A-Za-z0-9+/=]+"')
items = pat.findall(seg)
print('FACES 项数 =', len(items))
assert len(items) == 14

new = {}
for sp in ('04', '05', '09', '10'):
    fp = r'F:\Daodao\_tmp_face\for_apk_%s.png' % sp
    b64 = base64.b64encode(open(fp, 'rb').read()).decode()
    new[int(sp)] = '"data:image/png;base64,%s"' % b64
    print('准备替换索引', int(sp), os.path.getsize(fp), '字节')

pos = 0
for k, it in enumerate(items):
    idx = seg.index(it, pos)
    if k in new:
        seg = seg[:idx] + new[k] + seg[idx + len(it):]
        pos = idx + len(new[k])
    else:
        pos = idx + len(it)
s = s[:i] + seg + s[j:]

# 4) 版本 48 -> 49
assert s.count("var HTML_VER = '48';") == 1
s = s.replace("var HTML_VER = '48';", "var HTML_VER = '49';", 1)
open(p, 'w', encoding='utf-8-sig' if bom2 else 'utf-8', newline='').write(s)
print('新页面字节 =', len(s.encode('utf-8')))

m = r'F:\Daodao\src\_apk\AndroidManifest.xml'
raw = open(m, 'rb').read()
bom3 = raw.startswith(b'\xef\xbb\xbf')
t = raw.decode('utf-8-sig')
t = t.replace('versionCode="48"', 'versionCode="49"').replace('versionName="48.0"', 'versionName="49.0"')
open(m, 'wb').write((b'\xef\xbb\xbf' if bom3 else b'') + t.encode('utf-8'))
print('manifest:', re.findall(r'versionCode="\d+"', t), re.findall(r'versionName="[^"]*"', t))

c = r'F:\Daodao\src\桌面分身\pet.cs'
raw = open(c, 'rb').read()
bom4 = raw.startswith(b'\xef\xbb\xbf')
cs = raw.decode('utf-8-sig')
assert cs.count('public const int APP_VER = 48;') == 1
cs = cs.replace('public const int APP_VER = 48;', 'public const int APP_VER = 49;', 1)
open(c, 'wb').write((b'\xef\xbb\xbf' if bom4 else b'') + cs.encode('utf-8'))
print('APP_VER:', re.findall(r'public const int APP_VER = \d+;', cs))
