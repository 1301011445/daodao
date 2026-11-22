import io,re
p=r"F:\Daodao\src\桌面分身\pet.cs"
s=io.open(p,encoding="utf-8",errors="surrogateescape").read()
assert "_tmp_onpaint_anchor" not in s
old="""            // 开机不再一句接一句地自己播报（简报、记忆、今日所学都挪到右键菜单里，
            // 想看再点）。话只在两处出现：他要的早晚问候，还有用户点它或喊它的时候。
        }"""
assert old in s
new="""            // 开机不再一句接一句地自己播报（简报、记忆、今日所学都挪到右键菜单里，
            // 想看再点）。话只在两处出现：他要的早晚问候，还有用户点它或喊它的时候。
            // 上次选的是「贴边偷看」或「悬浮球」，开机就直接按那个样子待着
            if (petMode == 1 || petMode == 2) SetModeWindow();
        }"""
s=s.replace(old,new,1)
# 版本 109 -> 110
s=s.replace("public const int APP_VER = 109;","public const int APP_VER = 110;",1)
io.open(p,"w",encoding="utf-8",errors="surrogateescape").write(s)
print("pet.cs patched, APP_VER=110")
h=r"F:\Daodao\src\_apk\assets\dao.html"
t=io.open(h,encoding="utf-8").read()
t=re.sub(r"HTML_VER\s*=\s*'109'","HTML_VER = '110'",t,count=1)
io.open(h,"w",encoding="utf-8").write(t)
m=r"F:\Daodao\src\_apk\AndroidManifest.xml"
x=io.open(m,encoding="utf-8").read()
x=x.replace('android:versionCode="109"','android:versionCode="110"').replace('android:versionName="0.109"','android:versionName="0.110"')
io.open(m,"w",encoding="utf-8").write(x)
print("phone side bumped 110")