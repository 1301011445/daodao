import io,re
p=r'F:\Daodao\src\_apk\assets\dao.html'
src=io.open(p,encoding='utf-8').read()
i=src.find('var FACES = [')
print('FACES 位置:', i)
seg=src[i:i+200000]
# 列出每个 data URI 的开头与长度
uris=[m for m in re.finditer(r"'data:image/(png|jpeg);base64,([^']+)'", seg)]
for k,m in enumerate(uris[:20]):
    print(k, m.group(1), len(m.group(2)))
print('总数(前 200k 内):', len(uris))
# 找 poseImgsBySp 定义附近
j=src.find('var poseImgsBySp')
print('pose 定义行区:', src[j-200:j+120].replace('\n','|')[:300])
