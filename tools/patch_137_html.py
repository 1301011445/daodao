# -*- coding: utf-8 -*-
import io,os
files=[r"F:\Daodao\src\_apk\assets\dao.html", r"F:\Daodao\道-随身版.html"]
old='''    // 换完报个名，不然你不知道换成了谁
    try { say('换了个模样：' + (WHO[species] || '它自己') + '。'); } catch (err) {}'''
new='''    // 2026-11-26 用户：App 里选的形象，手机桌面上的悬浮窗要跟着换，不能各显示各的
    try { if (window.DaoNative && DaoNative.setArt) DaoNative.setArt(species); } catch (err) {}
    // 换完报个名，不然你不知道换成了谁
    try { say('换了个模样：' + (WHO[species] || '它自己') + '。'); } catch (err) {}'''
for p in files:
    if not os.path.exists(p): print("skip",p); continue
    t=io.open(p,encoding="utf-8",errors="ignore").read()
    n=t.count(old)
    if n==0: print("FAIL",p); continue
    t=t.replace(old,new,1)
    t=t.replace("var HTML_VER = '136';","var HTML_VER = '137';")
    # 悬浮窗三处文案：把「多大」写清楚，用户在面板里能对上
    t=t.replace('<div id="ovFt">第一次用要在系统里放行「显示在其他应用上层」。',
                '<div id="ovFt">满身站着时约 15% 屏高（v137 放大过，能看清眉眼）。骑云/鹤/剑会上下飘着飞。第一次用要在系统里放行「显示在其他应用上层」。')
    io.open(p,"w",encoding="utf-8").write(t)
    print("OK",p,"setArt+version")
