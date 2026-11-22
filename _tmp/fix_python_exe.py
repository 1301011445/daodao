# -*- coding: utf-8 -*-
"""把 pet.cs 里 4 处裸 "python" 改成 PyExe()（PyExe 注释里自己写了：服务进程里解析不到 python）"""
import io

P = r'F:\Daodao\src\桌面分身\pet.cs'
s = io.open(P, encoding='utf-8').read()
n = s.count('new ProcessStartInfo("python",')
s = s.replace('new ProcessStartInfo("python",', 'new ProcessStartInfo(PyExe(),')
io.open(P, 'w', encoding='utf-8').write(s)
print('替换 %d 处裸 python' % n)
print('剩余 "python" 直接启动：', s.count('ProcessStartInfo("python"'))
