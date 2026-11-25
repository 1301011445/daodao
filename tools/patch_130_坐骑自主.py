# -*- coding: utf-8 -*-
"""v130 / 2：坐骑「自主选择是否使用」
· SharedPreferences mountAuto=true：它自己每次启动按概率决定骑不骑、骑哪只
· 用户点按钮 = 接管（mountAuto 关），长按 = 交还给道自己决定
判据 N1~N4
"""
P = r'F:\Daodao\src\_apk\src\com\daodao\pet\DaoOverlay.java'
B = r'F:\Daodao\src\_apk\src\com\daodao\pet\DaoBridge.java'
H = r'F:\Daodao\src\_apk\assets\dao.html'
n = []


def rep(path, old, new, tag):
    s = open(path, encoding='utf-8').read()
    if old not in s:
        print('MISS', tag)
        return False
    open(path, 'w', encoding='utf-8').write(s.replace(old, new, 1))
    n.append(tag)
    return True


rep(P, '    private int mount = 0;   // 0 无坐骑，1~N 对应 MOUNT_FILES 里的图',
    '    private int mount = 0;   // 0 无坐骑，1~N 对应 MOUNT_FILES 里的图\n'
    '    private boolean mountAuto = true;   // 自主：每次启动自己决定骑不骑；用户点一下就接管', '字段 mountAuto')

rep(P, '            try { mount = getContext().getSharedPreferences("dao", 0).getInt("mount", 0); } catch (Throwable e) { mount = 0; }',
    '''            try {
                android.content.SharedPreferences spd = getContext().getSharedPreferences("dao", 0);
                mountAuto = spd.getBoolean("mountAuto", true);
                mount = spd.getInt("mount", 0);
                if (mountAuto) {
                    // 自主决定：六成概率骑一只，四成不骑（它自己也该有不骑的时候）
                    mount = (Math.random() < 0.6)
                            ? 1 + (int) (Math.random() * Math.max(1, mounts.length - 1)) : 0;
                }
            } catch (Throwable e) { mount = 0; mountAuto = true; }''', '启动自主决定')

rep(P, '''        void setMountArt(int k) {
            mount = Math.max(0, Math.min(mounts.length - 1, k));''',
    '''        void setMountArt(int k) {
            mountAuto = false;   // 用户手动选了，就不再自作主张
            mount = Math.max(0, Math.min(mounts.length - 1, k));
            try { getContext().getSharedPreferences("dao", 0).edit().putBoolean("mountAuto", false).apply(); } catch (Throwable e) { }''',
    '手动接管')

rep(P, '''        /** 演一个动作。''',
    '''        /** v130：把坐骑交回给道自己决定（长按按钮）；true 时立刻重新随机一次 */
        void setMountAuto(boolean auto) {
            mountAuto = auto;
            try { getContext().getSharedPreferences("dao", 0).edit().putBoolean("mountAuto", auto).apply(); } catch (Throwable e) { }
            if (auto) {
                mount = (Math.random() < 0.6)
                        ? 1 + (int) (Math.random() * Math.max(1, mounts.length - 1)) : 0;
                try { getContext().getSharedPreferences("dao", 0).edit().putInt("mount", mount).apply(); } catch (Throwable e) { }
            }
            invalidate();
        }

        /** 演一个动作。''', 'setMountAuto')

rep(B, '    @JavascriptInterface\n    public void setMount(int k) {',
    '''    @JavascriptInterface
    public void setMountAuto(boolean auto) {
        if (dao != null) dao.setMountAuto(auto);
    }

    @JavascriptInterface
    public void setMount(int k) {''', 'Bridge setMountAuto')

rep(H, "  var MOUNT_NAMES = ['坐骑', '祥云', '木马', '飞剑', '小鹿', '纸鹤'];",
    "  var MOUNT_NAMES = ['坐骑', '祥云', '木马', '飞剑', '小鹿', '纸鹤'];\n  var mountAuto = true;   // 由道自己决定骑不骑；长按按钮交回去", 'HTML 变量')

rep(H, '      mountState = (mountState + 1) % MOUNT_NAMES.length;',
    '      mountAuto = false;\n      mountState = (mountState + 1) % MOUNT_NAMES.length;', '点一下=接管')

print('PATCH2_OK', len(n))

j = open(P, encoding='utf-8').read()
b = open(B, encoding='utf-8').read()
h = open(H, encoding='utf-8').read()
c = [('N1 有自主标记', 'private boolean mountAuto = true;' in j),
     ('N2 启动时自己决定', 'if (mountAuto) {' in j and 'Math.random() < 0.6' in j),
     ('N3 手动即接管 + 可交还', 'mountAuto = false;   // 用户手动选了' in j and 'void setMountAuto(boolean auto)' in j),
     ('N4 桥接与页面都认这套', 'setMountAuto(boolean auto)' in b and 'mountAuto = false;' in h)]
for k, v in c:
    print(k, 'PASS' if v else 'FAIL')
print('SUMMARY', 'PASS' if all(v for k, v in c) else 'FAIL')
raise SystemExit(0 if all(v for k, v in c) else 1)
