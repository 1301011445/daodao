import io,re,base64,os
p=r'F:\Daodao\src\_apk\assets\dao.html'
src=io.open(p,encoding='utf-8').read()
out=r'F:\Daodao\_tmp_face\cloth'
os.makedirs(out,exist_ok=True)
def grab(name, start_marker, count, dq=True):
    i=src.find(start_marker)
    seg_end=src.find('];', i)
    seg=src[i:seg_end]
    if dq:
        pat=r'"data:image/(png|jpeg);base64,([^"]+)"'
    else:
        pat=r"'data:image/(png|jpeg);base64,([^']+)'"
    ms=re.findall(pat,seg)
    print(name,'start@',i,'imgs',len(ms))
    for k,(fmt,b64) in enumerate(ms):
        ext='png' if fmt=='png' else 'jpg'
        fn=os.path.join(out,f'{name}_{k}.{ext}')
        io.open(fn,'wb').write(base64.b64decode(b64))
        print('  ',fn,len(b64))
    return len(ms)
grab('FACES', 'var FACES = [', 14)
grab('POSES_7', 'var POSES_7 = [', 5)
grab('POSES', 'var POSES = [', 5)
grab('POSES_11', 'var POSES_11 = [', 5)
