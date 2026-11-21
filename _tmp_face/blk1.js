
/* 道 · 手机端语音工具栏（2026-11-20 补）
   为什么单独加一条：原页面只有打字，没有说话也没有听。这里不碰原有布局，只加一条浮动栏。
   能力来源：DaoNative.speak / listen（原生 TTS + 系统语音识别），电脑端 /say、/do、/music。 */
(function () {
  if (window.__daoBar) return;
  window.__daoBar = 1;

  var lastText = '';
  var pcIp = localStorage.getItem('dao_pc_ip') || '192.168.2.115';

  function el(tag, css, txt) {
    var d = document.createElement(tag);
    if (css) d.setAttribute('style', css);
    if (txt) d.textContent = txt;
    return d;
  }


  function tip(msg) {
    var t = el('div',
      'position:fixed;left:50%;transform:translateX(-50%);bottom:84px;z-index:10000;' +
      'max-width:80vw;padding:9px 14px;border-radius:12px;background:rgba(0,0,0,.78);color:#fff;' +
      'font-size:15px;line-height:1.45;font-family:system-ui,sans-serif;');
    t.textContent = msg;
    document.body.appendChild(t);
    setTimeout(function () { try { t.remove(); } catch (e) {} }, 2600);
  }

  // ---------- 跨网记忆同步（不挑 WiFi，走公网） ----------
  window.__daoSync = function (msg) {
    if (!msg) return;
    if (msg.indexOf('失败') >= 0) return;              // 网络不好就不吵人，下次自己再对
    if (msg.indexOf('最新') >= 0 && msg.indexOf('还没发过') < 0) return;
    tip(msg);
  };
  setTimeout(function () { try { if (window.DaoNative && DaoNative.syncNow) DaoNative.syncNow(); } catch (e) {} }, 1500);
setTimeout(function () { try { if (window.DaoNative && DaoNative.warmUp) DaoNative.warmUp(); } catch (e) {} }, 800);

  // ---------- 说话：先用电脑的声音，连不上再退回手机自带 TTS ----------
  // 电脑端 /tts 返回的是 Edge 合成的 mp3，音色比手机自带 TTS 自然；
  // 拿不到（没连 WiFi、电脑没开）就立退回原生，不让用户干等
  // 手机自己直连 Edge 朗读（不要密钥、不要额度）；连不上才退回电脑、再退回系统 TTS
  var voiceMode = localStorage.getItem('dao_voice_mode') || 'edge';
  var EDGE_IDX = { edge: 0, edge1: 1, edge2: 3 };
  function nativeSpeak(text) {
    if (window.DaoNative && DaoNative.speak) { try { DaoNative.speak(text); return; } catch (e) {} }
    if (window.speechSynthesis) {
      try {
        var u = new SpeechSynthesisUtterance(text);
        u.lang = 'zh-CN'; u.rate = 0.95;
        speechSynthesis.speak(u);
      } catch (e) {}
    }
  }
  function speak(text) {
    if (!text) return;
    lastText = text;
    // 说话前先把本地曲库停掉，避免对话里混进歌声
    try { if (window.daoStopMusic) window.daoStopMusic(); } catch (e) {}
    try { if (window.DaoNative && DaoNative.stopAll) DaoNative.stopAll(); } catch (e) {}
    if (EDGE_IDX[voiceMode] !== undefined) {
      if (window.DaoNative && DaoNative.speakEdge) { try { DaoNative.speakEdge(text, EDGE_IDX[voiceMode]); return; } catch (e) {} }
      nativeSpeak(text); return;
    }
    if (voiceMode === 'tencent') {
      if (window.DaoNative && DaoNative.speakTencent) {
        try { DaoNative.speakTencent(text, 0); return; } catch (e) {}
      }
      nativeSpeak(text); return;
    }
    if (voiceMode === 'cloud') {
      if (window.DaoNative && DaoNative.speakCloud) { try { DaoNative.speakCloud(text, 'female'); return; } catch (e) {} }
      nativeSpeak(text); return;
    }
    if (voiceMode !== 'pc') { nativeSpeak(text); return; }
    var done = false;
    var timer = setTimeout(function () { if (!done) { done = true; nativeSpeak(text); } }, 9000);
    try {
      var x = new XMLHttpRequest();
      x.open('POST', 'http://' + pcIp + ':8848/tts', true);
      x.responseType = 'blob';
      x.timeout = 12000;
      x.onload = function () {
        if (done) return;
        if (x.status === 200 && x.response && x.response.size > 2048) {
          done = true; clearTimeout(timer);
          try {
            var url = URL.createObjectURL(x.response);
            var a = new Audio(url);
            a.onended = function () { try { URL.revokeObjectURL(url); } catch (e) {} };
            a.play().catch(function () { nativeSpeak(text); });
            return;
          } catch (e) {}
        }
        done = true; clearTimeout(timer); nativeSpeak(text);
      };
      x.onerror = function () { if (!done) { done = true; clearTimeout(timer); nativeSpeak(text); } };
      x.ontimeout = function () { if (!done) { done = true; clearTimeout(timer); nativeSpeak(text); } };
      x.send(text);
    } catch (e) { if (!done) { done = true; clearTimeout(timer); nativeSpeak(text); } }
  }

  // ---------- 听（原生识别） ----------
  window.__daoVoice = function (id, text) {
    if (!text) return;
    if (/没听清|权限|没有语音识别|启动失败/.test(text)) { tip(text); return; }
    tip('你说：' + text);
    chatAsk(text);
  };

  // 「跟它说话」：点一下开输入框；按住 0.45 秒改成语音输入（松手识别）
  // 「跟它说话」：轻点＝直接开口说话（语音对话，再点一下结束并识别）
  //               长按 0.55 秒＝改用打字（键盘输入），不会再一点就弹键盘
  var streamed = false;
  var talkBtn = document.getElementById('btnTalk');
  var holdTmr = null, longFired = false, listening = false;

  function startListen() {
    if (!(window.DaoNative && (DaoNative.listenCloud || DaoNative.listen))) {
      tip('这台设备没有语音通道，长按可以打字');
      return;
    }
    listening = true;
    try { if (window.DaoNative && DaoNative.stopAll) DaoNative.stopAll(); } catch (e) {}
    talkBtn.classList.add('listening');
    try { if (DaoNative.listenCloud) DaoNative.listenCloud('mic'); else DaoNative.listen('mic'); } catch (e) {}
    tip('我在听…说完再点一下');
  }
  function stopListen() {
    listening = false;
    talkBtn.classList.remove('listening');
    try { if (DaoNative.stopListenCloud) DaoNative.stopListenCloud(); else if (DaoNative.stopListen) DaoNative.stopListen(); } catch (e) {}
    tip('好，我听听…');
  }
  talkBtn.addEventListener('pointerdown', function (e) {
    e.preventDefault();
    longFired = false;
    holdTmr = setTimeout(function () {
      holdTmr = null;
      longFired = true;
      if (listening) stopListen();
      askMode = 'chat';
      try { askInput.placeholder = '跟道说句话……'; } catch (err) {}
      openAsk();
    }, 550);
  });
  talkBtn.addEventListener('pointerup', function (e) {
    e.preventDefault();
    if (holdTmr) { clearTimeout(holdTmr); holdTmr = null; }
    if (longFired) return;             // 长按已经去打字的流程
    if (listening) stopListen(); else startListen();
  });
  talkBtn.addEventListener('pointercancel', function () {
    if (holdTmr) { clearTimeout(holdTmr); holdTmr = null; }
  });

  // ---------- 对话 ----------
  function chatAsk(q) {
    q = (q || '').trim();
    if (!q) return;
    // 「忘掉 xxx」「删掉 xxx」：走分布式删除，不是只在本地删
    var mm = q.match(/^(忘掉|删掉|忘记)(?:这件事)?[：: ]*(.+)$/);
    if (mm && mm[2]) {
      if (window.DaoNative && DaoNative.forget) { DaoNative.forget(mm[2].trim()); tip('好，这条从两端都删掉'); }
      else tip('这台设备删不了记忆');
      return;
    }
    if (window.DaoNative && (DaoNative.chatStream || DaoNative.chat)) {
      streamed = true;                       // 原生会边出字边说，页面别再重复念一遍
      tip('我在听你说…');
      if (DaoNative.chatStream) { try { DaoNative.chatStream(q, 'bar'); return; } catch (e) {} }
      DaoNative.chat(q, 'bar');
      return;
    }
    tip('这台设备连不上对话通道');
  }

  // 桥回来的回答：读出来 + 贴一句字幕（不改原页面自己的处理）
  var oldReply = window.__daoReply;
  window.__daoReply = function (id, reply, mood) {
    try { if (typeof oldReply === 'function') oldReply.apply(null, arguments); } catch (e) {}
    if (id === 'bar' && reply) {
      tip(reply);
      if (streamed) { streamed = false; return; }   // 流式路径：音频已由原生按句放完
      speak(reply);
    }
  };


  // ---------- 唱歌：让电脑端开口 ----------
  function hit(path, body) {
    return fetch('http://' + pcIp + ':8848' + path, {
      method: body === undefined ? 'GET' : 'POST',
      body: body
    }).then(function (r) { return r.text(); }).catch(function () { return 'ERR'; });
  }

  // ---------- 本地曲库：手机自己出声，不靠电脑 ----------
  // 曲子是 IMA ADPCM 压的（tools\音乐\手机曲库\adpcm.py），体积约原 wav 的 1/4，
  // WebView 的 file:// 不给 XHR 读 assets，所以走 DaoNative.assetB64 取字节再自己解
  var SONGS = [
    { k: 'guitu',    f: 'music/guitu.adp',    t: '归途的月光' },
    { k: 'gongzuo',  f: 'music/gongzuo.adp',  t: '把好日子扛在肩上' },
    { k: 'shaonian', f: 'music/shaonian.adp', t: '少年模样' }
  ];
  var STEPS = [7,8,9,10,11,12,13,14,16,17,19,21,23,25,28,31,34,37,41,45,50,55,60,66,
    73,80,88,97,107,118,130,143,157,173,190,209,230,253,279,307,337,371,408,449,
    494,544,598,658,724,796,876,963,1060,1166,1282,1411,1552,1707,1878,2066,2272,
    2499,2749,3024,3327,3660,4026,4428,4871,5358,5894,6484,7132,7845,8630,9493,
    10442,11487,12635,13899,15289,16818,18500,20350,22385,24623,27086,29794,32767];
  var IDXT = [-1,-1,-1,-1,2,4,6,8,-1,-1,-1,-1,2,4,6,8];
  var actx = null, srcNode = null, playing = -1, playingBuf = null, songBufCache = {};

  function b64ToBuf(b64) {
    var bin = atob(b64), n = bin.length, u8 = new Uint8Array(n);
    for (var i = 0; i < n; i++) u8[i] = bin.charCodeAt(i);
    return u8.buffer;
  }

  function decodeAdp(ab) {
    var dv = new DataView(ab);
    var m = String.fromCharCode(dv.getUint8(0), dv.getUint8(1), dv.getUint8(2), dv.getUint8(3));
    if (m !== 'DAO1') throw new Error('不是曲库文件');
    var sr = dv.getUint32(4, true), nf = dv.getUint32(8, true);
    var pcm = new Float32Array(nf * 2048), o = 0, pos = 12;
    for (var f = 0; f < nf; f++) {
      var pred = dv.getInt16(pos, true), idx = dv.getUint8(pos + 2);
      var end = Math.min(pos + 1028, dv.byteLength);
      for (var b = pos + 4; b < end; b++) {
        var by = dv.getUint8(b);
        for (var k = 0; k < 2; k++) {
          var code = k === 0 ? (by >> 4) & 15 : by & 15;
          var step = STEPS[idx];
          var delta = step >> 3;
          if (code & 4) delta += step;
          if (code & 2) delta += step >> 1;
          if (code & 1) delta += step >> 2;
          pred += (code & 8) ? -delta : delta;
          if (pred > 32767) pred = 32767; else if (pred < -32768) pred = -32768;
          idx += IDXT[code & 7];
          if (idx < 0) idx = 0; else if (idx > 88) idx = 88;
          pcm[o++] = pred / 32768.0;
        }
      }
      pos += 1028;
    }
    return { sr: sr, pcm: pcm.subarray(0, o) };
  }

  function stopMusic() {
    try { if (window.DaoNative && DaoNative.stopSong) DaoNative.stopSong(); } catch (e) {}
    try { if (srcNode) { srcNode.stop(); srcNode = null; } } catch (e) {}
    playing = -1;
    if (win) win.remove();
  }

  var win = null;
  function musicPanel() {
    if (win) { stopMusic(); return; }
    win = el('div',
      'position:fixed;left:12px;right:12px;bottom:74px;z-index:10001;padding:12px;border-radius:16px;' +
      'background:rgba(14,20,40,.96);color:#e8eeff;font-family:system-ui,sans-serif;font-size:16px;' +
      'box-shadow:0 8px 30px rgba(0,0,0,.45);');
    var hd = el('div', 'display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;');
    hd.appendChild(el('div', 'font-size:15px;opacity:.8;', '道自己的歌（手机本地放）'));
    var x = el('div', 'padding:4px 10px;font-size:20px;line-height:1;', '×');
    x.addEventListener('click', stopMusic);
    hd.appendChild(x);
    win.appendChild(hd);
    SONGS.forEach(function (s, i) {
      var r = el('div',
        'display:flex;align-items:center;min-height:52px;padding:0 12px;margin-top:8px;' +
        'border-radius:12px;background:rgba(118,158,255,.16);');
      r.textContent = s.t;
      r.addEventListener('click', function () { playSong(i); });
      win.appendChild(r);
    });
    document.body.appendChild(win);
  }

  function playSong(i) {
    var s = SONGS[i];
    if (playing === i) { stopMusic(); return; }
    stopMusic();
    // 唱歌前先把朗读停掉，两路声音不能一起响
    try { if (window.DaoNative && DaoNative.stopAll) DaoNative.stopAll(); } catch (e) {}
    try { if (window.speechSynthesis) window.speechSynthesis.cancel(); } catch (e) {}
    playing = i;
    tip('载入《' + s.t + '》…');
    // 先交给原生：读 assets、解 ADPCM、写 wav、MediaPlayer 放（真机上就是这条路）
    if (window.DaoNative && DaoNative.playSongAsset) {
      try {
        var nr = String(DaoNative.playSongAsset(s.k || ''));
        if (nr.indexOf('OK') === 0) { tip('正在放《' + s.t + '》，再点一下停'); return; }
        tip(nr.replace(/^ERR\|/, ''));   // 原生不行就继续走下面的网页解码
      } catch (e2) {}
    }
    try {
      if (!actx) actx = new (window.AudioContext || window.webkitAudioContext)();
      // 解一次缓存一次：同一首再点不用重新解码（4M 采样现解要一两秒）
      var buf = songBufCache[s.f];
      if (!buf) {
        var b64 = (window.DaoNative && DaoNative.assetB64) ? DaoNative.assetB64(s.f) : '';
        if (!b64) { tip('拿不到曲库文件'); return; }
        var d = decodeAdp(b64ToBuf(b64));
        buf = actx.createBuffer(1, d.pcm.length, d.sr);
        buf.getChannelData(0).set(d.pcm);
        songBufCache = {}; songBufCache[s.f] = buf;   // 只留最近一首，别把内存吃满
      }
      playingBuf = buf;
      srcNode = actx.createBufferSource();
      srcNode.buffer = buf;
      srcNode.connect(actx.destination);
      srcNode.onended = function () { if (playing === i) { playing = -1; } };
      srcNode.start(0);
      tip('正在放《' + s.t + '》，再点一下暂停');
    } catch (e) { tip('放不了：' + e.message); playing = -1; }
  }


  // 长按右上角「电脑」设电脑 IP（换 WiFi 时用）
  var tmr = null;
  var pcBtnEl = document.getElementById('pcBtn');
  pcBtnEl.addEventListener('pointerdown', function () {
    tmr = setTimeout(function () {
      var ip = window.prompt('电脑端 IP（同一 WiFi）', pcIp);
      if (ip) { pcIp = ip.trim(); localStorage.setItem('dao_pc_ip', pcIp); tip('已记下 ' + pcIp); }
    }, 1200);
  });
  ['pointerup', 'pointercancel', 'pointerleave'].forEach(function (k) {
    pcBtnEl.addEventListener(k, function () { if (tmr) { clearTimeout(tmr); tmr = null; } });
  });
  window.daoStopMusic = stopMusic;
  window.daoMusicPanel = musicPanel;
  window.daoPlaySong = playSong;
  window.daoPlayNext = function () { playSong((playing + 1) % (SONGS.length || 1)); };
})();
