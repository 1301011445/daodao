# 程序版本：v0.1 | 2026-11-22 | 一次性：dao.html 行为自测（面板状态机 + 按住说话）
import io
h = io.open(r'F:\Daodao\src\_apk\assets\dao.html', encoding='utf-8').read()
checks = [
    ('win 关面板时置空', h.count('win = null') >= 2),
    ('stopAudio 独立', 'function stopAudio()' in h),
    ('关面板走 closePanel', 'function closePanel()' in h),
    ('唱歌面板能再开', 'if (win) { stopMusic(); return; }' in h),
    ('点歌不再关面板', 'if (playing === i) { stopAudio(); return; }' in h),
    ('行高亮刷新 >=5 处', h.count('paintRows();') >= 5),
    ('按住说话', 'function startHold' in h and 'function endHold' in h),
    ('松手兜底 document', "document.addEventListener('pointerup'" in h),
    ('触摸不吃手势', '#btnTalk { touch-action: none' in h),
    ('短按阈值 350ms', 'held < 350' in h),
]
for n, ok in checks:
    print(('  OK   ' if ok else '  FAIL ') + n)
print('自测 ' + ('PASS' if all(o for _, o in checks) else 'FAIL'))
