# -*- coding: utf-8 -*-
"""给手机端补一个看得见的记事本入口：底部第四个按钮 + 全屏清单（点一下划掉，长按删）。"""
import io, re, sys

SRC = r'F:\Daodao\src\_apk\assets\dao.html'
html = io.open(SRC, encoding='utf-8').read()

# 1) 底部小按钮改成四格，并加「记事本」
old_grid = '#bar .minis { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 9px; width: 100%; }'
new_grid = '#bar .minis { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 7px; width: 100%; }'
assert old_grid in html
html = html.replace(old_grid, new_grid)

# 2) 按钮本体
old_btn = '''      <button id="btnSong"><span class="lb">唱歌</span></button>'''
new_btn = '''      <button id="btnSong"><span class="lb">唱歌</span></button>
      <button id="btnNote"><span class="lb">记事本</span></button>'''
assert old_btn in html
html = html.replace(old_btn, new_btn)

# 3) 面板骨架（放进 #stage 末尾，fixed 盖整屏）
old_pc = '''    <div id="pcPanel">
      <button id="pcSync">同步记忆</button>
      <button id="pcUpd">查新版本</button>
    </div>'''
new_pc = old_pc + '''
    <div id="notePanel">
      <div id="noteCard">
        <div id="noteHd"><b>记事本</b><button id="noteClose" aria-label="关上">×</button></div>
        <div id="noteList"></div>
        <div id="noteFt">点「✓」算做完，点「×」删掉这条</div>
      </div>
    </div>'''
assert old_pc in html
html = html.replace(old_pc, new_pc)

# 4) 样式
old_style = '''  #pcPanel.show { display: flex; }'''
new_style = old_style + '''
  #notePanel {
    position: fixed; inset: 0; display: none; z-index: 60;
    background: rgba(5,9,18,.78); backdrop-filter: blur(6px);
  }
  #notePanel.show { display: flex; align-items: flex-end; }
  #noteCard {
    width: 100%; max-height: 76vh; display: flex; flex-direction: column;
    background: rgba(15,21,38,.98); border: 1px solid rgba(120,150,220,.24);
    border-radius: 18px 18px 0 0; overflow: hidden;
  }
  #noteHd {
    display: flex; align-items: center; justify-content: space-between;
    padding: 14px 16px; border-bottom: 1px solid rgba(120,150,220,.14);
    color: #e6edff; font-size: 15px;
  }
  #noteHd b { font-weight: 600; letter-spacing: .6px; }
  #noteHd button { background: none; border: 0; color: #9fb0d0; font-size: 20px; padding: 0 4px; line-height: 1; }
  #noteList { flex: 1; overflow: auto; padding: 4px 12px 8px; }
  #noteList .empty { color: #8b9ab8; font-size: 13px; text-align: center; padding: 30px 0 36px; }
  #noteList .grp { color: #8fa4c8; font-size: 12px; letter-spacing: 1px; margin: 12px 4px 2px; }
  #noteList .row {
    display: flex; align-items: center; gap: 10px; padding: 10px;
    margin: 6px 0; border-radius: 12px;
    background: rgba(255,255,255,.05); border: 1px solid rgba(255,255,255,.07);
  }
  #noteList .row.done { opacity: .52; }
  #noteList .tm { min-width: 62px; font-size: 12.5px; color: #9fb2d6; line-height: 1.35; }
  #noteList .tx { flex: 1; font-size: 14px; color: #e8eeff; line-height: 1.45; word-break: break-all; }
  #noteList .tx small { display: block; margin-top: 3px; font-size: 11.5px; color: #7f90ad; }
  #noteList .op { display: flex; gap: 6px; }
  #noteList .op button {
    width: 36px; height: 34px; border-radius: 10px; font-size: 15px; line-height: 1;
    border: 1px solid rgba(130,170,255,.30); background: rgba(118,158,255,.16); color: #dbe6ff;
  }
  #noteList .op .ok { color: #a8e0b8; border-color: rgba(120,220,150,.34); background: rgba(90,200,130,.14); }
  #noteList .op .rm { color: #f0b0b0; border-color: rgba(230,130,130,.32); background: rgba(230,110,110,.12); }
  #noteFt { padding: 10px 16px 16px; text-align: center; font-size: 12px; color: #8393b1; }'''
assert old_style in html
html = html.replace(old_style, new_style)

