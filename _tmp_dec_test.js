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

  

var fs=require('fs');
var b64=fs.readFileSync('F:/Daodao/src/_apk/assets/music/guitu.adp').toString('base64');
var d=decodeAdp(b64ToBuf(b64));
var out=new Int16Array(d.pcm.length);
for(var k=0;k<d.pcm.length;k++){var v=Math.round(d.pcm[k]*32768);out[k]=v>32767?32767:(v<-32768?-32768:v);}
fs.writeFileSync('F:/Daodao/_tmp_node_pcm.raw', Buffer.from(out.buffer));
console.log('JS 解码：sr='+d.sr+' 样本='+d.pcm.length+' 时长='+(d.pcm.length/d.sr).toFixed(2)+'s');
