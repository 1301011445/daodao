import io,json
# 发版记录
p=r"F:\Daodao\发版记录.txt"
s=io.open(p,encoding="utf-8").read().rstrip("\n")+"""

[2026-11-22 18:08] v0.110 桌面端四种待法（贴边偷看 / 悬浮球 / 收起）+ 干活时自动贴边
- 用户要求：在别的窗口干活时，它可以在屏幕侧边只露半边（像乔巴探头），也可以缩成悬浮球，点一下再出来；要有多种模式
- 新增 右键「桌面 → 我在桌面上的样子」：满身 / 贴边偷看 / 缩成悬浮球 / 收起（只在托盘）；另有「干活时自己去边上偷看」「换一边（左/右）」
- 偷看：窗口中心压在屏幕边上，正好切掉一半身子；鼠标过来整只滑出，移开自动缩回；点一下就回满身
- 悬浮球：72 像素圆球（渐变+眨眼+笑弧），贴边停靠，点一下弹回满身；收起后托盘图标可唤回/退出
- 自动：GetForegroundWindow 轮询 900ms，前台不是自己就贴边，回到桌面或回到它身上就回原位；拖拽时不触发
- 选择记住：HKCU\\Software\\DaoPet 的 PetMode / PeekSide / AutoPeek
- 实测踩坑并修：第一版按「露出窗口宽 34%」定位，露的其实是窗口左侧空白，屏幕上看不到人；改成窗口中心压边才真的露半边（已验证 悬浮球 108px 圆、偷看窗口中心落在屏幕边）
- 包体：exe 9,940,480 B sha256_49819f7388df78c9；apk 8,187,982 B versionCode=110（页面只升版号，播放修复沿用 109）
- 短链：exe s/vBI6IqOIMZ、apk s/PiLlNPZVt1；两页已发 110；云侧 线上包校验 PASS 5/5、发布版本卡 PASS
"""
io.open(p,"w",encoding="utf-8").write(s)
print("发版记录 ok")

# 经验库
p3=r"F:\Daodao\经验库.md"
e=io.open(p3,encoding="utf-8").read()
add="""
## 2026-11-22 · 桌面宠物「贴边偷看」怎么定位才看得见
- 人物画在窗口正中，想让屏幕边缘切掉半身，要让**窗口中心**压在屏幕边上（x = 边 - W/2），不是按窗口宽度露出三成——那样露出来的是窗口左边的空白，屏幕上什么都没有。
- 验证分层透明窗口（TransparencyKey）不要用 PrintWindow 直接看，它会把透明区域渲染成黑色；看「圆球/边框那些不透明像素在不在」就够了，或者用 --dump 让 PaintAll 直接出图。
- 沙盒截图与真实屏幕可能是两套坐标（DPI/会话不同），据窗口 GetWindowRect 与 Screen 尺寸对不上时要先怀疑这一点。
"""
if "贴边偷看」怎么定位" not in e:
    e=e.rstrip("\n")+"\n"+add
    io.open(p3,"w",encoding="utf-8").write(e)
print("经验库 ok")

# 问题库：登记本轮自捕的定位坑（已解决）
p2=r"F:\Daodao\自我状态\问题库.json"
d=json.load(io.open(p2,encoding="utf-8"))
items=d if isinstance(d,list) else d.get("问题",d.get("items",[]))
ids=[x.get("id") for x in items]
if "Q-093" not in ids:
    items.append({"id":"Q-093","标题":"贴边偷看第一版定位错，屏幕上露出来的是窗口空白而不是半个人","来源":"自测（0.110 出包前）","严重度":"P2","状态":"solved","发现时间":"2026-11-22 17:55","解决时间":"2026-11-22 18:00","解决说明":"原按『露出窗口宽 34%』把窗口右侧推到屏幕外，但人物居中，屏幕里留下的是窗口左侧空白。改为窗口中心压在屏幕边上（右：x=Right-W/2，左：x=Left-W/2），屏幕正好切掉一半身子；滑出/缩回的坐标同步改。","scored":False,"复现":"【人工】右键 桌面→我在桌面上的样子→贴边偷看：屏幕右边缘应能看到半个人；鼠标移过去整只滑出，移开缩回"})
    io.open(p2,"w",encoding="utf-8").write(json.dumps(d,ensure_ascii=False,indent=1))
print("问题库 ok, 共",len(items))