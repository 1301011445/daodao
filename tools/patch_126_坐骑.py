# -*- coding: utf-8 -*-
"""v126 坐骑系统（手机端）
· 素材：assets/mount_cloud.png（祥云）、mount_horse.png（木马）
· 渲染：坐骑画在人物脚下，人物整体抬高到鞍位（rise = 坐骑高 ×0.52）
· 交互：主界面新增「坐骑」按钮，点一下轮换 无→祥云→木马→无，状态存 localStorage 与 SharedPreferences
判据 S1~S5
"""
P = r'F:\Daodao\src\_apk\src\com\daodao\pet\DaoOverlay.java'
B = r'F:\Daodao\src\_apk\src\com\daodao\pet\DaoBridge.java'
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


# 1) 字段
rep(P, '    private long walkOnAt = 0, walkOffAt = 0;   // 起步/停步时刻，用来算 400ms 过渡',
    '    private long walkOnAt = 0, walkOffAt = 0;   // 起步/停步时刻，用来算 400ms 过渡\n'
    '    // 2026-11-25 坐骑：0 无坐骑 / 1 祥云 / 2 木马\n'
    '    private int mount = 0;\n'
    '    private Bitmap mountCloud, mountHorse;')

# 2) 加载素材 + 读上次选择
rep(P, '            standArt = loadOpt("stand_" + art + ".png");\n'
       '            if (standArt != null && !standArt.isRecycled()) matteInPlace(standArt);',
    '            standArt = loadOpt("stand_" + art + ".png");\n'
    '            if (standArt != null && !standArt.isRecycled()) matteInPlace(standArt);\n'
    '            // 2026-11-25 坐骑素材：两张都是透明底，进来先过一遍 matte，免得边上带白\n'
    '            mountCloud = loadOpt("mount_cloud.png");\n'
    '            if (mountCloud != null && !mountCloud.isRecycled()) matteInPlace(mountCloud);\n'
    '            mountHorse = loadOpt("mount_horse.png");\n'
    '            if (mountHorse != null && !mountHorse.isRecycled()) matteInPlace(mountHorse);\n'
    '            try { mount = getContext().getSharedPreferences("dao", 0).getInt("mount", 0); } catch (Throwable e) { mount = 0; }')

# 3) 绘制坐骑 + 抬高人物
rep(P, '            c.drawOval(new RectF(w * 0.24f, h + bob - h * 0.03f, w * 0.76f, h + bob + h * 0.005f), sh);\n'
       '            c.save();',
    '            c.drawOval(new RectF(w * 0.24f, h + bob - h * 0.03f, w * 0.76f, h + bob + h * 0.005f), sh);\n'
    '            // 2026-11-25 坐骑：先把它画在脚下，人物再叠上去（不镜像、不跟着蹲，坐骑是地面上的东西）\n'
    '            float rise = 0f;\n'
    '            Bitmap mb = (mount == 1 ? mountCloud : (mount == 2 ? mountHorse : null));\n'
    '            if (mb != null && !mb.isRecycled()) {\n'
    '                float mw = w * 0.98f;\n'
    '                float mh = mw * mb.getHeight() / Math.max(1, mb.getWidth());\n'
    '                RectF mr = new RectF(w * 0.5f - mw * 0.5f, h + bob - mh, w * 0.5f + mw * 0.5f, h + bob);\n'
    '                c.drawBitmap(mb, null, mr, p);\n'
    '                rise = mh * 0.52f;   // 抬到鞍位：脚踩在坐骑背上，不是整个人沉进云里\n'
    '            }\n'
    '            c.save();\n'
    '            if (rise > 0f) c.translate(0, -rise);')

# 4) 外部切换接口
rep(P, '    /** 外部（手机主界面「换动作」按钮）让桌面上的那只动一下。 */',
    '    /** 2026-11-25 外部切换坐骑：0 无 / 1 祥云 / 2 木马。手机主界面「坐骑」按钮走这里。 */\n'
    '    public static void setMount(int k) {\n'
    '        if (sLive != null) sLive.setMountArt(k);\n'
    '    }\n\n'
    '    /** 外部（手机主界面「换动作」按钮）让桌面上的那只动一下。 */')

