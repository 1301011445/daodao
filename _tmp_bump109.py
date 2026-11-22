# 程序版本：v0.1 | 2026-11-22 | 一次性：0.109 版本号 +1（修手机端唱歌卡死/无声）
import io
def sub(p, old, new, enc='utf-8'):
    s = io.open(p, encoding=enc).read()
    assert old in s, (p, old)
    io.open(p, 'w', encoding=enc).write(s.replace(old, new, 1))
    print('OK', p)

sub(r'F:\Daodao\src\_apk\assets\dao.html', "var HTML_VER = '108';", "var HTML_VER = '109';")
sub(r'F:\Daodao\src\桌面分身\pet.cs', 'public const int APP_VER = 108;', 'public const int APP_VER = 109;')
sub(r'F:\Daodao\src\_apk\AndroidManifest.xml', 'android:versionCode="108"', 'android:versionCode="109"')
sub(r'F:\Daodao\src\_apk\AndroidManifest.xml', 'android:versionName="0.108"', 'android:versionName="0.109"')
