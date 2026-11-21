# -*- coding: utf-8 -*-
import re, io, subprocess, os, tempfile, json
p=r'F:\Daodao\src\_apk\assets\dao.html'
s=io.open(p,encoding='utf-8').read()
blocks=re.findall(r'<script>(.*?)</script>', s, re.S)
print('脚本块数', len(blocks), [len(b) for b in blocks])
b1, b2 = blocks[0], blocks[-1]
def names(t):
    fns=set(re.findall(r'function\s+([A-Za-z_$][\w$]*)\s*\(', t))
    vs=set(re.findall(r'\bvar\s+([A-Za-z_$][\w$]*)', t))
    return fns|vs
n1=names(b1); n2=names(b2)
used2=set(re.findall(r'\b([A-Za-z_$][\w$]*)\s*\(', b2))
missing=sorted(x for x in (used2 - n2) if x in n1)
print('第二块调用了、但只定义在第一块的标识符:', missing)
# 语法检查
for i,b in enumerate(blocks):
    f=os.path.join(tempfile.gettempdir(), 'blk%d.js'%i)
    io.open(f,'w',encoding='utf-8').write(b)
    r=subprocess.run([r'C:\Users\LDY\AppData\Local\Doubao\User Data\sandbox_runtime\bases\fa694f517e5995233c80a9a8db5212c2\node\node.exe','--check',f],capture_output=True,text=True)
    print('block%d 语法检查 %s %s'%(i,'OK' if r.returncode==0 else 'FAIL', (r.stderr or '').strip()[:300]))
