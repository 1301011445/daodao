import glob, os, shutil
from PIL import Image

bundle = r'F:\Daodao\src\桌面分身\_bundle'
bak = r'F:\Daodao\src\_bak\ridef_20261128_shrink'
os.makedirs(bak, exist_ok=True)
report = []
for f in sorted(glob.glob(os.path.join(bundle, 'ridef_*.png'))):
    name = os.path.basename(f)
    b = os.path.join(bak, name)
    if not os.path.exists(b):
        shutil.copy2(f, b)
    im = Image.open(b).convert('RGBA')
    w, h = im.size
    nh = 820
    nw = max(1, round(w * nh / h))
    im2 = im.resize((nw, nh), Image.LANCZOS)
    im2.save(f, optimize=True)
    report.append((name, os.path.getsize(b)//1024, os.path.getsize(f)//1024))
tot_old = sum(r[1] for r in report); tot_new = sum(r[2] for r in report)
for r in report: print(f'{r[0]}: {r[1]}K -> {r[2]}K')
print(f'TOTAL {tot_old}K -> {tot_new}K')
