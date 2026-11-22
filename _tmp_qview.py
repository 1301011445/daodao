import io,json
p=r"F:\Daodao\自我状态\问题库.json"
d=json.load(io.open(p,encoding="utf-8"))
items=d if isinstance(d,list) else d.get("问题",d.get("items",[]))
ids=[x.get("id") for x in items]
print("count",len(items),"has Q-092","Q-092" in ids,"Q-091" in ids)
print(json.dumps(items[-1],ensure_ascii=False)[:600])
print(json.dumps([x for x in items if x.get("id")=="Q-089"],ensure_ascii=False)[:600])