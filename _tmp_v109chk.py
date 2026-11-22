import zipfile,sys
p=r"F:\Daodao\src\_apk\Dao.apk"
z=zipfile.ZipFile(p)
h=[n for n in z.namelist() if n.endswith("dao.html")]
print("html entries",h)
s=z.read(h[0]).decode("utf-8","ignore")
import re
print("HTML_VER",re.findall(r"HTML_VER = '(\\d+)'",s))
print("daoSong", "__daoSong" in s, "START", "START" in s)
print("bak", [n for n in z.namelist() if ".bak" in n])
print("dex", [n for n in z.namelist() if n.endswith(".dex")])
print("music", [n for n in z.namelist() if "music/" in n])
d=z.read("classes.dex")
for k in [b"playSongAsset",b"decodePcm",b"playPcm",b"_daoSong",b"AUDIO_SESSION_ID_GENERATE",b"USAGE_MEDIA",b"WRITE_BLOCKING",b"writeWavFile",b"MediaPlayer"]:
    print(k.decode(), k in d)
