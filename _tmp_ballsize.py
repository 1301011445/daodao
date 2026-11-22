from PIL import Image
p=r"F:\Daodao\src\_apk\assets\ball.png"
im=Image.open(p)
print("now", im.size, round(__import__("os").path.getsize(p)/1024,1), "KB")
im=im.resize((320,320), Image.LANCZOS)
im.save(p, optimize=True)
print("after", im.size, round(__import__("os").path.getsize(p)/1024,1), "KB")
