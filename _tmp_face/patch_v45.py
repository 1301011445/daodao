import io, re, shutil
p = r'F:\Daodao\src\_apk\assets\dao.html'
shutil.copy2(p, r'F:\Daodao\_tmp_face\dao.html.v44.bak')
raw = open(p, 'rb').read()
bom = raw.startswith(b'\xef\xbb\xbf')
s = raw.decode('utf-8-sig')

def sub1(old, new, label):
    global s
    assert old in s, '没找到：' + label
    assert s.count(old) == 1, '出现不止一次：' + label
    s = s.replace(old, new)
    print('OK', label)

# 1) 换形象候选名单：扩到 14 只，新形象排最前
sub1('var _ks = [6, 7, 8, 11];',
     'var _ks = [12, 13, 6, 7, 8, 11, 0, 1, 2, 3, 4, 5, 9, 10];',
     '_ks 换形象名单')

# 2) 每日形象轮换名单：同样扩到 14 只
sub1('var _kinds = [6, 7, 8, 11];',
     'var _kinds = [12, 13, 6, 7, 8, 11, 0, 1, 2, 3, 4, 5, 9, 10];',
     '_kinds 每日名单')

# 3) 名字表补两只
sub1("var WHO = ['橘猫','白兔','小狐狸','熊猫','小恐龙','小企鹅','蓝发少女','黑发少年','银发剑客','魔法师','古风少女','小机器人'];",
     "var WHO = ['橘猫','白兔','小狐狸','熊猫','小恐龙','小企鹅','蓝发少女','黑发少年','银发剑客','魔法师','古风少女','小机器人','白衫少年','青衫少女'];",
     'WHO 名字表')

# 4) 脚底/宽度参数补两只
sub1('var FY = [0.34, 0.44, 0.35, 0.35, 0.34, 0.28, 0.30, 0.30, 0.34, 0.40, 0.34, 0.37];',
     'var FY = [0.34, 0.44, 0.35, 0.35, 0.34, 0.28, 0.30, 0.30, 0.34, 0.40, 0.34, 0.37, 0.34, 0.34];',
     'FY 脚底参数')
sub1('var FW = [0.55, 0.62, 0.55, 0.62, 0.55, 0.60, 0.50, 0.55, 0.30, 0.45, 0.32, 0.72];',
     'var FW = [0.55, 0.62, 0.55, 0.62, 0.55, 0.60, 0.50, 0.55, 0.30, 0.45, 0.32, 0.72, 0.30, 0.42];',
     'FW 宽度参数')

# 5) 版本牌
sub1("var HTML_VER = '44';", "var HTML_VER = '45';", 'HTML_VER')

open(p, 'w', encoding='utf-8-sig' if bom else 'utf-8', newline='').write(s)
print('BOM 保留:', bom, '| 新大小:', len(s.encode('utf-8')))
print('自检 _ks:', re.findall(r'var _ks = \[[^]]*\]', s)[0])
print('自检 _kinds:', re.findall(r'var _kinds = \[[^]]*\]', s)[0])
print('自检 WHO 项数:', s[s.index('var WHO = ['):s.index('];', s.index('var WHO = ['))].count(',') + 1)
print('自检 HTML_VER:', re.findall(r"var HTML_VER = '[^']*'", s))
print('自检 FACES 张数:', s[s.index('var FACES = ['):s.index('];', s.index('var FACES = ['))].count('data:image'))
