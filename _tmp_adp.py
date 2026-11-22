import struct, os
d=r"F:\Daodao\src\_apk\assets\music"
for n in os.listdir(d):
    if not n.endswith(".adp"): continue
    b=open(os.path.join(d,n),"rb").read(12)
    sr=frames=None
    if b[:4]==b"DAO1":
        sr=struct.unpack("<i", b[4:8])[0]
        frames=struct.unpack("<i", b[8:12])[0]
    print(n, "sr=",sr,"frames=",frames,"sec=",round(frames*2048/sr,1) if sr and frames else None, "bytes=",os.path.getsize(os.path.join(d,n)))
