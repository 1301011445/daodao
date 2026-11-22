# 程序版本：v0.1 | 2026-11-22 | 一次性：给 dao.html 的立绘绘制加 alpha 边带清理（治紫晕）
"""给 dao.html 加 SPR()：绘制前把 alpha≈0 处的残留色归零、alpha 很低且偏紫的像素去色，
再把 6 处 ctx.drawImage 的首参包一层。治 Q-083 里那种「同一张图在深色背景上浮现紫晕」。
"""
import io, re, shutil, datetime

P = r'F:\Daodao\src\_apk\assets\dao.html'
shutil.copyfile(P, P + '.bak_20261122_despill')
h = io.open(P, encoding='utf-8').read()

HELPER = '''  // 2026-11-22 Q-083：内嵌 webp 有不少「alpha=0 但 RGB 还留着紫」的像素。WebView 缩放时
  // 若没按预乘处理，这些看不见的颜色会顺着插值渗出来，就是深色底上的紫晕/粉晕。
  // 绘制前先过一遍：全透明处 RGB 归零；alpha 很低又是偏紫的，把绿提起来压掉紫味。
  // 结果按源对象缓存，同一张图只算一次。
  function SPR(src) {
    if (!src) return src;
    if (src.__clean) return src.__clean;
    try {
      var w = src.naturalWidth || src.width, hh = src.naturalHeight || src.height;
      if (!w || !hh) return src;
      var c = document.createElement('canvas');
      c.width = w; c.height = hh;
      var g = c.getContext('2d');
      g.drawImage(src, 0, 0);
      var d = g.getImageData(0, 0, w, hh), p = d.data, n = p.length;
      for (var i = 0; i < n; i += 4) {
        var a = p[i + 3];
        if (a < 6) { p[i] = 0; p[i + 1] = 0; p[i + 2] = 0; }
        else if (a < 40) {
          var r = p[i], gg = p[i + 1], b = p[i + 2], mn = Math.min(r, b);
          if (r > 90 && b > 90 && gg < mn * 0.8) {
            var t = (r + b) / 2;
            p[i + 1] = t > 255 ? 255 : (t < 0 ? 0 : t);
          }
        }
      }
      g.putImageData(d, 0, 0);
      src.__clean = c;
      return c;
    } catch (e) { return src; }
  }

'''

assert 'function SPR(' not in h
anchor = '  function resize() {'
assert anchor in h
h = h.replace(anchor, HELPER + anchor, 1)

h, n = re.subn(r'ctx\.drawImage\(([A-Za-z_$][\w.$\[\]]*)\s*,', r'ctx.drawImage(SPR(\1),', h)
print('drawImage 包装了', n, '处')
assert n == 6, 'drawImage 处数和预期不一致'

io.open(P, 'w', encoding='utf-8').write(h)
print('已写入', P)
