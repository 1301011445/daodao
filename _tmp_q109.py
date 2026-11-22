import io,json,datetime
p=r"F:\Daodao\自我状态\问题库.json"
d=json.load(io.open(p,encoding="utf-8"))
items=d if isinstance(d,list) else d.get("问题",d.get("items",[]))
for x in items:
    if x.get("id")=="Q-092":
        x["解决说明"]=x.get("解决说明","")+"｜17:45 二轮：decodePcm 整段 11MB 改边解边写（每帧 2048 采样）、失败不再走 8MB base64 同步过桥（改 XHR 异步 + 每 240 帧让一次 UI）、行上显示真实进度、2.4s 不推进即判失败（songPos/songDiag），0.109 已两端出包并发布。"
        x["解决时间"]="2026-11-22 17:45"
    if x.get("id")=="Q-089":
        x["解决说明"]=x.get("解决说明","")+"｜0.109 已把「真写进去多少采样」暴露给页面（songPos/songDiag）：装 0.109 后再点歌，屏幕上会显示 ♪ 12.3/188 秒或具体失败码，据此可一次定位。"
io.open(p,"w",encoding="utf-8").write(json.dumps(d,ensure_ascii=False,indent=1))
print("问题库 ok")