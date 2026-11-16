from datetime import datetime
root = r'F:\Daodao'
now = datetime.now().strftime('%Y-%m-%d %H:%M')

# 1) 同步日志
log = root + r'\同步日志.txt'
entry = f"""
【{now} 形象扩容 v44】
- 新增两只人形形象：face_12 白衫少年、face_13 青衫少女（手办质感、五官清楚，脸上没有腮红贴片/十字怒纹/泪滴，情绪只能靠眉眼嘴）
- 手机端 dao.html 的 FACES 从 12 张增到 14 张；上轮遗留的版本牌问题一并修掉：HTML_VER 38 -> 44
- 电脑端 _bundle 111 -> 113 个文件，exe 13,592,576 字节 13.6MB，ping 回 OK|道|44
- 手机端 Dao.apk 3,841,891 字节 3.66MB，versionCode 44 / versionName 44.0，签名 v1/v2/v3 全 true
- 线上：下载页 app_17hnj8acgs2 与清单页 app_17hpue26uuw 都发布 finished，data-ver 44，体积 13.6MB / 3.7MB
- 没做：新形象还没有 pose（站/打招呼/走路/欢呼/坐）与表情帧，桌上只会静态站着
"""
with open(log, 'a', encoding='utf-8') as f:
    f.write(entry)

# 2) 经验库
exp = root + r'\经验库.md'
exp_entry = f"""
## {now[:10]} 形象扩容：白底转透明与打包目录卫生

标签：#形象 #素材 #打包

- 生图默认就是白底不透明——哪怕提示词里写了「透明背景生成」，出图角点 alpha 仍是 255。要 alpha 必须出图后自己处理。
- GDI+ 直接对 24bpp 原图 LockBits 成 Format32bppArgb 改 alpha **不会生效**（写回后角点仍是 255）。正确顺序：先用 Graphics 以 SourceCopy 把原图画进一张新建的 Format32bppArgb 位图，再对这张锁位图。
- 抠白底用「从四条边泛洪 + 容差」而不是「全图按亮度阈值删」。后者会把白衬衫、白鞋一起打穿；泛洪只吃与边界连通的近白像素，人物内部的白衣服被轮廓包着，不连通就保住了。
- 泛洪之后还要补一刀：紧邻背景、且最小通道 >190 的前景像素直接置透明，否则抗锯齿边缘留一圈白边。
- 打包目录里别放 .bak：_apk\\assets 下留了一份 dao.html.v43.bak，apk 立刻从 3.66MB 涨到 5.93MB。备份挪出打包目录。
- 本机 pwsh 是 PowerShell 10，Add-Type 编译 System.Drawing 代码会缺 System.Private.Windows.GdiPlus/Core 引用；改用系统 Windows PowerShell 5.1 跑同一段代码即可，但 5.1 按 ANSI 读脚本，脚本里带中文路径会乱码——让 5.1 只处理纯英文路径，中文路径的搬运用新版 shell 做。
"""
with open(exp, 'a', encoding='utf-8') as f:
    f.write(exp_entry)

# 3) 待优化：形象池上限这条
todo = root + r'\待优化.txt'
txt = open(todo, encoding='utf-8').read()
old_kw = '形象池上限仍是 12'
if old_kw in txt:
    line_idx = None
    lines = txt.split('\n')
    for i, l in enumerate(lines):
        if old_kw in l:
            line_idx = i
            break
    if line_idx is not None:
        parts = lines[line_idx].split('|')
        if len(parts) >= 5:
            parts[2] = '中'
            parts[3] = '已解决(2026-11-16)'
            parts[4] = ('LoadFaces 本来就循环 face_0..face_63，加图即自动扩容：现 14 只'
                        '（新增 face_12 白衫少年 / face_13 青衫少女，names.txt 已补 13/14 行）。'
                        '剩下的是给新形象补 pose（站/打招呼/走路/欢呼/坐）与 expr 表情帧，以及 dao.html 的 WALKS/POSES 数组。')
            lines[line_idx] = '|'.join(parts)
        txt = '\n'.join(lines)
        open(todo, 'w', encoding='utf-8').write(txt)
        print('待优化 第3项 已标为已解决')
else:
    print('待优化 没找到那条，跳过')

print('同步日志 追加完成')
print('经验库 追加完成')
