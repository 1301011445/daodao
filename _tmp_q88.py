# 程序版本：v0.1 | 2026-11-22 | 一次性：补登 Q-088/Q-089 到问题库
import json, io

P = r'F:\Daodao\自我状态\问题库.json'
d = json.load(io.open(P, encoding='utf-8'))
cur = [q['id'] for q in d['问题']]

new = [
 dict(id='Q-088', 标题='apk 打包静默产出没有 classes.dex 的假包（7z 收尾改名失败、脚本不查退出码）',
      来源='构建链路自查', 严重度='P1', 状态='solved',
      发现时间='2026-11-22 13:35', 解决时间='2026-11-22 13:42',
      解决说明='7z 往 base.apk 塞 dex 时改名 base.apk.tmp1→base.apk 失败（目标被占用），脚本不看 $LASTEXITCODE 继续 zipalign/签名，得到 9.35MB 无 dex 的包；另把 assets 下的 dao.html 备份也打了进去。处置：新写 tools\\add_dex.py 用 zipfile 重写并自检，build.ps1 加 add_dex exit 硬校验 + obj/dex/gen 被占用时换时间戳新目录（绝不复用旧产物）。现包 8,179,790B、dex 里有 assetXhr/playPcm/AudioTrack、无 adpToWav、无 .bak 条目',
      scored=True,
      复现='【人工】跑 build.ps1 后：python -c "import zipfile;z=zipfile.ZipFile(r\'F:\\Daodao\\道.apk\');print(\'classes.dex\' in z.namelist())" 应为 True；解压看 assets 下无 .bak'),
 dict(id='Q-089', 标题='手机端点「唱歌」提示拿不到曲库文件 / 没声音（曲库 adp 在包里、解码器两端验证正常）',
      来源='用户反馈', 严重度='P1', 状态='open',
      发现时间='2026-11-22 12:10', 解决时间='',
      解决说明='已排：assets 内 3 个 adp 均在包（guitu 2025 帧/22050Hz）、JS 与 Java 解码逐点一致（188.03s、峰值 0.8965）、dex 里桥接方法齐全；故障只可能在读取/播放入口。已改 DaoBridge 为 MediaPlayer→AudioTrack 双引擎 + assetXhr 带异常原因，dao.html 同步重写并把失败原因显示到屏幕。待装新包装机看提示定位',
      scored=False,
      复现='【人工】手机装 F:\\Daodao\\道.apk → 点「唱歌」→ 选《归途》：应出声；若还不出，屏幕会显示 放不了：xxx；也读不到 assets/music/guitu.adp 之类具体原因'),
]

for q in new:
    if q['id'] not in cur:
        d['问题'].append(q)
        print('追加', q['id'])

io.open(P, 'w', encoding='utf-8').write(json.dumps(d, ensure_ascii=False, indent=1))
from collections import Counter
print('总数', len(d['问题']), Counter(x['状态'] for x in d['问题']))