rep(P, '        /** 演一个动作。0 挥手 1 点头 2 小跳 3 蹲一下；外面（手机「换动作」）也走这里。 */',
    '        /** 换坐骑：0 无 1 祥云 2 木马，记进 SharedPreferences，下次启动还在。 */\n'
    '        void setMountArt(int k) {\n'
    '            mount = Math.max(0, Math.min(2, k));\n'
    '            try { getContext().getSharedPreferences("dao", 0).edit().putInt("mount", mount).apply(); } catch (Throwable e) { }\n'
    '            invalidate();\n'
    '        }\n\n'
    '        /** 演一个动作。0 挥手 1 点头 2 小跳 3 蹲一下；外面（手机「换动作」）也走这里。 */')

# 5) 桥
rep(B, '    @JavascriptInterface\n    public void warmUp() {',
    '    @JavascriptInterface\n    public void setMount(int k) {\n'
    '        try { DaoOverlay.setMount(k); } catch (Throwable e) { }\n'
    '    }\n\n'
    '    @JavascriptInterface\n    public void warmUp() {')

# 6) 页面按钮 + 交互
rep(H, '      <button id="btnDesk"><span class="lb">上桌面</span></button>',
    '      <button id="btnDesk"><span class="lb">上桌面</span></button>\n'
    '      <button id="btnMount"><span class="lb">坐骑</span></button>')

rep(H, '  // ---------- 对话 ----------',
    '  // 2026-11-25 坐骑：点一下轮换 无 → 祥云 → 木马 → 无，状态记在本机\n'
    '  var mountState = 0;\n'
    "  try { mountState = parseInt(localStorage.getItem('daoMount') || '0', 10) || 0; } catch (e) {}\n"
    '  var btnMount = document.getElementById(\'btnMount\');\n'
    '  var MOUNT_NAMES = [\'坐骑\', \'祥云\', \'木马\'];\n'
    '  function mountLabel() {\n'
    '    try { var lb = btnMount.querySelector(\'.lb\'); if (lb) lb.textContent = MOUNT_NAMES[mountState] || \'坐骑\'; } catch (e) {}\n'
    '  }\n'
    '  function mountApply() {\n'
    '    if (window.DaoNative && DaoNative.setMount) { try { DaoNative.setMount(mountState); } catch (e) {} }\n'
    '  }\n'
    '  if (btnMount) {\n'
    '    mountLabel();\n'
    '    mountApply();\n'
    '    btnMount.addEventListener(\'click\', function () {\n'
    '      mountState = (mountState + 1) % 3;\n'
    '      try { localStorage.setItem(\'daoMount\', String(mountState)); } catch (e) {}\n'
    '      mountLabel();\n'
    '      mountApply();\n'
    '      tip(mountState === 0 ? \'坐骑收起来了\' : (mountState === 1 ? \'祥云垫脚，托着你走\' : \'小木马驮你一段\'));\n'
    '    });\n'
    '  }\n\n'
    '  // ---------- 对话 ----------')

print('PATCH_OK 改动数=', n)

# ---- 判据 ----
j = open(P, encoding='utf-8').read()
b = open(B, encoding='utf-8').read()
h = open(H, encoding='utf-8').read()
s1 = 'mount_cloud.png' in j and 'mount_horse.png' in j
s2 = 'float rise = 0f;' in j and 'c.translate(0, -rise)' in j
s3 = 'public static void setMount(int k)' in j and 'public void setMount(int k)' in b
s4 = 'id="btnMount"' in h and 'DaoNative.setMount' in h and "MOUNT_NAMES = ['坐骑', '祥云', '木马']" in h
s5 = 'getSharedPreferences("dao", 0).getInt("mount", 0)' in j and 'putInt("mount", mount)' in j
for name, v in (('S1 两张坐骑素材被加载', s1), ('S2 坐骑先画+人物抬高鞍位', s2),
                ('S3 静态与桥接口都在', s3), ('S4 页面按钮+轮换+桥调用', s4),
                ('S5 坐骑状态持久化', s5)):
    print(name, 'PASS' if v else 'FAIL')
ok = all([s1, s2, s3, s4, s5])
print('SUMMARY', 'PASS' if ok else 'FAIL')
raise SystemExit(0 if ok else 1)
