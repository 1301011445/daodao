# -*- coding: utf-8 -*-
"""v122 补丁：
1) 立绘缩小：scale 由 (sw*1.72, sh*1.04) 降到 (sw*1.45, sh*0.88)
2) 补回打字对话框：轻点「跟它说话」弹输入栏，长按仍是录音发送
"""
import io, os, sys

P = r'F:\Daodao\src\_apk\assets\dao.html'
s = open(P, encoding='utf-8').read()
n = 0


def rep(old, new):
    global s, n
    if old not in s:
        print('MISS:', old[:50])
        return
    s = s.replace(old, new, 1)
    n += 1


# 1) 缩小立绘
old_scale = 'scale = Math.min((sw * 1.72) / CW, (sh * 1.04) / CH);   // 2026-11-25 立绘再放大：原来人只占屏幕三分之一，上面空一大片'
rep(old_scale, 'scale = Math.min((sw * 1.45) / CW, (sh * 0.88) / CH);   // 2026-11-25 按要求缩小：原来放到 1.04 屏高，人顶到边、底部按钮被挤')

# 2) CSS
css = '''  /* 打字对话框：轻点「跟它说话」弹出；长按仍是录音发送 */
  #sayBar { position: fixed; left: 10px; right: 10px; bottom: 88px; display: none; align-items: center; gap: 8px; z-index: 40; }
  #sayBar.show { display: flex; }
  #sayTxt { flex: 1; height: 46px; border-radius: 23px; border: 1px solid rgba(255,255,255,.35);
            background: rgba(18,22,34,.94); color: #fff; font-size: 16px; padding: 0 16px; outline: none;
            -webkit-user-select: text; user-select: text; }
  #saySend { height: 46px; padding: 0 20px; border-radius: 23px; border: 0; background: #5b6cff; color: #fff; font-size: 16px; font-weight: 600; }
'''
rep('  #bubble.show { opacity: 1; transform: translate(-50%, 0); }',
    '  #bubble.show { opacity: 1; transform: translate(-50%, 0); }\n' + css)

# 3) HTML 输入栏
rep('    <button id="btnTalk">跟它说话</button>',
    '    <div id="sayBar"><input id="sayTxt" type="text" placeholder="想跟它说什么…" autocomplete="off" autocapitalize="off" spellcheck="false"><button id="saySend">发送</button></div>\n    <button id="btnTalk">跟它说话</button>')

# 4) JS 接线
js = '''  // 2026-11-25 补回打字对话框：轻点=打字，长按=说话
  var sayBar = document.getElementById('sayBar');
  var sayTxt = document.getElementById('sayTxt');
  function openSay() {
    if (!sayBar) return;
    sayBar.classList.add('show');
    setTimeout(function () { try { sayTxt.focus(); } catch (e) {} }, 80);
  }
  function closeSay() { try { sayBar.classList.remove('show'); sayTxt.blur(); } catch (e) {} }
  function sendSay() {
    var q = (sayTxt && sayTxt.value || '').trim();
    if (!q) { closeSay(); return; }
    sayTxt.value = '';
    closeSay();
    tip('你说：' + q);
    chatAsk(q);
  }
  if (sayBar) {
    try { document.getElementById('saySend').addEventListener('click', function (e) { e.preventDefault(); sendSay(); }); } catch (e) {}
    try { sayTxt.addEventListener('keydown', function (e) { if (e.key === 'Enter') { e.preventDefault(); sendSay(); } }); } catch (e) {}
  }

'''
rep('  // ---------- 对话 ----------', js + '  // ---------- 对话 ----------')

# 5) 轻点改为弹输入栏（原来只提示按太短）
rep("    if (held < 350) tip('按太短了（' + (held / 1000).toFixed(1) + ' 秒），按住说满半秒再松手');",
    "    if (held < 350) { openSay(); }   // 轻点=打字，长按才是说话")

open(P, 'w', encoding='utf-8').write(s)
print('PATCH_OK 改动数=', n, '文件字节=', len(s.encode('utf-8')))
