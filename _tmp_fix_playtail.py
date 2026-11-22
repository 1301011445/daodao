# 程序版本：v0.1 | 2026-11-22 | 一次性：playSong 收尾三处（结束/失败刷新高亮、停止提示语）
import io
P = r'F:\Daodao\src\_apk\assets\dao.html'
h = io.open(P, encoding='utf-8').read()

pairs = [
    ("srcNode.onended = function () { if (playing === i) { playing = -1; } };",
     "srcNode.onended = function () { if (playing === i) { playing = -1; paintRows(); } };"),
    ("(natErr || '正常')); playing = -1; }",
     "(natErr || '正常')); playing = -1; paintRows(); }"),
    ("tip('好，我听听…');", "tip('听完了，我在想…');"),
]
for a, b in pairs:
    assert a in h, a
    h = h.replace(a, b, 1)
io.open(P, 'w', encoding='utf-8').write(h)
print('三处收尾改好')
