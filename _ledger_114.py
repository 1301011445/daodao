import json, io
p = r'F:\Daodao\自我状态\版本账本.json'
d = json.load(io.open(p, encoding='utf-8'))
d['历史'].append({
    "版本": "1.14", "时间": "2026-11-23 13:59",
    "电脑": {"字节": 9949184, "sha256": "624ee46d51caaa15"},
    "手机": {"字节": 13054490, "sha256": "e5212b6b1ef90258", "versionCode": 114},
    "线上": {"清单页": "app_17hpue26uuw", "落地页": "app_17jdxkgf27q", "data_ver": 114,
             "exe": "https://aka.doubaocdn.com/s/iawt24zMmZ",
             "apk": "https://aka.doubaocdn.com/s/OZIeZGhMsA"},
    "说明": "v114：修手机端浮窗画面扭曲——drawWarp 头部侧倾改按头宽(0.35w×0.45)计算并 ±0.05w 封顶；挥手位移按 0.022w / 0.030h 像素封顶（原 0.055w/0.075h 在 180px 高的小立绘下会把手臂抻长、手折到脸边）"
})
d['真用']['电脑'] = {"最后": "2026-11-23 13:59", "版本": "114",
                     "证据": "F:\\Daodao\\道.exe 9,949,184 B（进程待重启生效）"}
json.dump(d, io.open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print("账本 历史条数", len(d['历史']))
