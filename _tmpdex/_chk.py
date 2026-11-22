import struct
d=open(r"F:\Daodao\_tmpdex\classes.dex","rb").read()
print("dex bytes", len(d))
print("0.52 present:", d.count(b"\xb8\x1e\x05\x3f"))
print("0.79 present:", d.count(b"\xcd\xcc\x4c\x3f"))
print("0.26 present:", d.count(b"\x8f\xc2\x85\x3e"))
