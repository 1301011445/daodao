import sys, importlib.util, io, json
p=r'F:\Daodao\tools\问题库.py'
s=importlib.util.spec_from_file_location('qk',p); m=importlib.util.module_from_spec(s); s.loader.exec_module(m)
db=r'F:\Daodao\自我状态\问题库.json'
data=json.load(io.open(db,encoding='utf-8'))
items=data['问题'] if isinstance(data,dict) and '问题' in data else data
hit=[x for x in items if 'openAsk' in str(x.get('标题',''))]
if hit:
    print('已存在:', hit[0].get('编号'), hit[0].get('状态'))
    qid=hit[0].get('编号')
else:
    r=m.register('手机端长按「跟它说话」报 openAsk is not defined（打字入口失效）','P0',
                 ['q'], ['dao.html 两块脚本作用域隔离，第2块调用了第1块私有函数'])
    print('登记:', r)
    qid=r.get('编号') if isinstance(r,dict) else None
try:
    print('关闭:', m.close(qid, '已显式开放 window.daoAskSide/daoAskOpen，第2块改走入口；v0.87 已编译发布'))
except Exception as e:
    print('关闭失败:', e)
