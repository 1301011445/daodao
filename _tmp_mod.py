mods = ["lameenc","pydub","soundfile","numpy","scipy"]
for m in mods:
    try:
        __import__(m); print(m, "OK")
    except Exception as e:
        print(m, "NO")
