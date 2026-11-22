# 2026-11-22 一次性：给问题库补 Q-094（手机浮窗只出包、没真机验过）
import io, json, datetime

P = r'F:\Daodao\自我状态\问题库.json'
d = json.load(io.open(P, encoding='utf-8'))
items = d['问题']
ids = [x['id'] for x in items]
print('count', len(items), 'max', max(ids, key=lambda s: int(s.split('-')[1])))

new = {
    "id": "Q-094",
    "标题": "手机端「在桌面上」浮窗只出了包，还没在真机上装过、看过",
    "来源": "用户反馈（手机端也要能直接在桌面显示）",
    "严重度": "P2",
    "状态": "open",
    "发现时间": "2026-11-22 18:20",
    "备注": "本轮没有 adb 设备，只能核对包内内容（DaoOverlay 类、SYSTEM_ALERT_WINDOW / FOREGROUND_SERVICE 权限、服务声明、btnDesk / ovPanel）和线上包字节；四种状态的观感、贴边位置、通知栏按钮都得等真机",
    "复现": "【人工】装 111 版 apk → 点底部「上桌面」→ 系统里允许「显示在其他应用上层」→ 选贴边偷看 → 按主页键：应看到半边身子贴在屏幕右边，点它回满身；选小圆球后点一下应弹回满身；打开「道」本体时浮窗应自己躲起来，退回桌面再出现；通知栏三个按钮（满身/贴边/球）都能用"
}

if any(x['id'] == 'Q-094' for x in items):
    print('Q-094 已存在，跳过')
else:
    items.append(new)
    json.dump(d, io.open(P, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('Q-094 appended, now', len(items))
