# 程序版本：v0.1 | 2026-11-22 | 一次性：修「唱歌按钮只能按一次」+「跟它说话改成按住说、松手发」
import io, shutil

P = r'F:\Daodao\src\_apk\assets\dao.html'
shutil.copyfile(P, r'F:\Daodao\_bak\dao.html.bak_20261122_holdtalk')
h = io.open(P, encoding='utf-8').read()

# ---------- 1) CSS：按住钮别被系统长按菜单/滑动吃掉 ----------
CSS_ANCHOR = '  #btnTalk.listening { background: linear-gradient(180deg, rgba(120,220,170,.55), rgba(60,170,130,.35)); border-'
idx = h.find(CSS_ANCHOR)
assert idx > 0
# 在 #btnTalk.listening 规则之前插一条
h = h[:idx] + '  #btnTalk { touch-action: none; -webkit-user-select: none; user-select: none; }\n' + h[idx:]

# ---------- 2) 音乐：stopMusic 拆成 stopAudio / closePanel，win 置空 ----------
OLD_STOP = '''  function stopMusic() {
    try { if (window.DaoNative && DaoNative.stopSong) DaoNative.stopSong(); } catch (e) {}
    try { if (srcNode) { srcNode.stop(); srcNode = null; } } catch (e) {}
    playing = -1;
    if (win) win.remove();
  }

  var win = null;
  function musicPanel() {
    if (win) { stopMusic(); return; }
'''
NEW_STOP = '''  var rows = [];
  function paintRows() {
    for (var _i = 0; _i < rows.length; _i++) {
      var r = rows[_i], on = (playing === _i);
      r.style.background = on ? 'rgba(118,158,255,.42)' : 'rgba(118,158,255,.16)';
      r.style.borderColor = on ? 'rgba(170,200,255,.75)' : 'rgba(118,158,255,.16)';
      r.textContent = SONGS[_i].t + (on ? '  ♪ 播放中' : '');
    }
  }
  // 2026-11-22 用户报「按了一次唱歌，就没办法按第二次」：
  // 原来 stopMusic 既停声音又 remove 面板，却没把 win 置空 → 面板关过一次以后，
  // musicPanel() 仍以为面板开着，只调 stopMusic 就 return，于是永远打不开第二次。
  // 拆成三件事，各管各的：停声音 / 关面板 / 重画画布状态。
  function stopAudio() {
    try { if (window.DaoNative && DaoNative.stopSong) DaoNative.stopSong(); } catch (e) {}
    try { if (srcNode) { srcNode.stop(); srcNode = null; } } catch (e) {}
    playing = -1;
    paintRows();
  }
  function closePanel() {
    if (win) { try { win.remove(); } catch (e) {} win = null; }
    rows = [];
  }
  function stopMusic() { stopAudio(); closePanel(); }

  var win = null;
  function musicPanel() {
    if (win) { stopMusic(); return; }
'''
assert OLD_STOP in h
h = h.replace(OLD_STOP, NEW_STOP, 1)

# 面板行：记进 rows、带边框、行上显示播放态
OLD_ROWS = '''    SONGS.forEach(function (s, i) {
      var r = el('div',
        'display:flex;align-items:center;min-height:52px;padding:0 12px;margin-top:8px;' +
        'border-radius:12px;background:rgba(118,158,255,.16);');
      r.textContent = s.t;
      r.addEventListener('click', function () { playSong(i); });
      win.appendChild(r);
    });
    document.body.appendChild(win);
'''
NEW_ROWS = '''    rows = [];
    SONGS.forEach(function (s, i) {
      var r = el('div',
        'display:flex;align-items:center;min-height:52px;padding:0 12px;margin-top:8px;' +
        'border-radius:12px;border:1px solid rgba(118,158,255,.16);background:rgba(118,158,255,.16);');
      r.textContent = s.t;
      r.addEventListener('click', function () { playSong(i); });
      win.appendChild(r);
      rows.push(r);
    });
    document.body.appendChild(win);
    paintRows();
'''
assert OLD_ROWS in h
h = h.replace(OLD_ROWS, NEW_ROWS, 1)

# playSong：别再把面板一起关掉
OLD_PLAY = '''    if (playing === i) { stopMusic(); return; }
    stopMusic();
'''
NEW_PLAY = '''    if (playing === i) { stopAudio(); return; }
    stopAudio();
'''
assert OLD_PLAY in h
h = h.replace(OLD_PLAY, NEW_PLAY, 1)

