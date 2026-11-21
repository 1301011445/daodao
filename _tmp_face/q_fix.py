import io, json, importlib.util
db=r'F:\Daodao\自我状态\问题库.json'
d=json.load(io.open(db,encoding='utf-8'))
for i in d['问题']:
    if i.get('id')=='Q-059':
        i['标题']='手机端长按「跟它说话」报 openAsk is not defined（打字入口失效）'
        i['来源']='用户截图（v0.86 手机端）'
        i['严重度']='P0'
        i['说明']='dao.html 两块脚本作用域隔离，第2块调用了第1块私有函数 openAsk/askInput/askMode'
s=importlib.util.spec_from_file_location('qk', r'F:\Daodao\tools\问题库.py')
m=importlib.util.module_from_spec(s); s.loader.exec_module(m)
m.save(d)
print('修复后:', [x for x in d['问题'] if x.get('id')=='Q-059'])
print('close:', m.close('Q-059', '已显式开放 window.daoAskSide/daoAskOpen 等入口，第2块改走入口；v0.87 已编译并发布，两页线上 87'))
print('最终:', [x for x in json.load(io.open(db,encoding='utf-8'))['问题'] if x.get('id')=='Q-059'])

# 账本按原结构重写
led=r'F:\Daodao\自我状态\版本账本.json'
j={
 '真用':{
   '电脑':{'最后':'2026-11-21 10:55','版本':'87','证据':'进程 道.exe /ping 回 OK|道|87'},
   '手机':{'最后':'2026-11-20 20:45:15','版本':'78','证据':'手机自检.txt 最后一行（v0.87 待真机安装）'}
 },
 '已结算':{},
 '检测':{'时间':'2026-11-21 10:58','电脑':'87','apk':'87','页面':'87','线上':'87','手机':'78',
        '手机上报时间':'2026-11-20 20:45:15','一致':True,'落后':{'手机':0,'页面':0}}
}
io.open(led,'w',encoding='utf-8').write(json.dumps(j,ensure_ascii=False,indent=2))
print('账本:', json.dumps(j,ensure_ascii=False))
