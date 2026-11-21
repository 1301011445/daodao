import re, io, os
p = r"F:\Daodao\src\_apk\assets\dao.html"
s = io.open(p, encoding="utf-8", errors="replace").read()
blocks = re.findall(r"<script[^>]*>(.*?)</script>", s, re.S)
print("script blocks:", len(blocks), "sizes:", [len(b) for b in blocks])
outdir = r"F:\Daodao\_tmp_face"
for i, b in enumerate(blocks):
    fn = os.path.join(outdir, "blk%d.js" % i)
    io.open(fn, "w", encoding="utf-8").write(b)
    print("wrote", fn, len(b))
