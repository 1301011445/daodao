# -*- coding: utf-8 -*-
"""把记事本的点击绑定从第一个 script 块挪到第二个（noteOpen/noteAct 都在第二块里，跨块调不到）。"""
import io, re

SRC = r'F:\Daodao\src\_apk\assets\dao.html'
html = io.open(SRC, encoding='utf-8').read()

block = """  var noteBtn = document.getElementById('btnNote');
  if (noteBtn) noteBtn.addEventListener('pointerdown', function (e) { if (e) e.preventDefault(); noteOpen(); });
  var noteCl = document.getElementById('noteClose');
  if (noteCl) noteCl.addEventListener('pointerdown', function (e) { if (e) e.preventDefault(); noteClose(); });
  var noteBg = document.getElementById('notePanel');
  if (noteBg) noteBg.addEventListener('pointerdown', function (e) { if (e.target === noteBg) noteClose(); });
  var noteLst = document.getElementById('noteList');
  if (noteLst) noteLst.addEventListener('click', function (e) {
    var t = e.target || {};
    var op = t.getAttribute ? t.getAttribute('data-op') : null;
    if (!op) return;
    e.preventDefault();
    noteAct(op, t.getAttribute('data-id'));
  });

"""
assert block in html, '绑定块没找到'
html = html.replace(block, '', 1)

# 放到第二块末尾（最后一个 </script> 之前）
last = html.rfind('</script>')
html = html[:last] + block.rstrip() + "\n  " + html[last:]

io.open(SRC, 'w', encoding='utf-8', newline='').write(html)
print('绑定已挪到第二块，文件 %d 字节' % len(html))
