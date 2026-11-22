# 程序版本：v0.1 | 2026-11-22 | 一次性：失败提示带上「原生错误 / b64 长度」，截图就能定位
import io
P = r'F:\Daodao\src\_apk\assets\dao.html'
h = io.open(P, encoding='utf-8').read()

a = "if (!b64) { tip('放不了：' + (natErr || '未知原因') + '；也读不到 ' + s.f); playing = -1; paintRows(); return; }"
b = ("if (!b64) { tip('放不了：' + (natErr || '未知原因') + '；' + s.f + ' 读到 0 字节'); "
     "playing = -1; paintRows(); return; }")
assert a in h
h = h.replace(a, b, 1)

# 原生那句 ERR 太长时截断，保持一行能截全屏
a2 = "natErr = nr.replace(/^ERR\\|/, '').replace(/^ERR/, '');"
b2 = "natErr = nr.replace(/^ERR\\|/, '').replace(/^ERR/, '').slice(0, 120);"
assert a2 in h
h = h.replace(a2, b2, 1)

io.open(P, 'w', encoding='utf-8').write(h)
print('失败提示已加长（带字节数/截断原生错误）')
