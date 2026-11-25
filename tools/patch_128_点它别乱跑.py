# -*- coding: utf-8 -*-
"""v128 修「点它就乱动还走掉」
根因三条：
1) ACTION_MOVE 阈值只有 6dp：手指一点点的抖动就被判成拖动，窗口跟着手指乱窜。
2) ACTION_UP 里「按住超过 400ms 但没移动」直接 cycleArt() 换形象 —— 点击稍慢就变脸，观感就是乱动。
3) walkDrift() 只给 2 秒冷却：戳完一放手，两三秒内自己又开始走，走出屏幕回来不在原地。
另外「点一下 = 直接开 App」，一戳人就整只消失，也会被当成走掉。

改法：
- 拖动阈值 6dp → 16dp（真拖动才跟手）
- 碰一下就立刻收住当前这一步走路，并且 8 秒内不自己走
- 单点 = 站定 + 应一声（点头+挥手+说一句），不再开 App
- 双击（500ms 内两下）= 打开 App
- 长按不再换形象（换形象只留通知栏那颗按钮，避免误触）
判据 P1~P6
"""
P = r'F:\Daodao\src\_apk\src\com\daodao\pet\DaoOverlay.java'
s = open(P, encoding='utf-8').read()
stats = []


def rep(old, new, tag):
    global s
    if old not in s:
        print('MISS', tag)
        return False
    s = s.replace(old, new, 1)
    stats.append(tag)
    return True


# 1) 记双击用的上次点击时刻
rep('    private long touchAt = 0;',
    '    private long touchAt = 0;\n    private long lastTapAt = 0;   // v128 双击判定：500ms 内第二下才算双击',
    '字段 lastTapAt')

# 2) 触摸：阈值放大、按下即收步、单击应声、双击开 App、长按不换形象
rep('''                case MotionEvent.ACTION_DOWN:
                    dRx = e.getRawX(); dRy = e.getRawY();
                    wx0 = lp.x; wy0 = lp.y;
                    t0 = System.currentTimeMillis();
                    touchAt = t0;
                    moved = false;
                    return true;
                case MotionEvent.ACTION_MOVE: {
                    float dx = e.getRawX() - dRx, dy = e.getRawY() - dRy;
                    if (!moved && (Math.abs(dx) > dp(6) || Math.abs(dy) > dp(6))) moved = true;
                    if (moved) dragTo(wx0 + (int) dx, wy0 + (int) dy);
                    touchAt = System.currentTimeMillis();
                    return true;
                }
                case MotionEvent.ACTION_UP: {
                    long dt = System.currentTimeMillis() - t0;
                    if (!moved && dt < 400) {
                        onTap();
                    } else if (!moved) {
                        cycleArt();          // 长按不动 = 换形象（跟通知里那颗按钮同一个口子）
                    } else {
                        onDrop();
                    }
                    return true;
                }''',
    '''                case MotionEvent.ACTION_DOWN:
                    dRx = e.getRawX(); dRy = e.getRawY();
                    wx0 = lp.x; wy0 = lp.y;
                    t0 = System.currentTimeMillis();
                    touchAt = t0;
                    moved = false;
                    // v128：手一碰就先站住，别让人边点边走
                    walking = false;
                    if (pv != null) pv.walking = false;
                    return true;
                case MotionEvent.ACTION_MOVE: {
                    float dx = e.getRawX() - dRx, dy = e.getRawY() - dRy;
                    // v128：阈值 6dp → 16dp。手指按在桌面上天然会抖 2~8dp，
                    // 原来那点抖动就被当成拖动，窗口跟着手指乱窜。
                    if (!moved && (Math.abs(dx) > dp(16) || Math.abs(dy) > dp(16))) moved = true;
                    if (moved) dragTo(wx0 + (int) dx, wy0 + (int) dy);
                    touchAt = System.currentTimeMillis();
                    return true;
                case MotionEvent.ACTION_UP: {
                    long dt = System.currentTimeMillis() - t0;
                    long now = System.currentTimeMillis();
                    touchAt = now;
                    if (moved) {                // 真拖动：只落位，不演动作
                        lastTapAt = 0;
                        onDrop();
                    } else if (dt < 400) {      // 轻点
                        if (lastTapAt != 0 && now - lastTapAt < 500) {
                            lastTapAt = 0;
                            openApp();          // 双击：打开 App
                        } else {
                            lastTapAt = now;
                            onTap();            // 单击：站定应一声
                        }
                    } else {                    // 长按：也只应一声，换形象另走通知按钮
                        lastTapAt = 0;
                        onTap();
                    }
                    return true;
                }''',
    '触摸判定')

# 3) 走路冷却 2s → 8s，且立刻收步
rep('        if (now - touchAt < 2000) { walking = false; if (pv != null) pv.walking = false; return; }',
    '''        // v128：原来只挡 2 秒，戳完一放手两三秒内又自己开走，走出屏幕；改成 8 秒
        if (now - touchAt < 8000) {
            if (walking) { walking = false; if (pv != null) pv.walking = false; }
            walkNextAt = now + 6000;
            return;
        }''',
    '走路冷却')

# 4) 单击：站定 + 应声（满身时不再直接开 App）
rep('''        private void onTap() {
            if (vm == MODE_BALL || vm == MODE_PEEK) {
                // 跟电脑端一个规矩：戳一下就站直，不再满屏贴边；顺手打个招呼
                setModeInternal(MODE_FULL);
                greet(true);
            } else {
                openApp();
            }
        }''',
    '''        private void onTap() {
            // v128：单击只做「站定 + 应一声」，不再一戳就把 App 弹出来（那样看着像人凭空没了）。
            // 要开 App 改成双击。
            long now = System.currentTimeMillis();
            touchAt = now;
            walking = false;
            if (pv != null) pv.walking = false;
            if (vm == MODE_BALL || vm == MODE_PEEK) {
                setModeInternal(MODE_FULL);
            }
            greet(true);
        }''',
    '单击应声')

open(P, 'w', encoding='utf-8').write(s)
print('PATCH_OK 改动', len(stats))

j = open(P, encoding='utf-8').read()
checks = [
    ('P1 拖动阈值 16dp', 'Math.abs(dx) > dp(16)' in j and 'dp(6)' not in j),
    ('P2 按下即收步', 'walking = false;\n                    if (pv != null) pv.walking = false;' in j),
    ('P3 单击不弹 App / 双击才弹', 'lastTapAt != 0 && now - lastTapAt < 500' in j and 'android:onClick' not in j),
    ('P4 长按不换形象', 'cycleArt();          // 长按不动' not in j),
    ('P5 走路冷却 8 秒', 'now - touchAt < 8000' in j),
    ('P6 onTap 里不再 openApp', 'private void onTap() {' in j and j.split('private void onTap() {')[1].split('}')[0].find('openApp') < 0),
]
for n, v in checks:
    print(n, 'PASS' if v else 'FAIL')
print('SUMMARY', 'PASS' if all(v for _, v in checks) else 'FAIL')
raise SystemExit(0 if all(v for _, v in checks) else 1)
