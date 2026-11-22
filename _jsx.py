import io,re
s=io.open(r"F:\Daodao\src\_apk\assets\dao.html",encoding="utf-8").read()
blocks=re.findall(r"<script[^>]*>(.*?)</script>",s,re.S)
open(r"F:\Daodao\_jscheck.js","w",encoding="utf-8").write(max(blocks,key=len))
print("blocks",len(blocks),"size",len(max(blocks,key=len)))
