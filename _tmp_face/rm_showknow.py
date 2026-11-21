import io
p=r'F:\Daodao\src\_apk\assets\dao.html'
lines=io.open(p,encoding='utf-8').read().split('\n')
i=[k for k,l in enumerate(lines) if l.strip().startswith('function showKnow()')]
print('showKnow 起始行(0基):', i)
if i:
    st=i[0]
    # 找到函数结束：从 st 开始找第一处纯 "  }" 的行
    en=None
    for k in range(st+1,len(lines)):
        if lines[k].strip()=='}' and lines[k].startswith('  }'):
            en=k; break
    print('结束行:', en, repr(lines[st]), repr(lines[en]))
    # 连同后面空行一起去掉
    del lines[st:en+1]
    while st < len(lines) and lines[st].strip()=='':
        del lines[st]
    io.open(p,'w',encoding='utf-8',newline='\n').write('\n'.join(lines))
    print('已删除 showKnow')
