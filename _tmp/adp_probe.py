import io, struct
p=r"F:\Daodao\src\_apk\assets\music\guitu.adp"
b=open(p,"rb").read()
print("文件字节", len(b))
print("magic", b[0:4])
sr=struct.unpack("<i", b[4:8])[0]; frames=struct.unpack("<i", b[8:12])[0]
print("sr", sr, "frames", frames, "推算采样数", frames*2048, "时长秒", round(frames*2048/sr,2))
print("按每帧1028字节推算应有字节", 12+frames*1028)
