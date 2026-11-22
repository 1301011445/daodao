import io,json
# 发版记录
p=r"F:\Daodao\发版记录.txt"
s=io.open(p,encoding="utf-8").read()
s=s.rstrip("\n")+"""

[2026-11-22 17:45] v0.109 手机端「点了歌没声、面板点不动退不出」根治 + 两端同步发页
- 用户截图（108）：三首列表都在，第三行显示「♪ 播放中」，实际无声，× 与行都点不动
- 根因三条：① 原生 decodePcm 一次解出 11MB short[] 才开播，低内存机 OOM；② 失败后页面走 assetB64/assetXhr，8MB base64 同步过桥把 JS 线程堵死；③ 开播前就把行标成「播放中」，成没成不回报
- DaoBridge 改边解边写：每帧 1028 字节解 2048 采样直接写 AudioTrack（内存几百 KB），先起 track 再回 OK；新增 songPos()/songDiag()；错误带码 NOFILE/HEADER/TRACK/WRITE/CATCH
- dao.html：行上显示真实进度「♪ 12.3 / 188 秒」；400ms 轮询，2.4 秒没往前走就标失败并附诊断（peak=0 说明解出来就是静音）；面板加「停止」按钮、点面板外可收、× 不再被盖；网页解码改 XHR 异步取包 + 每 240 帧让一次 UI，不再堵
- 包体：exe 9,933,824 B sha256_5f26f600fc32f933；apk 8,187,982 B sha256_0709d6e60b493711，versionCode=109/0.109，dex 98,252 B 含 decodeFrame/songPos/songDiag、无 decodePcm
- 短链：exe https://aka.doubaocdn.com/s/svHU9tJE00、apk https://aka.doubaocdn.com/s/AaawoSZsbC；两页已发 109（清单页 app_17hpue26uuw / 落地页 app_17jdxkgf27q）
- 云侧核验：线上包校验 PASS 5/5；两端自用体检 SELFTEST 17/17 PASS（报告 巡检报告\\两端自用_20261122_1742.md）
"""
io.open(p,"w",encoding="utf-8").write(s)
print("发版记录 ok")

# 待优化
p2=r"F:\Daodao\待优化.txt"
t=io.open(p2,encoding="utf-8").read()
t=t.replace("23. 原生 MediaPlayer 如果「成功但静音」（音量被调 0 或走了错音频流）页面没有任何办法知道；需要下一版加一次「播完是否真出过声」的自检或音量读取。",
            "23. [已办 0.109] 换成 AudioTrack 直推 + songPos/songDiag：2.4 秒没推进就判失败、peak=0 直接说「解出来是静音」，不再出现假的「播放中」。")
t=t.replace("20. apk 里 6.2MB 的 adp 是原样存储、解码后 PCM 常驻内存约 +10MB",
            "20. apk 里 6.2MB 的 adp 是原样存储；0.109 改成边解边写，PCM 不再常驻 11MB（内存这一项已解决，只剩包体大小可选做）")
io.open(p2,"w",encoding="utf-8").write(t)
print("待优化 ok")