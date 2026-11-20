
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

  // ---------- 浮动栏 ----------
  var bar = el('div',
    'position:fixed;left:0;right:0;bottom:0;z-index:9999;display:flex;gap:8px;' +
    'padding:10px 12px calc(10px + env(safe-area-inset-bottom));' +
    'background:linear-gradient(180deg,rgba(11,16,34,0),rgba(11,16,34,.92) 38%);' +
    'font-family:system-ui,-apple-system,"PingFang SC",sans-serif;user-select:none;');

  function btn(label, bg) {
    var b = el('div',
      'flex:1;min-height:48px;min-width:64px;display:flex;align-items:center;justify-content:center;' +
      'border-radius:14px;font-size:16px;color:#fff;background:' + bg + ';' +
      '-webkit-tap-highlight-color:transparent;touch-action:none;');
    b.textContent = label;
    return b;
  }

  var bTalk = btn('按住说话', 'linear-gradient(180deg,#3f7cff,#2a54c8)');
  var bSay = btn('朗读', 'linear-gradient(180deg,#5b6b8c,#39445c)');
  var bChat = btn('对话', 'linear-gradient(180deg,#24b47e,#178260)');
  var bSing = btn('唱一句', 'linear-gradient(180deg,#c2578f,#8d3568)');
  var bMusic = btn('听歌', 'linear-gradient(180deg,#8a6ad4,#5c43a0)');
  bar.appendChild(bTalk); bar.appendChild(bSay); bar.appendChild(bChat); bar.appendChild(bSing);
  bar.appendChild(bMusic);
  document.body.appendChild(bar);

  function tip(msg) {
    var t = el('div',
      'position:fixed;left:50%;transform:translateX(-50%);bottom:84px;z-index:10000;' +
      'max-width:80vw;padding:9px 14px;border-radius:12px;background:rgba(0,0,0,.78);color:#fff;' +
      'font-size:15px;line-height:1.45;font-family:system-ui,sans-serif;');
    t.textContent = msg;
    document.body.appendChild(t);
    setTimeout(function () { try { t.remove(); } catch (e) {} }, 2600);
  }

  // ---------- 说话：先用电脑的声音，连不上再退回手机自带 TTS ----------
  // 电脑端 /tts 返回的是 Edge 合成的 mp3，音色比手机自带 TTS 自然；
  // 拿不到（没连 WiFi、电脑没开）就立退回原生，不让用户干等
  var voiceMode = localStorage.getItem('dao_voice_mode') || 'pc';
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

  var holding = false;
  bTalk.addEventListener('pointerdown', function (e) {
    e.preventDefault();
    holding = true;
    bTalk.style.filter = 'brightness(1.25)';
    // 有网就用云端识别（GLM-ASR，比厂商识别器准）；云端不可用才退回系统识别
    if (window.DaoNative && DaoNative.listenCloud) { DaoNative.listenCloud('mic'); tip('我在听…松手结束'); }
    else if (window.DaoNative && DaoNative.listen) { DaoNative.listen('mic'); tip('我在听…松手结束'); }
    else tip('这台设备没有语音通道，先打字吧');
  });
  function endTalk(e) {
    if (!holding) return;
    holding = false;
    bTalk.style.filter = '';
    if (window.DaoNative && DaoNative.stopListenCloud) DaoNative.stopListenCloud();
    else if (window.DaoNative && DaoNative.stopListen) DaoNative.stopListen();
  }
  bTalk.addEventListener('pointerup', endTalk);
  bTalk.addEventListener('pointercancel', endTalk);
  bTalk.addEventListener('pointerleave', endTalk);

  // ---------- 对话 ----------
  function chatAsk(q) {
    q = (q || '').trim();
    if (!q) return;
    if (window.DaoNative && DaoNative.chat) {
      tip('道在想…');
      DaoNative.chat(q, 'bar');
      return;
    }
    tip('这台设备连不上对话通道');
  }
  bChat.addEventListener('click', function () {
    var q = window.prompt('跟道说点什么');
    if (q) chatAsk(q);
  });

  // 桥回来的回答：读出来 + 贴一句字幕（不改原页面自己的处理）
  var oldReply = window.__daoReply;
  window.__daoReply = function (id, reply, mood) {
    try { if (typeof oldReply === 'function') oldReply.apply(null, arguments); } catch (e) {}
    if (id === 'bar' && reply) { tip(reply); speak(reply); }
  };

  // 点一下读；长按 1.2 秒在「电脑的声音 / 手机自带朗读」之间切换
  var sayTmr = null;
  bSay.addEventListener('pointerdown', function () {
    sayTmr = setTimeout(function () {
      var order = ['pc', 'tencent', 'cloud', 'native'];
      var idx = order.indexOf(voiceMode);
      voiceMode = order[(idx < 0 ? 0 : idx + 1) % order.length];
      localStorage.setItem('dao_voice_mode', voiceMode);
      var names = { pc: '电脑的声音', tencent: '腾讯云语音', cloud: '云端语音（GLM-TTS）', native: '手机自带的朗读' };
      if (voiceMode === 'tencent' && window.DaoNative && DaoNative.hasTencentKeys && DaoNative.hasTencentKeys() !== '1') {
        tip('腾讯语音还没填密钥：长按「听歌」录入');
      } else {
        tip('改用' + (names[voiceMode] || voiceMode));
      }
    }, 1200);
  });
  ['pointerup', 'pointercancel', 'pointerleave'].forEach(function (k) {
    bSay.addEventListener(k, function () { if (sayTmr) { clearTimeout(sayTmr); sayTmr = null; } });
  });
  bSay.addEventListener('click', function () {
    if (!lastText) { tip('还没内容可读'); return; }
    speak(lastText);
  });

  // ---------- 唱歌：让电脑端开口 ----------
  function hit(path, body) {
    return fetch('http://' + pcIp + ':8848' + path, {
      method: body === undefined ? 'GET' : 'POST',
      body: body
    }).then(function (r) { return r.text(); }).catch(function () { return 'ERR'; });
  }
  var singTmr = null;
  bSing.addEventListener('pointerdown', function () {
    singTmr = setTimeout(function () {
      var f = window.prompt('要道记住什么？（下次对话它会记着）');
      if (f && window.DaoNative && DaoNative.remember) {
        var r = '记住';
        try { r = DaoNative.remember(f) || '记住'; } catch (e) {}
        tip(r);
      }
    }, 1200);
  });
  ['pointerup', 'pointercancel', 'pointerleave'].forEach(function (k) {
    bSing.addEventListener(k, function () { if (singTmr) { clearTimeout(singTmr); singTmr = null; } });
  });
  bSing.addEventListener('click', function () {
    tip('让道唱一句…');
    hit('/do', '唱一句').then(function (r) { if (r === 'ERR') tip('连不上电脑端'); });
  });

  // ---------- 本地曲库：手机自己出声，不靠电脑 ----------
  // 曲子是 IMA ADPCM 压的（tools\音乐\手机曲库\adpcm.py），体积约原 wav 的 1/4，
  // WebView 的 file:// 不给 XHR 读 assets，所以走 DaoNative.assetB64 取字节再自己解
  var SONGS = [
    { f: 'music/guitu.adp',    t: '归途的月光' },
    { f: 'music/gongzuo.adp',  t: '把好日子扛在肩上' },
    { f: 'music/shaonian.adp', t: '少年模样' }
  ];
  var STEPS = [7,8,9,10,11,12,13,14,16,17,19,21,23,25,28,31,34,37,41,45,50,55,60,66,
    73,80,88,97,107,118,130,143,157,173,190,209,230,253,279,307,337,371,408,449,
    494,544,598,658,724,796,876,963,1060,1166,1282,1411,1552,1707,1878,2066,2272,
    2499,2749,3024,3327,3660,4026,4428,4871,5358,5894,6484,7132,7845,8630,9493,
    10442,11487,12635,13899,15289,16818,18500,20350,22385,24623,27086,29794,32767];
  var IDXT = [-1,-1,-1,-1,2,4,6,8,-1,-1,-1,-1,2,4,6,8];
  var actx = null, srcNode = null, playing = -1, playingBuf = null;

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
    playing = i;
    tip('载入《' + s.t + '》…');
    try {
      var b64 = (window.DaoNative && DaoNative.assetB64) ? DaoNative.assetB64(s.f) : '';
      if (!b64) { tip('拿不到曲库文件'); return; }
      var d = decodeAdp(b64ToBuf(b64));
      if (!actx) actx = new (window.AudioContext || window.webkitAudioContext)();
      var buf = actx.createBuffer(1, d.pcm.length, d.sr);
      buf.getChannelData(0).set(d.pcm);
      playingBuf = buf;
      srcNode = actx.createBufferSource();
      srcNode.buffer = buf;
      srcNode.connect(actx.destination);
      srcNode.onended = function () { if (playing === i) { playing = -1; } };
      srcNode.start(0);
      tip('正在放《' + s.t + '》，再点一下暂停');
    } catch (e) { tip('放不了：' + e.message); playing = -1; }
  }

  bMusic.addEventListener('click', musicPanel);

  // 长按「听歌」1.5 秒：录入腾讯云语音合成密钥（存本机，不上传）
  var mTmr = null;
  bMusic.addEventListener('pointerdown', function () {
    mTmr = setTimeout(function () {
      var sid = window.prompt('腾讯云 SecretId（API 密钥里的 SecretId）', '');
      if (!sid) return;
      var sk = window.prompt('腾讯云 SecretKey', '');
      if (!sk) return;
      if (window.DaoNative && DaoNative.setTencentKeys) {
        DaoNative.setTencentKeys(sid.trim(), sk.trim());
        tip(DaoNative.hasTencentKeys() === '1' ? '密钥已存，长按「朗读」切到腾讯云语音' : '密钥没存上');
      }
    }, 1500);
  });
  ['pointerup', 'pointercancel', 'pointerleave'].forEach(function (k) {
    bMusic.addEventListener(k, function () { if (mTmr) { clearTimeout(mTmr); mTmr = null; } });
  });

  // 长按「对话」设电脑 IP（换 WiFi 时用）
  var tmr = null;
  bChat.addEventListener('pointerdown', function () {
    tmr = setTimeout(function () {
      var ip = window.prompt('电脑端 IP（同一 WiFi）', pcIp);
      if (ip) { pcIp = ip.trim(); localStorage.setItem('dao_pc_ip', pcIp); tip('已记下 ' + pcIp); }
    }, 1200);
  });
  ['pointerup', 'pointercancel', 'pointerleave'].forEach(function (k) {
    bChat.addEventListener(k, function () { if (tmr) { clearTimeout(tmr); tmr = null; } });
  });
})();
