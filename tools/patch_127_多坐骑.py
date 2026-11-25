# -*- coding: utf-8 -*-
"""v127 多坐骑（5 只）：祥云 / 木马 / 飞剑 / 小鹿 / 纸鹤
· Java 从两个固定字段改成数组，按钮轮换 0~5
判据 T1~T4
"""
P = r'F:\Daodao\src\_apk\src\com\daodao\pet\DaoOverlay.java'
H = r'F:\Daodao\src\_apk\assets\dao.html'
n = 0


def rep(path, old, new):
    global n
    s = open(path, encoding='utf-8').read()
    if old not in s:
        print('MISS:', path.split('\\')[-1], old[:50].replace('\n', ' '))
        return
    open(path, 'w', encoding='utf-8').write(s.replace(old, new, 1))
    n += 1


rep(P, '    private int mount = 0;\n    private Bitmap mountCloud, mountHorse;',
    '    private int mount = 0;   // 0 无坐骑，1~N 对应 MOUNT_FILES 里的图\n'
    '    private static final String[] MOUNT_FILES = {\n'
    '            "mount_cloud.png",   // 1 祥云\n'
    '            "mount_horse.png",   // 2 小木马\n'
    '            "mount_sword.png",   // 3 飞剑\n'
    '            "mount_deer.png",    // 4 小鹿\n'
    '            "mount_crane.png"    // 5 纸鹤\n'
    '    };\n'
    '    private Bitmap[] mounts = new Bitmap[MOUNT_FILES.length];')

rep(P, '            // 2026-11-25 坐骑素材：两张都是透明底，进来先过一遍 matte，免得边上带白\n'
       '            mountCloud = loadOpt("mount_cloud.png");\n'
       '            if (mountCloud != null && !mountCloud.isRecycled()) matteInPlace(mountCloud);\n'
       '            mountHorse = loadOpt("mount_horse.png");\n'
       '            if (mountHorse != null && !mountHorse.isRecycled()) matteInPlace(mountHorse);',
    '            // 2026-11-25 坐骑素材：五只都是透明底，进来先过一遍 matte，免得边上带白\n'
    '            for (int i = 0; i < MOUNT_FILES.length; i++) {\n'
    '                mounts[i] = loadOpt(MOUNT_FILES[i]);\n'
    '                if (mounts[i] != null && !mounts[i].isRecycled()) matteInPlace(mounts[i]);\n'
    '            }')

rep(P, '            Bitmap mb = (mount == 1 ? mountCloud : (mount == 2 ? mountHorse : null));',
    '            Bitmap mb = (mount > 0 && mount < mounts.length ? mounts[mount] : null);')

rep(P, '            mount = Math.max(0, Math.min(2, k));',
    '            mount = Math.max(0, Math.min(mounts.length - 1, k));')

rep(H, "  var MOUNT_NAMES = ['坐骑', '祥云', '木马'];",
    "  var MOUNT_NAMES = ['坐骑', '祥云', '木马', '飞剑', '小鹿', '纸鹤'];")

rep(H, '      mountState = (mountState + 1) % 3;',
    '      mountState = (mountState + 1) % MOUNT_NAMES.length;')

rep(H, "      tip(mountState === 0 ? '坐骑收起来了' : (mountState === 1 ? '祥云垫脚，托着你走' : '小木马驮你一段'));",
    "      tip(mountState === 0 ? '坐骑收起来了' : ('坐骑：' + MOUNT_NAMES[mountState] + '，托着你走'));")

print('PATCH_OK 改动数=', n)

j = open(P, encoding='utf-8').read()
h = open(H, encoding='utf-8').read()
t1 = 'MOUNT_FILES' in j and 'mount_sword.png' in j and 'mount_crane.png' in j
t2 = 'for (int i = 0; i < MOUNT_FILES.length; i++)' in j
t3 = 'mount < mounts.length ? mounts[mount]' in j and 'mounts.length - 1, k' in j
t4 = "'飞剑'" in h and 'MOUNT_NAMES.length;' in h
for name, v in (('T1 五只坐骑进配置表', t1), ('T2 循环加载', t2),
                ('T3 渲染与切换按数组长度', t3), ('T4 页面轮换 6 档（含无）', t4)):
    print(name, 'PASS' if v else 'FAIL')
print('SUMMARY', 'PASS' if all([t1, t2, t3, t4]) else 'FAIL')
raise SystemExit(0 if all([t1, t2, t3, t4]) else 1)
