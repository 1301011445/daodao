# -*- coding: utf-8 -*-
"""清单按时间排序：逾期 → 今天 → 明天 → 以后，同一组内按点数先后。"""
import io
SRC = r'F:\Daodao\src\_apk\assets\dao.html'
html = io.open(SRC, encoding='utf-8').read()

old = """    var arr = noteArr(), out = '', pend = 0, lastGrp = '';
    var nowMs = Date.now();"""
new = """    var arr = noteArr(), out = '', pend = 0, lastGrp = '';
    var nowMs = Date.now();
    arr.sort(function (a, b) { return String(a.when || '').localeCompare(String(b.when || '')); });"""
assert old in html
html = html.replace(old, new, 1)

io.open(SRC, 'w', encoding='utf-8', newline='').write(html)
print('排序补丁完成')
