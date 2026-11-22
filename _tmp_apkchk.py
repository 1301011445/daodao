import zipfile,io,re,subprocess
p=r"F:\Daodao\src\_apk\Dao.apk"
z=zipfile.ZipFile(p)
names=z.namelist()
print("entries",len(names),"dex", "classes.dex" in names, z.getinfo("classes.dex").file_size if "classes.dex" in names else 0)
print("bak", [n for n in names if n.endswith(".bak") or ".bak_" in n][:3])
h=z.read("assets/dao.html").decode("utf-8")
print("HTML_VER", re.search(r"HTML_VER\s*=\s*'(\d+)'",h).group(1))
print("has setStatus","function setStatus" in h,"songDiag","songDiag" in h)
d=z.read("classes.dex")
print("dex bytes",len(d), "decodeFrame", b"decodeFrame" in d, "songPos", b"songPos" in d, "songDiag", b"songDiag" in d, "decodePcm", b"decodePcm" in d)
print("music", [n for n in names if n.startswith("assets/music/")])