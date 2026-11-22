import io,re
# 1) 版本号 108 -> 109
p1=r"F:\Daodao\src\桌面分身\pet.cs"; s=io.open(p1,encoding="utf-8",errors="surrogateescape").read()
assert "public const int APP_VER = 108;" in s
s=s.replace("public const int APP_VER = 108;","public const int APP_VER = 109;",1)
io.open(p1,"w",encoding="utf-8",errors="surrogateescape").write(s)
p2=r"F:\Daodao\src\_apk\assets\dao.html"; h=io.open(p2,encoding="utf-8").read()
h=re.sub(r"HTML_VER\s*=\s*'108'","HTML_VER = '109'",h,count=1)
io.open(p2,"w",encoding="utf-8").write(h)
p3=r"F:\Daodao\src\_apk\AndroidManifest.xml"; m=io.open(p3,encoding="utf-8").read()
m=m.replace('android:versionCode="108"','android:versionCode="109"').replace('android:versionName="0.108"','android:versionName="0.109"')
io.open(p3,"w",encoding="utf-8").write(m)
print("ver bump ok")

# 2) 体检脚本 dex 关键名跟上新版
p4=r"F:\Daodao\tools\两端自用体检.py"; t=io.open(p4,encoding="utf-8").read()
t=t.replace("all(k in dex for k in ('playSongAsset', 'playPcm', 'assetXhr'))",
            "all(k in dex for k in ('playSongAsset', 'decodeFrame', 'songPos', 'songDiag', 'assetXhr'))")
t=t.replace("('function startHold' in html) and ('win = null' in html)",
            "('function startHold' in html) and ('win = null' in html) and ('function setStatus' in html) and ('songDiag' in html)")
io.open(p4,"w",encoding="utf-8").write(t)
print("体检脚本已跟上新线索")