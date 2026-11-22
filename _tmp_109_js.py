# 程序版本：v0.1 | 2026-11-22 | 一次性：dao.html 歌单面板重写（进度/失败可见、面板可关、网页解码不再堵 UI）
import io

P = r'F:\Daodao\src\_apk\assets\dao.html'
s = io.open(P, encoding='utf-8').read()

i0 = s.index('  var rows = [];')
i1 = s.index('  // 长按右上角「电脑」设电脑 IP')
new = r'''  var rows = [], statusEl = null;
  var songSt = 'idle', songPosSec = 0, songLastPos = -1, stallCnt = 0, pollTimer = null, songTotal = 0;
  var outsideH = null;

  function setStatus(msg, isErr) {
    if (!statusEl) return;
    statusEl.textContent = msg || '';
    statusEl.style.color = isErr ? '#ff9c9c' : '#9fb6d9';
  }
  function rowText(i) {
    var s = SONGS[i];
    if (i !== playing) return s.t;
    if (songSt === 'load') return s.t + '  …载入中';
    if (songSt === 'play') return s.t + '  ♪ ' + songPosSec.toFixed(1) + ' / ' + songTotal + ' 秒';
    if (songSt === 'err') return s.t + '  ✕ 失败';
    return s.t;
  }
  function paintRows() {
    for (var _i = 0; _i < rows.length; _i++) {
      var r = rows[_i], on = (playing === _i);
      r.style.background = on ? (songSt === 'err' ? 'rgba(255,120,120,.24)' : 'rgba(118,158,255,.42)') : 'rgba(118,158,255,.16)';
      r.style.borderColor = on ? (songSt === 'err' ? 'rgba(255,150,150,.7)' : 'rgba(170,200,255,.75)') : 'rgba(118,158,255,.16)';
      r.textContent = rowText(_i);
    }
  }

  // 进度：直接问原生「真写进去多少采样」，不再凭「起了个线程」就当播放中。
  // 2.4 秒没往前走，标失败并附诊断；peak=0 说明解出来就是静音。
  function startPoll() {
    if (pollTimer) return;
    pollTimer = setInterval(function () {
      if (playing < 0) { stopPoll(); return; }
      var d = -1;
      try { d = (window.DaoNative && DaoNative.songPos) ? Number(DaoNative.songPos()) : -1; } catch (e) { d = -1; }
      if (songSt === 'play' && d >= 0) {
        if (d > songLastPos + 0.001) { stallCnt = 0; songPosSec = d; } else { stallCnt++; }
        songLastPos = d;
        if (stallCnt >= 6) {
          songSt = 'err';
          var dg = '';
          try { dg = (window.DaoNative && DaoNative.songDiag) ? String(DaoNative.songDiag()) : ''; } catch (e2) { }
          setStatus('播放没在走：' + dg + '（查音量/耳机，或这台的音频流 $正常）', true);
        }
        paintRows();
      }
    }, 400);
  }
  function stopPoll() { if (pollTimer) { clearInterval(pollTimer); pollTimer = null; } }

  // 2026-11-22 用户报「按了一次唱歌，就没办法按第二次」：原来 stopMusic 停声音又 remove 面板却不置空 win。
  // 拆成三件事各管各的：停声音 / 关面板 / 重画。
  function stopAudio() {
    try { if (window.DaoNative && DaoNative.stopSong) DaoNative.stopSong(); } catch (e) {}
    try { if (srcNode) { srcNode.stop(); srcNode = null; } } catch (e) {}
    playing = -1; songSt = 'idle'; songPosSec = 0; songLastPos = -1; stallCnt = 0;
    stopPoll(); paintRows();
  }
  function closePanel() {
    if (win) { try { win.remove(); } catch (e) {} win = null; }
    rows = []; statusEl = null;
    if (outsideH) { try { document.removeEventListener('pointerdown', outsideH, true); } catch (e) {} outsideH = null; }
  }
  function stopMusic() { stopAudio(); closePanel(); }

  var win = null;
  function musicPanel() {
    if (win) { stopMusic(); return; }
    win = el('div',
      'position:fixed;left:12px;right:12px;bottom:96px;z-index:10002;padding:12px 12px 10px;border-radius:16px;' +
      'background:rgba(14,20,40,.97);color:#e8eeff;font-family:system-ui,sans-serif;font-size:16px;' +
      'box-shadow:0 8px 30px rgba(0,0,0,.5);touch-action:manipulation;-webkit-user-select:none;user-select:none;');
    var hd = el('div', 'display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;');
    hd.appendChild(el('div', 'font-size:15px;opacity:.8;', '道自己的歌（手机本地放）'));
    var box = el('div', 'display:flex;align-items:center;');
    var sp = el('div', 'padding:5px 12px;margin-right:6px;font-size:13px;border-radius:9px;background:rgba(118,158,255,.22);', '停止');
    sp.addEventListener('click', function (ev) {
      if (ev && ev.stopPropagation) ev.stopPropagation();
      stopAudio(); setStatus('停了；再点一行就重新放');
    });
    var x = el('div', 'padding:4px 10px;font-size:22px;line-height:1;', '×');
    x.addEventListener('click', function (ev) {
      if (ev && ev.stopPropagation) ev.stopPropagation();
      stopMusic();
    });
    box.appendChild(sp); box.appendChild(x); hd.appendChild(box);
    win.appendChild(hd);
    statusEl = el('div', 'font-size:12px;line-height:1.45;color:#9fb6d9;min-height:17px;margin:2px 2px 2px;word-break:break-all;', '');
    win.appendChild(statusEl);
    rows = [];
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
    setStatus('点一首就放；再点这一行就停');
    // 点面板外面也能收起来（原来只能去点右上角小 ×，手指容易点空）
    outsideH = function (ev) {
      if (win && ev && ev.target && !win.contains(ev.target)) stopMusic();
    };
    setTimeout(function () { try { document.addEventListener('pointerdown', outsideH, true); } catch (e) {} }, 0);
  }

  var songPending = -1;

  function playSong(i) {
    var s = SONGS[i];
    if (playing === i && songSt !== 'err') { stopAudio(); setStatus('停了'); return; }
    if (!s) return;
    stopAudio();
    try { if (window.DaoNative && DaoNative.stopAll) DaoNative.stopAll(); } catch (e) {}
    try { if (window.speechSynthesis) window.speechSynthesis.cancel(); } catch (e) {}
    songPending = i; playing = i; songSt = 'load'; songPosSec = 0; songLastPos = -1; stallCnt = 0;
    paintRows(); setStatus('载入《' + s.t + '》…（包内 6MB，解码要一两秒）');
    startPoll();
    if (window.DaoNative && DaoNative.playSongAsset) {
      try {
        var nr = String(DaoNative.playSongAsset(s.k || '') || '');
        if (nr.indexOf('START') === 0) return;      // 等 __daoSong 回话（OK 或 ERR）
        if (nr.indexOf('OK') === 0) { songSt = 'play'; paintRows(); return; }
        failSong(i, nr.replace(/^ERR\|?/, ''));
        return;
      } catch (e2) {
        failSong(i, '桥接异常 ' + (e2 && e2.message ? e2.message : ''));
        return;
      }
    }
    failSong(i, '这一版没有原生播放接口');
  }

  function failSong(i, msg) {
    playing = i; songSt = 'err'; stopPoll(); paintRows();
    setStatus('放不了：' + (msg || '未知原因'), true);
    // 原生放不了才走网页解码；走之前先把原因摆出来，别再让人对着「播放中」干等
    webPlay(i, msg || '');
  }

  window.__daoSong = function (evt) {
    evt = String(evt || '');
    var i = songPending, s = (i >= 0 && SONGS[i]) ? SONGS[i] : null;
    var parts = evt.split('|');
    var nm = parts[parts.length - 1];
    if (evt.indexOf('ERR') === 0) {
      var m = evt.replace(/^ERR\|?/, '').slice(0, 110);
      if (typeof nm !== 'string') nm = '';
      failSong(i >= 0 ? i : playing, m);
      return;
    }
    if (evt.indexOf('OK|') === 0) {
      var sec = parseFloat(parts[1]) || 0;
      songTotal = Math.round(sec);
      songSt = 'play'; songPosSec = 0; songLastPos = -1; stallCnt = 0;
      startPoll(); paintRows();
      setStatus('正在放《' + (s ? s.t : '这首') + '》共 ' + songTotal + ' 秒；点这一行停');
      return;
    }
    if ((evt.indexOf('DONE') === 0 || evt.indexOf('STOP') === 0) && s && nm && nm !== s.k) return;
    if (evt.indexOf('DONE') === 0 || evt.indexOf('STOP') === 0) {
      playing = -1; songSt = 'idle'; stopPoll(); paintRows();
      setStatus(evt.indexOf('DONE') === 0 ? '放完了' : '停了');
    }
  };

  // 网页解码：XHR 异步取包内 adp（不再走 8MB base64 同步过桥），按帧分批解，每批让一次 UI
  function webPlay(i, natErr) {
    var s = SONGS[i];
    if (!s) { playing = -1; paintRows(); return; }
    setStatus('原生失败（' + (natErr || '未知') + '），改用网页解码…');
    try {
      var xhr = new XMLHttpRequest();
      xhr.open('GET', s.f, true);
      xhr.responseType = 'arraybuffer';
      xhr.onload = function () {
        if (!xhr.response || xhr.response.byteLength < 16) { failSongPlain(i, '网页读不到 ' + s.f); return; }
        decodeAsync(i, xhr.response);
      };
      xhr.onerror = function () { failSongPlain(i, '网页读不到 ' + s.f); };
      xhr.send();
    } catch (e) {
      failSongPlain(i, '网页取包失败 ' + (e && e.message ? e.message : ''));
    }
  }
  function failSongPlain(i, msg) {
    playing = i; songSt = 'err'; paintRows();
    setStatus('放不了：' + msg, true);
  }

  function decodeAsync(i, ab) {
    var s = SONGS[i], dv = new DataView(ab);
    var m = String.fromCharCode(dv.getUint8(0), dv.getUint8(1), dv.getUint8(2), dv.getUint8(3));
    if (m !== 'DAO1') { failSongPlain(i, '网页解码：包头不是 DAO1'); return; }
    var sr = dv.getUint32(4, true), nf = dv.getUint32(8, true);
    if (!sr || !nf) { failSongPlain(i, '网页解码：头里 sr/帧数 是 0'); return; }
    var total = nf * 2048;
    try { if (!actx) actx = new (window.AudioContext || window.webkitAudioContext)(); } catch (e) { failSongPlain(i, '这台设备网页音频起不来'); return; }
    if (actx.state === 'suspended' && actx.resume) { try { actx.resume(); } catch (e) {} }
    var f32 = new Float32Array(total), o = 0, pos = 12, f = 0, peak = 0;
    songTotal = Math.round(total / sr);
    setStatus('网页解码中…共 ' + songTotal + ' 秒');
    function step() {
      var stopAt = f + 240;
      for (; f < nf && f < stopAt; f++) {
        var pred = dv.getInt16(pos, true), idx = dv.getUint8(pos + 2);
        var end = Math.min(pos + 1028, dv.byteLength);
        for (var b = pos + 4; b < end; b++) {
          var by = dv.getUint8(b);
          for (var k = 0; k < 2; k++) {
            var code = k === 0 ? (by >> 4) & 15 : by & 15;
            var st = STEPS[idx];
            var delta = st >> 3;
            if (code & 4) delta += st;
            if (code & 2) delta += st >> 1;
            if (code & 1) delta += st >> 2;
            pred += (code & 8) ? -delta : delta;
            if (pred > 32767) pred = 32767; else if (pred < -32768) pred = -32768;
            idx += IDXT[code & 7];
            if (idx < 0) idx = 0; else if (idx > 88) idx = 88;
            if (o < total) { f32[o++] = pred; var a = pred < 0 ? -pred : pred; if (a > peak) peak = a; }
          }
        }
        pos += 1028;
      }
      if (f < nf) { setTimeout(step, 0); return; }
      if (peak === 0) { failSongPlain(i, '网页解码出来全是静音（包内数据是空的）'); return; }
      try {
        var buf = actx.createBuffer(1, Math.max(1, o), sr), ch = buf.getChannelData(0);
        for (var q = 0; q < o; q++) ch[q] = f32[q] / 32768.0;
        srcNode = actx.createBufferSource();
        srcNode.buffer = buf; srcNode.connect(actx.destination);
        srcNode.onended = function () { if (playing === i) { playing = -1; songSt = 'idle'; paintRows(); setStatus('放完了'); } };
        srcNode.start(0);
        playing = i; songSt = 'play'; songPosSec = 0; paintRows();
        setStatus('正在放《' + s.t + '》（网页解码，' + songTotal + ' 秒）');
      } catch (e) { failSongPlain(i, '网页播放失败 ' + (e && e.message ? e.message : '')); }
    }
    step();
  }

'''
s = s[:i0] + new + s[i1:]

# tip 提到面板之上，否则失败原因被面板盖住
s = s.replace("'position:fixed;left:50%;transform:translateX(-50%);bottom:84px;z-index:10000;' +",
              "'position:fixed;left:50%;transform:translateX(-50%);bottom:140px;z-index:10060;' +", 1)

io.open(P, 'w', encoding='utf-8').write(s)
print('dao.html OK, 行数', s.count('\n') + 1)
