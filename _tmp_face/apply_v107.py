# -*- coding: utf-8 -*-
"""v0.107 一次性打补丁（从 git HEAD 的原版页面开始，避免在改坏的中间文件上继续叠）：
1) 底部第四个按钮「记事本」+ 全屏清单（点 ✓ 划掉、点 × 删掉）
2) 表情白名单：只有 4/5/8/9/10 这五只换表情图，避免"少女一秒变熊猫"
3) 立绘与这五只的表情图换成桌面同一套高清手办图（webp）
"""
import io, os, re, base64
from PIL import Image

HEAD = r'F:\Daodao\_tmp_face\gitver\dao_head.html'
CUR = r'F:\Daodao\src\_apk\assets\dao.html'
BUNDLE = r'F:\Daodao\src\桌面分身\_bundle'
KEYS = ['happy', 'sad', 'angry', 'sleep']
EXPR_OK = [4, 5, 8, 9, 10]

html = io.open(HEAD, encoding='utf-8').read()

# ---------- A. 底部第四个按钮 ----------
old_grid = '#bar .minis { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 9px; width: 100%; }'
html = html.replace(old_grid, '#bar .minis { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 7px; width: 100%; }')

old_btn = '      <button id="btnSong"><span class="lb">唱歌</span></button>'
assert old_btn in html
html = html.replace(old_btn, old_btn + '\n      <button id="btnNote"><span class="lb">记事本</span></button>')

# ---------- B. 面板骨架 ----------
old_pc = '''    <div id="pcPanel">
      <button id="pcSync">同步记忆</button>
      <button id="pcUpd">查新版本</button>
    </div>'''
assert old_pc in html
panel = old_pc + '''
    <div id="notePanel">
      <div id="noteCard">
        <div id="noteHd"><b>记事本</b><button id="noteClose" aria-label="关上">×</button></div>
        <div id="noteList"></div>
        <div id="noteFt">点「✓」算做完，点「×」删掉这条</div>
      </div>
    </div>'''
html = html.replace(old_pc, panel)

# ---------- C. 样式 ----------
old_style = '  #pcPanel.show { display: flex; }'
assert old_style in html
html = html.replace(old_style, old_style + '''
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
  #noteFt { padding: 10px 16px 16px; text-align: center; font-size: 12px; color: #8393b1; }''')

# ---------- D. 逻辑 + 绑定（都放进有 pcIp/noteSync 的那个块） ----------
anchor = """      try { localStorage.setItem(NOTE_LIST, JSON.stringify(arr)); } catch (e) {}
      phoneAlarmAll(arr);
    }).catch(function () {});
  }
"""
assert anchor in html
logic = anchor + """
  // v0.107：记事本不再是"只能靠嘴问"，底部第四个按钮直接把清单摊开
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
    var day = diff === 0 ? '今天' : diff === 1 ? '明天' : diff === -1 ? '昨天' : (diff < 0 ? '逾期' : ((+m[2]) + '月' + (+m[3]) + '日'));
    return [day, (+m[4]) + '点' + (m[5] === '00' ? '' : ((+m[5]) + '分'))];
  }
  function noteRender() {
    var box = document.getElementById('noteList');
    if (!box) return;
    var arr = noteArr(), out = '', pend = 0, lastGrp = '', nowMs = Date.now();
    arr.sort(function (a, b) { return String(a.when || '').localeCompare(String(b.when || '')); });
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
    var arr = noteArr(), keep = [], i;
    for (i = 0; i < arr.length; i++) if (String(arr[i].id) === String(id) && op === 'done') arr[i].done = '1';
    if (op === 'del') {
      for (i = 0; i < arr.length; i++) if (String(arr[i].id) !== String(id)) keep.push(arr[i]);
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

  (function () {
    var b = document.getElementById('btnNote');
    if (b) b.addEventListener('pointerdown', function (e) { if (e) e.preventDefault(); noteOpen(); });
    var c = document.getElementById('noteClose');
    if (c) c.addEventListener('pointerdown', function (e) { if (e) e.preventDefault(); noteClose(); });
    var bg = document.getElementById('notePanel');
    if (bg) bg.addEventListener('pointerdown', function (e) { if (e.target === bg) noteClose(); });
    var ls = document.getElementById('noteList');
    if (ls) ls.addEventListener('click', function (e) {
      var t = e.target || {};
      var op = t.getAttribute ? t.getAttribute('data-op') : null;
      if (!op) return;
      e.preventDefault();
      noteAct(op, t.getAttribute('data-id'));
    });
  })();
"""
html = html.replace(anchor, logic, 1)

