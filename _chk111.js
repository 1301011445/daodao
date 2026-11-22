
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
      'position:fixed;left:50%;transform:translateX(-50%);bottom:140px;z-index:10060;' +
      'max-width:80vw;padding:9px 14px;border-radius:12px;background:rgba(0,0,0,.78);color:#fff;' +
      'font-size:15px;line-height:1.45;font-family:system-ui,sans-serif;pointer-events:none;');
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
  // v0.91：输入框删了之后「讲题」没了入口，这里按话里的意思分流：
  //         说「这题怎么做 / 讲一下 / 帮我解」就走进讲题，其余照旧走聊天
  var EXPLAIN_RE = /(这|那)[道个]?题|解题|怎么解|怎么算|讲讲|讲一下|帮我讲|解释一下|说下思路/;
  // v0.96：记事本入口。说「记一下…」「提醒我…」就登记到电脑上的 记事本.txt，到点它会自己开口
  // v0.106：句首是时间/重复词也算登记（说「每天 早上八点 打卡」以前被判成闲聊）
  var NOTE_RE = /^(记一下|记一条|记下|帮我记|提醒我|待办|记住)|^(每天|每日|每周|每星期|每礼拜|每月|明天|后天|大后天|今早|今晚|今儿)\s*.{0,14}?[\d一二三四五六七八九十两]{1,2}[点時时]|^[上下中晚凌晨早白夜傍]{0,3}\s*[\d一二三四五六七八九十两]{1,2}[点時时]/;
  var NOTE_READ_RE = /(记事本|念一下|读一下|今天有什么|有什么安排|今天要做什么|还有什么事|待办有哪些)/;
  var NOTE_Q = 'dao_note_queue';

  function noteSay(s) {
    if (!s) return;
    try { if (window.DaoNative && DaoNative.speak) DaoNative.speak(s); } catch (e) {}
  }

  function noteQueueAdd(text) {
    try {
      var q = JSON.parse(localStorage.getItem(NOTE_Q) || '[]');
      q.push(text);
      localStorage.setItem(NOTE_Q, JSON.stringify(q));
    } catch (e) {}
  }

  function noteFlush() {
    var q = [];
    try { q = JSON.parse(localStorage.getItem(NOTE_Q) || '[]'); } catch (e) {}
    if (!q.length) return;
    var done = [];
    function one(i) {
      if (i >= q.length) {
        try { localStorage.setItem(NOTE_Q, '[]'); } catch (e) {}
        if (done.length) { tip('补记上了 ' + done.length + ' 条'); noteSync(); }
        return;
      }
      fetch('http://' + pcIp + ':8848/note?op=add&text=' + encodeURIComponent(q[i]))
        .then(function (r) { return r.text(); })
        .then(function (s) {
          if (s.indexOf('OK|') === 0) { done.push(q[i]); var f = s.split('|'); phoneAlarm(f[1], f[2], f[3]); one(i + 1); }
          else { one(i + 1); }
        })
        .catch(function () { try { localStorage.setItem(NOTE_Q, JSON.stringify(q.slice(i))); } catch (e) {} });
    }
    one(0);
  }

  var NOTE_MAIL_RE = /(提醒|通知|消息).{0,6}发到|收件邮箱|发到哪个邮箱|邮箱设成|改成.{0,12}@|也发到|加上.{0,10}@|多发.{0,10}@|清空收件|取消收件|别发邮件|不发邮件|收件人|哪个邮箱发|用什么邮箱发/;
  var MAIL_RE = /[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}/g;

  var NOTE_DONE_RE = /(做完了|办完了|弄完了|完成了|搞定了|搞定了|已经弄好|已经做完|这条好了|那件事做完了)/;
  // v0.106：多加裸「去掉/拿掉/划掉」和「别再提醒」这种夹了字的说法
  var NOTE_DEL_RE = /(删掉|删除|去掉|拿掉|划掉|不要这条|取消这条|别(再|又)?提醒|不用(再)?提醒|别再?说这个)/;

  // 句子里的时间串转人话：'2026-11-22 09:00' → '11月22日9点'
  function noteHuman(w) {
    var m = String(w || '').match(/^(\d{4})-(\d{2})-(\d{2})\s*(\d{2}):(\d{2})/);
    if (!m) return String(w || '');
    var mm = parseInt(m[2], 10), dd = parseInt(m[3], 10), hh = parseInt(m[4], 10), mi = parseInt(m[5], 10);
    return mm + '月' + dd + '日' + hh + '点' + (mi === 0 ? '' : mi + '分');
  }

  // 这句话到底在说记事本里的哪一条？先看「第 N 条」，再拿句子里剥掉动词剩下的词去比待办名
  function noteStripCmd(text) {
    return String(text || '').replace(/把|帮我|请|这条|那条|一下|标记|已经|算|做完了|完成了|办完了|弄完了|搞定|搞定了|删掉|删除|去掉|拿掉|划掉|取消|别(再|又)?提醒|不用(再)?提醒|了|吧|。|，|、|！|？/g, '').replace(/\s+/g, '');
  }

  function noteMatchTodo(text) {
    var arr = [], s = String(text || '');
    try { arr = JSON.parse(localStorage.getItem('dao_note_list') || '[]') || []; } catch (e) { arr = []; }
    if (/第\s*([0-9]{1,3}|[一二三四五六七八九十]{1,3})\s*条/.test(s)) return 'id';
    var key = noteStripCmd(s);
    if (!key) return /这条|那条|这件事|那件事/.test(s) ? 'latest' : '';
    for (var i = 0; i < arr.length; i++) {
      if (arr[i].done === '1') continue;
      if (String(arr[i].text || '').indexOf(key) >= 0) return 'name';
    }
    for (var j = 0; j < arr.length; j++) {
      if (arr[j].done === '1') continue;
      var t = String(arr[j].text || '');
      if (t && key.indexOf(t) >= 0) return 'name';
    }
    if (/这条|那条|这件事|那件事/.test(s)) return 'latest';
    return '';
  }

  // 「这条」指哪条：镜像里还没做完、时间最早的那条
  function noteNearest() {
    var arr = [], best = null, bestMs = 0;
    try { arr = JSON.parse(localStorage.getItem('dao_note_list') || '[]') || []; } catch (e) { arr = []; }
    for (var i = 0; i < arr.length; i++) {
      if (arr[i].done === '1') continue;
      var ms = new Date(String(arr[i].when).replace(/-/g, '/') + ':00').getTime();
      if (!(ms > 0)) continue;
      if (!best || ms < bestMs) { best = arr[i]; bestMs = ms; }
    }
    return best;
  }


  function noteBy(op, text, id) {
    var base = id
      ? ('http://' + pcIp + ':8848/note?op=' + (op === 'doneby' ? 'done' : 'del') + '&id=' + id)
      : ('http://' + pcIp + ':8848/note?op=' + op + '&text=' + encodeURIComponent(text));
    fetch(base).then(function (r) { return r.text(); }).then(function (s) {
      var msg;
      if (s.indexOf('OK|') === 0) {
        var f = s.split('|'), rid = parseInt(f[1], 10) || 0;
        msg = (op === 'doneby' ? '好，这条算做完了：' : '好，删掉了：') + (f[2] || '');
        if (f[4]) msg += '，' + f[4] + '下次在' + noteHuman(f[3]) + '，我到时候再喊你';
        try { if (window.DaoNative && DaoNative.noteCancel && rid) DaoNative.noteCancel(rid); } catch (e) {}
        noteSync();
      } else if (s === 'OK') {
        msg = (op === 'doneby' ? '好，这条算做完了：' : '好，删掉了：') + (text || '');
        try { if (window.DaoNative && DaoNative.noteCancel && id) DaoNative.noteCancel(id); } catch (e) {}
        noteSync();
      } else {
        msg = s.indexOf('ERR|') === 0 ? ('没改成：' + s.substring(4)) : ('没改成：' + s);
      }
      tip(msg); noteSay(msg);
    }).catch(function () { tip('电脑没连上，等它回话再改'); });
  }

  function noteDone(text) { noteBy('doneby', text); }
  function noteDel(text) { noteBy('delby', text); }

  function noteMail(text) {
    var s = String(text);
    var mails = s.match(MAIL_RE) || [];
    var base = 'http://' + pcIp + ':8848/note?op=';
    var url, adding = false;
    if (mails.length > 0) {
      adding = /也发|加上|再加|顺便发|多发/.test(s);
      url = base + 'setmail&to=' + encodeURIComponent(mails.join(',')) + (adding ? '&add=1' : '');
    } else if (/清空|取消收件|别发|不发/.test(s)) {
      url = base + 'setmail&clear=1';
    } else if (/哪个邮箱发|用什么邮箱发|发件|谁发的/.test(s)) {
      url = base + 'mailinfo';
    } else {
      url = base + 'getmail';
    }
    fetch(url).then(function (r) { return r.text(); }).then(function (res) {
      var msg;
      if (res.indexOf('OK|') === 0) {
        msg = res.substring(3);
        if (mails.length > 0 && !adding) msg = '好，提醒发到 ' + msg;
        else if (mails.length > 0 && adding) msg = '好，也发到 ' + msg;
        else if (url.indexOf('mailinfo') > 0) msg = msg;
        else if (url.indexOf('getmail') > 0) msg = msg === '还没设收件邮箱' ? '现在还没设收件邮箱，只在本机说话' : ('现在发到 ' + msg);
      } else {
        msg = '没设上：' + res;
      }
      tip(msg); noteSay(msg);
    }).catch(function () { tip('电脑没连上，等它回话再设'); });
  }

  function phoneAlarm(idStr, whenStr, text) {
    try {
      if (!(window.DaoNative && DaoNative.noteAlarm)) return;
      var ms = new Date(String(whenStr).replace(/-/g, '/') + ':00').getTime();
      if (!(ms > 0)) return;
      DaoNative.noteAlarm(parseInt(idStr, 10) || 0, ms, text);
    } catch (e) {}
  }

  function noteAdd(text) {
    var url = 'http://' + pcIp + ':8848/note?op=add&text=' + encodeURIComponent(text);
    fetch(url).then(function (r) { return r.text(); }).then(function (s) {
      if (s.indexOf('OK|') === 0) {
        var f = s.split('|');
        var when = noteHuman(f[2]), rep = f[4] || '';
        tip('记下了：' + (rep ? rep + ' ' : '') + when + ' ' + f[3]);
        noteSay('记下了，' + (rep ? rep + '，' : '') + when + '，' + f[3]);
        phoneAlarm(f[1], f[2], f[3]);
        noteSync();
      } else {
        tip('没记上：' + s);
      }
    }).catch(function () {
      noteQueueAdd(text);
      tip('电脑没连上，先记在手机上，等我回话再补');
    });
  }

  function noteRead() {
    fetch('http://' + pcIp + ':8848/note?op=today').then(function (r) { return r.text(); }).then(function (s) {
      var t = s.indexOf('OK|') === 0 ? s.substring(3) : '记事本打不开';
      if (s.indexOf('OK|') === 0) { try { localStorage.setItem('dao_note_last', t); } catch (e) {} noteSync(); }
      tip(t);
      noteSay(t);
    }).catch(function () {
      var local = noteLocalText();
      var last = '';
      try { last = localStorage.getItem('dao_note_last') || ''; } catch (e) {}
      var t = local ? ('电脑没连上，按手机上记的：' + local) : (last ? ('电脑没连上，这是上次记下的：' + last) : '电脑没连上，手机上还没有记事本备份');
      tip(t);
      noteSay(t);
    });
  }

  // 把电脑上的记事本（条目级）同步一份到手机上，断网时也能念
  var NOTE_LIST = 'dao_note_list';
  function noteSync() {
    fetch('http://' + pcIp + ':8848/note?op=list').then(function (r) { return r.text(); }).then(function (s) {
      if (s.indexOf('OK') !== 0) return;
      var rows = s.split('\n').slice(1), arr = [];
      for (var i = 0; i < rows.length; i++) {
        var f = rows[i].split('\t');
        if (f.length < 5) continue;
        arr.push({ id: f[0], when: f[1], done: f[2], text: f[4] });
      }
      try { localStorage.setItem(NOTE_LIST, JSON.stringify(arr)); } catch (e) {}
      phoneAlarmAll(arr);
    }).catch(function () {});
  }

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
    var m = String(w || '').match(/^(\d{4})-(\d{2})-(\d{2})\s+(\d{2}):(\d{2})/);
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

  // 把手机镜像里的待办整体重排一遍闹钟（重复提醒滚到下一条后靠这次刷新接上）
  function phoneAlarmAll(arr) {
    if (!(window.DaoNative && DaoNative.noteAlarm)) return;
    var now = Date.now();
    for (var i = 0; i < arr.length; i++) {
      if (arr[i].done === '1') continue;
      var ms = new Date(String(arr[i].when).replace(/-/g, '/') + ':00').getTime();
      if (!(ms > now + 60000)) continue;
      phoneAlarm(arr[i].id, arr[i].when, arr[i].text);
    }
  }

  function noteLocalText() {
    var arr = [];
    try { arr = JSON.parse(localStorage.getItem(NOTE_LIST) || '[]'); } catch (e) {}
    if (!arr.length) return '';
    var d = new Date();
    var ymd = function (dt) {
      var m = dt.getMonth() + 1, day = dt.getDate();
      return dt.getFullYear() + '-' + (m < 10 ? '0' + m : m) + '-' + (day < 10 ? '0' + day : day);
    };
    var today = ymd(d), tm = new Date(d.getTime() + 86400000), tomorrow = ymd(tm);
    var overdue = [], tdy = [], tmr = [];
    for (var i = 0; i < arr.length; i++) {
      if (arr[i].done === '1') continue;
      var when = String(arr[i].when || ''), day = when.substring(0, 10);
      var hm = when.substring(11, 16).split(':');
      var label = (parseInt(hm[0], 10) || 0) + '点' + (hm[1] || '00') + '分';
      var line = label + ' ' + arr[i].text;
      if (day === today) tdy.push(line);
      else if (day === tomorrow) tmr.push(line);
      else if (day < today) overdue.push(line);
    }
    var out = '';
    if (overdue.length) out += '逾期' + overdue.length + '件：' + overdue.join('；') + '。';
    if (tdy.length) out += '今天有' + tdy.length + '件：' + tdy.join('；') + '。';
    if (tmr.length) out += '明天有' + tmr.length + '件：' + tmr.join('；') + '。';
    return out || '这两天没有要做的。';
  }

  // 手机本地闹钟响、点通知进来时，原生端会调这个函数，让它把这条念出来
  window.__daoAlarm = function (t) {
    if (!t) t = '到点了';
    try { tip('到点了：' + t); } catch (e) {}
    try { noteSay('到点了，' + t); } catch (e) {}
    // 响过一次之后同步一次：重复提醒（每天/每周/每月）要马上把下一次排上，不然只响这一回
    setTimeout(function () { try { noteSync(); } catch (e) {} }, 1500);
  };

  function noteAlarmSetting() {
    var ok = false;
    try { ok = (window.DaoNative && DaoNative.noteOpenAlarmSetting) ? DaoNative.noteOpenAlarmSetting() : false; } catch (e) {}
    var t = ok ? '带你去开「精确闹钟」，允许了提醒才会准点响' : '这个机型不用单独开，或者系统里没这个开关';
    tip(t); noteSay(t);
  }

  window.__daoVoice = function (id, text) {
    if (!text) return;
    if (/没听清|权限|没有语音识别|启动失败/.test(text)) { tip(text); return; }
    tip('你说：' + text);
    noteFlush();
    if (/精确闹钟|闹钟不准|提醒不准|闹钟权限/.test(text)) { noteAlarmSetting(); return; }
    if (NOTE_MAIL_RE.test(text)) { noteMail(text); return; }
    // v0.106：说「完成了/搞定了」不一定是记事本的事，得先认出是哪一条，认不出就当普通聊天
    if (NOTE_DONE_RE.test(text) || NOTE_DEL_RE.test(text)) {
      var hit = noteMatchTodo(text), isDone = NOTE_DONE_RE.test(text);
      if (hit === 'latest') {
        var nb = noteNearest();
        if (nb) { noteBy(isDone ? 'doneby' : 'delby', nb.text, parseInt(nb.id, 10) || 0); return; }
        var none = '记事本上现在没有待办的事';
        tip(none); noteSay(none); return;
      }
      if (hit) { if (isDone) noteDone(text); else noteDel(text); return; }
      if (text.length <= 14 && (/^(把|帮我|请|第)/.test(text) || /^(这条|那条|这件事|那件事)/.test(text)) && !/陪|聊|笑话|天气|吃饭|睡觉|你好|谢谢/.test(text)) {
        var nohit = '记事本里没找到这条，说个名字或者「第几条」都行';
        tip(nohit); noteSay(nohit); noteSync(); return;
      }
    }
    if (NOTE_READ_RE.test(text)) { noteRead(); return; }
    if (NOTE_RE.test(text)) { noteAdd(text); return; }
    if (EXPLAIN_RE.test(text) && window.daoExplain) { window.daoExplain(text); return; }
    chatAsk(text);
  };
  setTimeout(noteFlush, 800);
  setTimeout(noteSync, 1000);
  // 手机第一次用记事本前，先要一次通知权限（Android 13 起必须显式申请）
  setTimeout(function () {
    try {
      if (window.DaoNative && DaoNative.noteCanNotify && DaoNative.noteAskPermission) {
        if (!DaoNative.noteCanNotify()) DaoNative.noteAskPermission();
      }
    } catch (e) {}
  }, 1500);
  // Android 12 起精确闹钟要单独授权，没开就提示一次
  setTimeout(function () {
    try {
      if (window.DaoNative && DaoNative.noteAlarmOk && !DaoNative.noteAlarmOk()) {
        tip('精确闹钟没开，提醒可能晚几分钟；说「开精确闹钟」我带你去设置');
      }
    } catch (e) {}
  }, 2000);

  // 「跟它说话」：2026-11-22 按用户要求改成「按住说，松手发」——对话按长按时长算。
  // 按下就开始录，松手结束并让原生识别；按不到 0.35 秒当误触，只提示不硬发；
  // 按住期间按钮上实时显示已按多少秒，看得见这一句说了多长。
  var streamed = false;
  var talkBtn = document.getElementById('btnTalk');
  var listening = false;
  var holdT0 = 0, holdTick = null;

  function startListen() {
    if (!(window.DaoNative && (DaoNative.listenCloud || DaoNative.listen))) {
      tip('这台设备没有语音通道，装到手机上就能跟我说');
      return;
    }
    listening = true;
    try { if (window.DaoNative && DaoNative.stopAll) DaoNative.stopAll(); } catch (e) {}
    talkBtn.classList.add('listening');
    try { if (DaoNative.listenCloud) DaoNative.listenCloud('mic'); else DaoNative.listen('mic'); } catch (e) {}
    tip('按住别松，说完松手');
  }
  function stopListen() {
    listening = false;
    talkBtn.classList.remove('listening');
    try { if (DaoNative.stopListenCloud) DaoNative.stopListenCloud(); else if (DaoNative.stopListen) DaoNative.stopListen(); } catch (e) {}
    tip('听完了，我在想…');
  }
  function abortListen() {
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

  var rows = [], statusEl = null;
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
          setStatus('播放没在走：' + dg + '（查音量/耳机，或这台的音频流不正常）', true);
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
  // ---------- 手机桌面上（浮窗）----------
  // 2026-11-22：电脑端那四种样子搬到手机上。点「上桌面」开面板，
  // 选 满身 / 贴边偷看 / 小圆球 / 收起；真挂窗口的是原生 DaoOverlay 前台服务。
  var ovPanel = document.getElementById('ovPanel');
  var ovBtns = ovPanel ? ovPanel.querySelectorAll('#ovGrid button[data-m]') : [];
  var ovSideBtn = document.getElementById('ovSide');
  var ovPoll = null;

  function ovHas() { return !!(window.DaoNative && DaoNative.overlayOn); }
  function ovState() {
    try { if (window.DaoNative && DaoNative.overlayState) return DaoNative.overlayState(); } catch (e) {}
    return '0|1|2';
  }
  function ovPaint() {
    var s = String(ovState()).split('|');
    var on = s[0] === '1', m = parseInt(s[1], 10), sd = parseInt(s[2], 10);
    for (var i = 0; i < ovBtns.length; i++) {
      var k = parseInt(ovBtns[i].getAttribute('data-m'), 10);
      if (on && k === m) ovBtns[i].classList.add('on'); else ovBtns[i].classList.remove('on');
    }
    if (ovSideBtn) ovSideBtn.textContent = '换一边（现在在' + (sd === 1 ? '左' : '右') + '边）';
  }
  function ovOpen() {
    if (!ovHas()) { tip('这台设备没有浮窗通道，装到手机上才有'); return; }
    ovPaint();
    ovPanel.classList.add('show');
    if (ovPoll) clearInterval(ovPoll);
    ovPoll = setInterval(ovPaint, 900);
  }
  function ovClose() {
    if (!ovPanel) return;
    ovPanel.classList.remove('show');
    if (ovPoll) { clearInterval(ovPoll); ovPoll = null; }
  }
  function ovNeedPerm() {
    try { if (window.DaoNative && DaoNative.overlayReady && DaoNative.overlayReady() === '1') return false; } catch (e) {}
    try { if (window.DaoNative && DaoNative.overlayAsk) DaoNative.overlayAsk(); } catch (e) {}
    tip('先去系统设置里允许「显示在其他应用上层」，回来再点一次');
    return true;
  }
  function ovCall(fn, arg) {
    try { if (window.DaoNative && DaoNative[fn]) return DaoNative[fn](arg); } catch (e) { tip('叫不动浮窗'); }
    return '';
  }
  if (ovPanel) {
    document.getElementById('ovClose').addEventListener('click', ovClose);
    document.getElementById('btnDesk').addEventListener('pointerdown', function (e) {
      if (e && e.preventDefault) e.preventDefault();
      if (ovPanel.classList.contains('show')) ovClose(); else ovOpen();
    });
    for (var oi = 0; oi < ovBtns.length; oi++) {
      ovBtns[oi].addEventListener('click', function () {
        var m = parseInt(this.getAttribute('data-m'), 10);
        if (ovNeedPerm()) return;
        if (m === 3 && ovState().split('|')[0] === '1') ovCall('overlayMode', 3);
        else ovCall('overlayOn', m);
        setTimeout(ovPaint, 400);
        if (m === 3) tip('窗口收起来了，通知栏里还留着，点一下能唤回');
        else if (m === 2) tip('缩成小球了，点它一下就站起来');
        else if (m === 1) tip('去边上扒着了，点它一下回满身');
        else tip('满身站到桌面上了，按一下主页键看看');
      });
    }
    document.getElementById('ovSide').addEventListener('click', function () {
      if (ovNeedPerm()) return;
      ovCall('overlaySide');
      setTimeout(ovPaint, 400);
      tip('换到另一边了');
    });
    document.getElementById('ovOff').addEventListener('click', function () {
      ovCall('overlayOff');
      setTimeout(ovPaint, 300);
      ovClose();
      tip('从桌面上拿下来了');
    });
    document.getElementById('ovPerm').addEventListener('click', function () {
      if (window.DaoNative && DaoNative.overlayAsk) ovCall('overlayAsk');
      else tip('这台设备开不了这个权限');
    });
  }

  window.daoStopMusic = stopMusic;
  window.daoMusicPanel = musicPanel;
  window.daoPlaySong = playSong;
  window.daoPlayNext = function () { playSong((playing + 1) % (SONGS.length || 1)); };
})();
