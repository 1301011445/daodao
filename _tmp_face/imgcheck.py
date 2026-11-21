import re, io, base64, struct, os
p = r"F:\Daodao\src\_apk\assets\dao.html"
s = io.open(p, encoding="utf-8", errors="replace").read()
uris = re.findall(r"data:image/(png|jpeg|webp);base64,([A-Za-z0-9+/=]+)", s)
print("data-uri 数量:", len(uris))
bad = 0
for i, (fmt, b64) in enumerate(uris):
    try:
        raw = base64.b64decode(b64, validate=True)
    except Exception as e:
        print("  [%d] base64 解码失败: %s" % (i, e)); bad += 1; continue
    if fmt == "png":
        if len(raw) < 33 or raw[:8] != b"\x89PNG\r\n\x1a\n":
            print("  [%d] PNG 头不对 len=%d head=%r" % (i, len(raw), raw[:8])); bad += 1; continue
        w, h = struct.unpack(">II", raw[16:24])
        end = raw.rstrip()[-12:]
        print("  [%d] png %dx%d  %d bytes  tail=%r" % (i, w, h, len(raw), end))
print("损坏数:", bad)