# ---------- E. 表情白名单 ----------
old_sp = """  function spriteFor(sp) {
    if (emo >= 0 && emoLeft > 0) {"""
assert old_sp in html
html = html.replace(old_sp, """  // v0.107：只有表情图和立绘是"同一个角色、同一画风、整身"的五只才换表情图。
  // 0 橘猫 / 1 白兔 / 2 狐狸 / 3 熊猫 的表情原来是动物卡通，6 蓝发 / 11 机械是另一种画风，
  // 7 黑发只有头肩特写——这些一律保住立绘，宁可只靠姿势和动作，也不要"少女一秒变熊猫"。
  var EXPR_OK = { 4: 1, 5: 1, 8: 1, 9: 1, 10: 1 };
  function spriteFor(sp) {
    if (emo >= 0 && emoLeft > 0 && EXPR_OK[sp]) {""")

# ---------- F. 立绘 / 五只表情换桌面高清图 ----------
def span(text, head):
    i = text.index(head)
    depth = 0
    for j in range(i, len(text)):
        if text[j] == '[':
            depth += 1
        elif text[j] == ']':
            depth -= 1
            if depth == 0:
                return i, j + 2
    raise RuntimeError('no end ' + head)

def rows_of(text, head):
    i = text.index(head) + len(head)
    depth, i0, rows = 1, None, []
    while i < len(text):
        c = text[i]
        if c == '[':
            depth += 1
            if depth == 2:
                i0 = i + 1
        elif c == ']':
            if depth == 2 and i0 is not None:
                rows.append(text[i0:i]); i0 = None
            depth -= 1
            if depth == 0:
                return rows, i + 2
        i += 1
    raise RuntimeError('rows no end')

def webp_b64(path, height, q):
    im = Image.open(path).convert('RGBA')
    k = height / float(im.height)
    im = im.resize((max(1, int(round(im.width * k))), height), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, 'WEBP', quality=q, method=6)
    return '"data:image/webp;base64,' + base64.b64encode(buf.getvalue()).decode('ascii') + '"'

# 先拿原 EXPRS 的 12 行（换图之前解析，保险）
orig_rows, _ = rows_of(html, 'var EXPRS = [')

face_lines = []
for i in range(14):
    face_lines.append('    ' + webp_b64(os.path.join(BUNDLE, 'face_%d.png' % i), 420, 82))
a0, a1 = span(html, 'var FACES = [')
html = html[:a0] + 'var FACES = [\n' + ',\n'.join(face_lines) + '\n  ];' + html[a1:]

new_rows = []
for r in range(12):
    if r in EXPR_OK:
        items = [webp_b64(os.path.join(BUNDLE, 'expr_%d_%s.png' % (r, k)), 380, 80) for k in KEYS]
        new_rows.append('  [' + ',\n   '.join(items) + ']')
    else:
        new_rows.append('  [' + re.sub(r'\s+', ' ', orig_rows[r].strip()) + ']')
b0, b1 = span(html, 'var EXPRS = [')
html = html[:b0] + 'var EXPRS = [\n' + ',\n'.join(new_rows) + '\n  ];' + html[b1:]

io.open(CUR, 'w', encoding='utf-8', newline='').write(html)
print('v0.107 页面写出：%.0f KB' % (len(html.encode('utf-8')) / 1024.0))
