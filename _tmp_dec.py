import struct
STEP=[7,8,9,10,11,12,13,14,16,17,19,21,23,25,28,31,34,37,41,45,50,55,60,66,73,80,88,97,107,118,130,143,157,173,190,209,230,253,279,307,337,371,408,449,494,543,598,658,724,796,876,963,1060,1166,1282,1411,1552,1707,1878,2066,2272,2499,2749,3024,3327,3660,4026,4428,4871,5358,5894,6484,7132,7845,8630,9493,10442,11487,12635,13899,15289,16818,18500,20352,22390,24621,27083,29792,32767]
IDX=[-1,-1,-1,-1,2,4,6,8,-1,-1,-1,-1,2,4,6,8]
def decode(data, maxframes=4000):
    pos=12; out=[]; peaks=0; clip=0
    frames=0
    while frames<maxframes and pos+4<len(data):
        pred=struct.unpack("<h", data[pos:pos+2])[0]
        idx=data[pos+2]&0xff
        end=min(pos+1028,len(data))
        for b in range(pos+4,end):
            by=data[b]
            for k in (0,1):
                code=(by>>4) if k==0 else (by&15)
                idx=max(0,min(88,idx))
                step=STEP[idx]
                delta=step>>3
                if code&4: delta+=step
                if code&2: delta+=step>>1
                if code&1: delta+=step>>2
                pred = pred-delta if code&8 else pred+delta
                if pred>32767: pred=32767; clip+=1
                elif pred<-32768: pred=-32768; clip+=1
                idx+=IDX[code&7]
                out.append(pred)
        pos+=1028; frames+=1
    return out, clip
import os
for n in ["guitu","gongzuo","shaonian"]:
    p=rf"F:\Daodao\src\_apk\assets\music\{n}.adp"
    d=open(p,"rb").read()
    o,clip=decode(d, 1200)
    peak=max(max(o),-min(o))
    import math
    rms=math.sqrt(sum(x*x for x in o)/len(o))
    print(n,"samples",len(o),"peak",peak,"rms",round(rms),"clip",clip)
