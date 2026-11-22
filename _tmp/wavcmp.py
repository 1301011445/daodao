import wave, struct
w=wave.open(r"F:\Daodao\_tmp\guitu_java.wav")
n=w.getnframes(); print("java 采样", n, "s r", w.getframerate())
d=w.readframes(8); print("java 前 8 采样", struct.unpack("<8h", d))
w.setpos(1000); print("java 1000 起 8 个", struct.unpack("<8h", w.readframes(8)))
