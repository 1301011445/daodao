# -*- coding: utf-8 -*-
"""替换 dao.html 的 playSong：原生双引擎失败后给出具体原因，并试 XHR 取 assets"""
import io

P = r'F:\Daodao\src\_apk\assets\dao.html'
s = io.open(P, encoding='utf-8').read()

start = s.index('  function playSong(i) {')
# 找函数结尾：从 function 起配平花括号
b0 = s.index('{', start)
depth = 0
i = b0
in_str = None
while i < len(s):
    c = s[i]
    if in_str:
        if c == '\\':
            i += 2
            continue
        if c == in_str:
            in_str = None
    elif c in '"\'"':
        in_str = c
    elif c == '{':
        depth += 1
    elif c == '}':
        depth -= 1
        if depth == 0:
            break
    i += 1
end = i + 1
old = s[start:end]

new = '''  function playSong(i) {
    var s = SONGS[i];
    if (playing === i) { stopMusic(); return; }
    stopMusic();
    // 唱歌前先把朗读停掉，两路声音不能一起响
    try { if (window.DaoNative && DaoNative.stopAll) DaoNative.stopAll(); } catch (e) {}
    try { if (window.speechSynthesis) window.speechSynthesis.cancel(); } catch (e) {}
    playing = i;
    tip('载入《' + s.t + '》…');
    // 先交给原生：读 assets、解 ADPCM，再 MediaPlayer / AudioTrack 放（2026-11-22 双引擎）
    var natErr = '';
    if (window.DaoNative && DaoNative.playSongAsset) {
      try {
        var nr = String(DaoNative.playSongAsset(s.k || ''));
        if (nr.indexOf('OK') === 0) { tip('正在放《' + s.t + '》，再点一下停'); return; }
        natErr = nr.replace(/^ERR\\|/, '').replace(/^ERR/, '');
      } catch (e2) { natErr = '桥接异常 ' + (e2 && e2.message ? e2.message : ''); }
    } else { natErr = '这一版没有原生播放接口'; }
    // 原生不行 → 网页自己解。先 assetB64，读不到就用 XHR 直接取 assets
    var b64 = '';
    try { b64 = (window.DaoNative && DaoNative.assetB64) ? String(DaoNative.assetB64(s.f) || '') : ''; } catch (e3) { b64 = ''; }
    if (!b64 && window.DaoNative && DaoNative.assetXhr) {
      try {
        var xr = String(DaoNative.assetXhr(s.f) || '');
        if (xr && xr.indexOf('ERR') !== 0) b64 = xr;
        else if (xr) natErr = natErr + ' / ' + xr;
      } catch (e4) {}
    }
    if (!b64) { tip('放不了：' + (natErr || '未知原因') + '；也读不到 ' + s.f); playing = -1; return; }
    try {
      if (!actx) actx = new (window.AudioContext || window.webkitAudioContext)();
      // 解一次缓存一次：同一首再点不用重新解码（4M 采样现解要一两秒）
      var buf = songBufCache[s.f];
      if (!buf) {
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
      tip('正在放《' + s.t + '》，再点一下暂停' + (natErr ? '（原生没成，走的网页解码）' : ''));
    } catch (e) { tip('放不了：' + e.message + '；原生 ' + (natErr || '正常')); playing = -1; }
  }'''

s = s[:start] + new + s[end:]
io.open(P, 'w', encoding='utf-8').write(s)
print('替换完成，字符 %d -> %d' % (len(old), len(new)))
print('引用 assetXhr：', s.count('assetXhr'))
