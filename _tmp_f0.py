from PIL import Image
im=Image.open(r"F:\Daodao\src\_apk\assets\walk8.png").convert("RGBA")
im.crop((0,0,192,384)).save(r"C:\Users\LDY\Doubao\chats\2026-11-11\new-chat\道_第0帧.png")
print("ok")