OLD_SET = '''    playing = i;
    tip('载入《' + s.t + '》…');'''
NEW_SET = '''    playing = i;
    paintRows();
    tip('载入《' + s.t + '》…');'''
assert OLD_SET in h
h = h.replace(OLD_SET, NEW_SET, 1)

# 失败分支也把高亮退回去
h = h.replace("playing = -1; return; }", "playing = -1; paintRows(); return; }", 1)
h = h.replace("playing = -1; } catch (e) { tip('放不了：'", "playing = -1; paintRows(); } catch (e) { tip('放不了：'", 1)

# ---------- 3) 「跟它说话」：按住说、松手发，按时长判断 ----------
OLD_TALK = '''  // 「跟它说话」：轻点＝直接开口说话（语音对话，再点一下结束并识别）
  var streamed = false;
  var talkBtn = document.getElementById('btnTalk');
  var listening = false;
'''
NEW_TALK = '''  // 「跟它说话」：2026-11-22 按用户要求改成「按住说，松手发」——对话按长按时长算。
  // 按下就开始录，松手结束并让原生识别；按不到 0.35 秒当误触，只提示不硬发；
  // 按住期间按钮上实时显示已按多少秒，看得见这一句说了多长。
  var streamed = false;
  var talkBtn = document.getElementById('btnTalk');
  var listening = false;
  var holdT0 = 0, holdTick = null;
'''
assert OLD_TALK in h
h = h.replace(OLD_TALK, NEW_TALK, 1)

OLD_LISTEN_TIP = "    tip('我在听…说完再点一下');"
NEW_LISTEN_TIP = "    tip('按住别松，说完松手');"
assert OLD_LISTEN_TIP in h
h = h.replace(OLD_LISTEN_TIP, NEW_LISTEN_TIP, 1)

OLD_UP = '''  // v0.88：打字功能按用户要求删除，长按不再有任何作用，「跟它说话」只剩轻点说话
  talkBtn.addEventListener('pointerup', function (e) {
    e.preventDefault();
    if (listening) stopListen(); else startListen();
  });
'''
NEW_UP = '''  function abortListen() {
    listening = false;
    try { talkBtn.classList.remove('listening'); } catch (e) {}
    try { if (window.DaoNative && DaoNative.stopListenCloud) DaoNative.stopListenCloud(); else if (window.DaoNative && DaoNative.stopListen) DaoNative.stopListen(); } catch (e) {}
  }
  function holdLabel(ms) {
    var s = (ms / 1000).toFixed(1);
    try { talkBtn.textContent = '🔴 说…' + s + 's（松手就发）'; } catch (e) {}
  }
  function startHold(e) {
    if (e && e.preventDefault) e.preventDefault();
    if (holdT0) return;                       // 已经在按着，别重复开录
    holdT0 = Date.now();
    if (!listening) startListen();
    holdLabel(0);
    if (holdTick) clearInterval(holdTick);
    holdTick = setInterval(function () { holdLabel(Date.now() - holdT0); }, 200);
  }
  function endHold(cancel) {
    if (!holdT0) return;                      // 没在按，忽略重复的 up/cancel
    var held = Date.now() - holdT0;
    holdT0 = 0;
    if (holdTick) { clearInterval(holdTick); holdTick = null; }
    try { talkBtn.textContent = '跟它说话'; } catch (e) {}
    if (cancel) { abortListen(); tip('松开了，这句不算'); return; }
    if (listening) stopListen();
    if (held < 350) tip('按太短了（' + (held / 1000).toFixed(1) + ' 秒），按住说满半秒再松手');
    else tip('这一句 ' + (held / 1000).toFixed(1) + ' 秒，发出去了');
  }
  talkBtn.addEventListener('pointerdown', function (e) { startHold(e); });
  talkBtn.addEventListener('pointerup', function (e) { e.preventDefault(); endHold(false); });
  talkBtn.addEventListener('pointercancel', function () { endHold(true); });
  // 手指滑出按钮再松：按钮上收不到 up，用 document 兜住
  document.addEventListener('pointerup', function (e) {
    if (!holdT0) return;
    if (e && e.target === talkBtn) return;    // 按钮自己的 up 处理过了
    endHold(false);
  });
'''
assert OLD_UP in h
h = h.replace(OLD_UP, NEW_UP, 1)

io.open(P, 'w', encoding='utf-8').write(h)
print('已改 dao.html：音乐面板状态机 + 按住说话')
