# -*- coding: utf-8 -*-
p = r'F:\Daodao\src\_apk\assets\dao.html'
raw = open(p, 'rb').read()
s = raw.decode('utf-8')

# 1) 插入与电脑端同一套的三次贝塞尔缓动（参数照搬 Flutter Curves.easeOutCubic / easeOutQuint）
anchor = "  function boneSway(fy, ph) {"
helper = (
"  // 2026-11-17：三次贝塞尔缓动，参数照搬 Flutter 实现\n"
"  // 来源：flutter/flutter · packages/flutter/lib/src/animation/curves.dart\n"
"  //   Curves.easeOutCubic = Cubic(0.215, 0.61, 0.355, 1.0)\n"
"  //   Curves.easeOutQuint = Cubic(0.23, 1.0, 0.32, 1.0)\n"
"  function bezierAxis(t, a, b) {\n"
"    var u = 1 - t;\n"
"    return 3 * u * u * t * a + 3 * u * t * t * b + t * t * t;\n"
"  }\n"
"  function cubicEase(x, x1, y1, x2, y2) {\n"
"    if (x <= 0) return 0;\n"
"    if (x >= 1) return 1;\n"
"    var t = x, i, bx, d;\n"
"    for (i = 0; i < 8; i++) {\n"
"      bx = bezierAxis(t, x1, x2) - x;\n"
"      if (Math.abs(bx) < 1e-4) break;\n"
"      d = (bezierAxis(t + 1e-4, x1, x2) - bezierAxis(t - 1e-4, x1, x2)) / 2e-4;\n"
"      if (Math.abs(d) < 1e-6) break;\n"
"      t -= bx / d;\n"
"      if (t < 0) t = 0;\n"
"      if (t > 1) t = 1;\n"
"    }\n"
"    return bezierAxis(t, y1, y2);\n"
"  }\n"
"  function easeOutCubic(x) { return cubicEase(x, 0.215, 0.61, 0.355, 1.0); }\n"
"  function easeOutQuint(x) { return cubicEase(x, 0.23, 1.0, 0.32, 1.0); }\n"
)
assert s.count(anchor) == 1, s.count(anchor)
s = s.replace(anchor, helper + anchor, 1)

# 2) 二次动作的抬升幅度改走 easeOutCubic（原来按线性分配，越靠肩头越生硬）
old_lift = "      var lift = (fy > 0.78) ? (-0.9 * (fy - 0.78) / 0.22) * Math.sin(t * 1.05 + fy * 1.6) : 0;"
new_lift = "      var lift = (fy > 0.78) ? (-0.9 * easeOutCubic((fy - 0.78) / 0.22)) * Math.sin(t * 1.05 + fy * 1.6) : 0;"
assert s.count(old_lift) == 1, s.count(old_lift)
s = s.replace(old_lift, new_lift, 1)

open(p, 'wb').write(s.encode('utf-8'))
print("done, bytes", len(s.encode('utf-8')))
