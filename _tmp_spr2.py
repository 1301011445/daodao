# 程序版本：v0.1 | 2026-11-22 | SPR 加一档：alpha<200 的粉边也把绿抬到 min(R,B)
import io
P = r'F:\Daodao\src\_apk\assets\dao.html'
h = io.open(P, encoding='utf-8').read()
a = """        else if (a < 40) {
          var r = p[i], gg = p[i + 1], b = p[i + 2], mn = Math.min(r, b);
          if (r > 90 && b > 90 && gg < mn * 0.8) {
            var t = (r + b) / 2;
            p[i + 1] = t > 255 ? 255 : (t < 0 ? 0 : t);
          }
        }"""
b = """        else if (a < 200) {
          // 淡边（a<200）上的粉/紫：直接把绿抬到 min(R,B)，去掉紫味但不改亮度太多
          var r = p[i], gg = p[i + 1], b = p[i + 2], mn = Math.min(r, b);
          if (r > 110 && b > 110 && gg < mn * 0.85) {
            p[i + 1] = mn;
          }
        }"""
assert a in h
io.open(P, 'w', encoding='utf-8').write(h.replace(a, b, 1))
print('SPR 规则已扩到 alpha<200')
