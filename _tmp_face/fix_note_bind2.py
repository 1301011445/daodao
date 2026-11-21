# -*- coding: utf-8 -*-
"""记事本函数挂在 window 上，点击绑定无论落在哪个闭包里都能调到。"""
import io
SRC = r'F:\Daodao\src\_apk\assets\dao.html'
html = io.open(SRC, encoding='utf-8').read()

anchor = """  function noteClose() {
    var p = document.getElementById('notePanel');
    if (p) p.classList.remove('show');
  }
"""
shim = anchor + """  // 这两个函数在闭包里，底部按钮的绑定在另一层，挂到 window 上才不会"noteOpen is not defined"
  try { window.__noteOpen = noteOpen; window.__noteClose = noteClose; window.__noteAct = noteAct; } catch (e) {}
"""
assert anchor in html
html = html.replace(anchor, shim, 1)

old_bind = """  var noteBtn = document.getElementById('btnNote');
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
  });"""
new_bind = """  (function () {
    var noteBtn = document.getElementById('btnNote');
    if (noteBtn) noteBtn.addEventListener('pointerdown', function (e) { if (e) e.preventDefault(); if (window.__noteOpen) window.__noteOpen(); });
    var noteCl = document.getElementById('noteClose');
    if (noteCl) noteCl.addEventListener('pointerdown', function (e) { if (e) e.preventDefault(); if (window.__noteClose) window.__noteClose(); });
    var noteBg = document.getElementById('notePanel');
    if (noteBg) noteBg.addEventListener('pointerdown', function (e) { if (e.target === noteBg && window.__noteClose) window.__noteClose(); });
    var noteLst = document.getElementById('noteList');
    if (noteLst) noteLst.addEventListener('click', function (e) {
      var t = e.target || {};
      var op = t.getAttribute ? t.getAttribute('data-op') : null;
      if (!op) return;
      e.preventDefault();
      if (window.__noteAct) window.__noteAct(op, t.getAttribute('data-id'));
    });
  })();"""
assert old_bind in html
html = html.replace(old_bind, new_bind, 1)

io.open(SRC, 'w', encoding='utf-8', newline='').write(html)
print('window 挂载 + 绑定改成 window 调用，完成')
