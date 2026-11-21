import io
def sub(path, olds, new, cnt=1):
    s = io.open(path, encoding="utf-8").read()
    for o in olds:
        if o in s:
            s = s.replace(o, new, cnt)
            io.open(path, "w", encoding="utf-8").write(s)
            print("OK  ", path, "|", o.strip()[:60], "->", new.strip()[:60])
            return True
    print("MISS", path); return False

sub(r"F:\Daodao\src\桌面分身\pet.cs", ["public const int APP_VER = 85;"], "public const int APP_VER = 86;")
sub(r"F:\Daodao\src\_apk\assets\dao.html", ["var HTML_VER='85';"], "var HTML_VER='86';")
sub(r"F:\Daodao\src\_apk\AndroidManifest.xml",
    ['android:versionCode="85"'], 'android:versionCode="86"')
sub(r"F:\Daodao\src\_apk\AndroidManifest.xml",
    ['android:versionName="0.85">'], 'android:versionName="0.86">')
# 随身版网页副本
import shutil, os
desk = r"C:\Users\LDY\Desktop\道-随身版.html"
try:
    shutil.copyfile(r"F:\Daodao\src\_apk\assets\dao.html", desk)
    print("OK   随身版已复制")
except Exception as e:
    print("随身版复制失败：", e)