# 5) 逻辑：渲染清单、做完、删掉、打开/关上
anchor = """      try { localStorage.setItem(NOTE_LIST, JSON.stringify(arr)); } catch (e) {}
      phoneAlarmAll(arr);
    }).catch(function () {});
  }
"""
assert anchor in html
logic = anchor + """
  // v0.107：记事本不再是"只能靠嘴找"，底部第四个按钮直接把清单摊开
  function noteArr() {
    var a = [];
    try { a = JSON.parse(localStorage.getItem(NOTE_LIST) || '[]') || []; } catch (e) { a = []; }
    return a;
  }
  function noteEsc(s) {
    return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }
  function noteDayLabel(w) {
    var m = String(w || '').match(/^(\\d{4})-(\\d{2})-(\\d{2})\\s+(\\d{2}):(\\d{2})/);
    if (!m) return ['', String(w || '')];
    var d = new Date(+m[1], +m[2] - 1, +m[3]);
    var t0 = new Date(); t0.setHours(0, 0, 0, 0);
    var d0 = new Date(d.getTime()); d0.setHours(0, 0, 0, 0);
    var diff = Math.round((d0 - t0) / 86400000);
    var day = diff === 0 ? '今天' : diff === 1 ? '明天' : diff === -1 ? '昨天' : (diff < 0 ? '逾期' : (+m[2]) + '月' + (+m[3]) + '日');
    return [day, (+m[4]) + '点' + (m[5] === '00' ? '' : (+m[5]) + '分')];
  }
  function noteRender() {
    var box = document.getElementById('noteList');
    if (!box) return;
    var arr = noteArr(), out = '', pend = 0, lastGrp = '';
    var nowMs = Date.now();
    for (var i = 0; i < arr.length; i++) {
      var o = arr[i];
      if (String(o.done) === '1') continue;
      pend++;
      var lb = noteDayLabel(o.when), g = lb[0] || '待办';
      if (g !== lastGrp) { out += '<div class="grp">' + noteEsc(g) + '</div>'; lastGrp = g; }
      var ms = new Date(String(o.when).replace(/-/g, '/') + ':00').getTime();
      var late = ms && ms < nowMs;
      out += '<div class="row"><div class="tm">' + noteEsc(lb[1]) +
             '</div><div class="tx">' + noteEsc(o.text) +
             (late ? '<small>已过点，还没划掉</small>' : '') +
             '</div><div class="op"><button class="ok" data-op="done" data-id="' + noteEsc(o.id) + '">✓</button>' +
             '<button class="rm" data-op="del" data-id="' + noteEsc(o.id) + '">×</button></div></div>';
    }
    var doneRows = '';
    for (var j = 0; j < arr.length; j++) if (String(arr[j].done) === '1') { doneRows += arr[j].text + '；'; }
    if (!out) out = '<div class="empty">还没有登记的事。<br>说一句「记一下 明天九点 交表」就行。</div>';
    if (doneRows) out += '<div class="grp">已完成</div><div class="empty" style="padding:10px 6px;text-align:left">' + noteEsc(doneRows) + '</div>';
    box.innerHTML = out;
    var ft = document.getElementById('noteFt');
    if (ft) ft.textContent = pend ? ('还有 ' + pend + ' 件没做完 · 点「✓」算做完，点「×」删掉这条') : '点「✓」算做完，点「×」删掉这条';
  }
  function noteAct(op, id) {
    var arr = noteArr();
    for (var i = 0; i < arr.length; i++) {
      if (String(arr[i].id) !== String(id)) continue;
      if (op === 'done') arr[i].done = '1';
      break;
    }
    if (op === 'del') {
      var keep = [];
      for (var k = 0; k < arr.length; k++) if (String(arr[k].id) !== String(id)) keep.push(arr[k]);
      arr = keep;
    }
    try { localStorage.setItem(NOTE_LIST, JSON.stringify(arr)); } catch (e) {}
    noteRender();
    fetch('http://' + pcIp + ':8848/note?op=' + op + '&id=' + encodeURIComponent(id))
      .then(function (r) { return r.text(); })
      .then(function (s) {
        if (s.indexOf('OK') !== 0) { tip('电脑那边没改成：' + s); }
        setTimeout(function () { try { noteSync(); } catch (e) {} }, 600);
      })
      .catch(function () { tip('电脑没连上，先记在手机上，连上会自己同步'); });
  }
  function noteOpen() {
    var p = document.getElementById('notePanel');
    if (!p) return;
    noteRender();
    p.classList.add('show');
    try { noteSync(); } catch (e) {}
  }
  function noteClose() {
    var p = document.getElementById('notePanel');
    if (p) p.classList.remove('show');
  }
"""
html = html.replace(anchor, logic)

# 6) 事件绑定：按钮、关、遮罩、行内两个操作
old_bind = """  document.getElementById('btnSwap').addEventListener('pointerdown', function (e) {"""
new_bind = """  var noteBtn = document.getElementById('btnNote');
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

  document.getElementById('btnSwap').addEventListener('pointerdown', function (e) {"""
assert old_bind in html
html = html.replace(old_bind, new_bind)

io.open(SRC, 'w', encoding='utf-8', newline='').write(html)
print('OK 补丁写完，文件 %d 字节' % len(html))
print('  记事本按钮：', 'id="btnNote"' in html, '｜面板：', 'id="notePanel"' in html,
      '｜函数：', all(f in html for f in ('function noteOpen', 'function noteAct', 'function noteRender')))
