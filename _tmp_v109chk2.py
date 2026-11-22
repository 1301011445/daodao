import zipfile,re
p=r"F:\Daodao\src\_apk\Dao.apk"
z=zipfile.ZipFile(p)
s=z.read("assets/dao.html").decode("utf-8","ignore")
print("HTML_VER", re.findall(r"HTML_VER = '([0-9]+)'", s))
print("START gate", "indexOf('START')" in s, "webFallbackPlay", "webFallbackPlay" in s)
d=z.read("classes.dex")
for k in ["AudioAttributes","AudioFormat","setUsage","USAGE_MEDIA","STREAM_MUSIC","setVolume","CONTENT_TYPE_MUSIC","daoSong","startHold"]:
    print(k, k.encode() in d)
print("dex len", len(d))
