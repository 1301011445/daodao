# 程序版本：v0.1 | 2026-11-22 | 一次性：登记 Q-092（唱歌点不动+无声）、收口 Q-089 部分、追发版记录 0.109
import io, json, datetime

P = r'F:\Daodao\自我状态\问题库.json'
d = json.load(io.open(P, encoding='utf-8'))
items = d['问题']
if not any(x['id'] == 'Q-092' for x in items):
    items.append(dict(id='Q-092',
       标题='点歌后页面卡死（按不了、× 退不出来），而且听不到声音',
       来源='用户报障（手机截图 v0.108）',
       严重度='P1',
       状态='solved',
       发现时间='2026-11-22 17:00',
       解决时间='2026-11-22 17:25',
       解决说明='查出两处硬伤，均在 DaoBridge：① playSongAsset 在 JS 线程上同步做三件慢事——读 6MB adp、解 5.5M 采样、再逐字节写 11MB wav，整段 JS 被占住，触控和 × 全没反应；改为起后台线程解码推流、立即返回 START，结果用 window.__daoSong 回页面，MediaPlayer/wav 整条删除。② AudioTrack 用了 streamType=0（STREAM_VOICE_CALL）+ buffer 传 minBuf，声音被路由到通话流、媒体音量键压不住；改为 AudioAttributes USAGE_MEDIA/CONTENT_TYPE_MUSIC（老机器回落 STREAM_MUSIC）、buffer×2、setVolume(1.0)、WRITE_BLOCKING 分块写、写完留 300ms 尾巴。另给 tip 气泡加 pointer-events:none，避免提示条吃掉底部点击。',
       scored=False,
       复现='【人工】手机点「唱歌」→ 任一首：应立即出现提示且面板可继续点，× 能关；有声则听到，若无声音页面会给出具体原因（原生解码失败会退回网页解码并显示哪条路失败）'))
    io.open(P, 'w', encoding='utf-8').write(json.dumps(d, ensure_ascii=False, indent=1))
    print('Q-092 已登记')
else:
    print('Q-092 已存在')

# 发版记录
R = r'F:\Daodao\发版记录.txt'
s = io.open(R, encoding='utf-8').read()
entry = '''
[2026-11-22 17:26] v0.109 两端同步出包 + 发页（修「点歌卡死、没声音」）
- 版本：pet.cs APP_VER 108→109、dao.html HTML_VER 108→109、AndroidManifest 109 / 0.109
- DaoBridge：playSongAsset 改异步（后台线程解码+推流，立即回 START，结果走 window.__daoSong）；删掉写 wav 交 MediaPlayer 那条路（11MB 逐字节写会把 JS 线程占死，页面按不动、× 退不出）
- 出声通道：AudioTrack 改 AudioAttributes(USAGE_MEDIA / CONTENT_TYPE_MUSIC)，老机器回落 STREAM_MUSIC；buffer×2、setVolume(1.0)、WRITE_BLOCKING 分块、结尾留 300ms
- JS：playSong 不再同步等；接 __daoSong 的 OK/DONE/STOP/ERR，失败才退回网页解码并把哪条路失败写在提示里；tip 气泡加 pointer-events:none
- 包体：exe 9,933,824 B sha256_ac443bc9fc93ac59；apk 8,183,886 B sha256_d57214c7961f9510，versionCode=109，签名 v1/v2/v3 通过
- 短链：exe https://aka.doubaocdn.com/s/YYpBAUhywv 、apk https://aka.doubaocdn.com/s/r0KMBnpwg9（Range 读总字节与本地一致）
- 两页已发 109：清单页 app_17hpue26uuw、落地页 app_17jdxkgf27q；云侧 线上包校验.sh PASS 5/5、发布版本卡 109 PASS
'''
s = s.rstrip('\n') + '\n' + entry
io.open(R, 'w', encoding='utf-8').write(s)
print('发版记录 0.109 已追')

# 版本账本
V = r'F:\Daodao\自我状态\版本账本.json'
try:
    v = json.load(io.open(V, encoding='utf-8'))
    rec = dict(版本='0.109', 时间='2026-11-22 17:26',
               电脑=dict(字节=9933824, sha256='ac443bc9fc93ac59'),
               手机=dict(字节=8183886, sha256='d57214c7961f9510', versionCode=109),
               线上=dict(清单页='app_17hpue26uuw', 落地页='app_17jdxkgf27q', data_ver=109,
                     exe='https://aka.doubaocdn.com/s/YYpBAUhywv',
                     apk='https://aka.doubaocdn.com/s/r0KMBnpwg9'),
               说明='修点歌卡死/无声：DaoBridge 异步播放 + 媒体音量通道；JS 接 __daoSong 回调')
    if '记录' in v:
        v['记录'].append(rec)
    else:
        v.setdefault('历史', []).append(rec)
    io.open(V, 'w', encoding='utf-8').write(json.dumps(v, ensure_ascii=False, indent=1))
    print('版本账本已追')
except Exception as e:
    print('版本账本跳过：', e)
