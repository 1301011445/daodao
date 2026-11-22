import struct, io
p=r"F:\Daodao\src\_apk\assets\music\guitu.adp"
b=open(p,"rb").read()
print("bytes",len(b))
sr,nf=struct.unpack("<II", b[4:12])
print("sr",sr,"frames",nf,"sec",round(nf*2048/sr,2))
ADP_STEP=[7,8,9,10,11,12,13,14,16,17,19,21,23,25,28,31,34,37,41,45,50,55,60,66,73,80,88,97,107,118,130,143,157,173,190,209,230,253,279,307,337,371,408,449,494,544,598,658,724,796,876,963,1060,1166,1282,1411,1552,1707,1878,2066,2272,2499,2749,3024,3327,3660,4026,4428,4871,5358,5894,6484,7132,7845,8630,9493,10442,11487,12635,13899,15289,16818,18500,20350,22385,24623,27086,29794,32767]
IDXT=[-1,-1,-1,-1,2,4,6,8,-1,-1,-1,-1,2,4,6,8]
peak=0; n=0; pos=12
for f in range(nf):
    pred=struct.unpack("<h", b[pos:pos+2])[0]; idx=b[pos+2]
    end=min(pos+1028,len(b))
    for by in b[pos+4:end]:
        for k in (0,1):
            code=(by>>4)&15 if k==0 else by&15
            step=ADP_STEP[idx]; delta=step>>3
            if code&4: delta+=step
            if code&2: delta+=step>>1
            if code&1: delta+=step>>2
            pred = pred-delta if code&8 else pred+delta
            pred=max(-32768,min(32767,pred))
            idx+=IDXT[code&7]; idx=max(0,min(88,idx))
            a=abs(pred)
            if a>peak: peak=a
            n+=1
    pos+=1028
print("samples",n,"peak",peak,"norm",round(peak/32767,4))