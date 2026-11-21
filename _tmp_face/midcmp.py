import sys, os
from importlib.util import spec_from_file_location, module_from_spec
p=r'F:\Daodao\tools\音乐\前奏钩子\前奏钩子检查.py'
s=spec_from_file_location('hook',p); h=module_from_spec(s); s.loader.exec_module(h)
for f in [r'F:\Daodao\tools\音乐\故乡歌\out\归途的月光.mid', r'F:\Daodao\tools\音乐\故乡歌\out\归途的月光_和弦修正.mid']:
    print('###', os.path.basename(f), os.path.getsize(f))
    fmt,div,tr=h.read_mid(f)
    print(' fmt',fmt,'div',div,'tracks',len(tr))
    chans={}
    for i,t in enumerate(tr):
        ev,tp=h.parse_track(t)
        for x in ev:
            if x[0]=='on': chans.setdefault((x[2],i),[]).append((x[1],x[3]))
    for k in sorted(chans):
        v=chans[k]
        print('  ch%d tr%d n=%d first=%s' % (k[0],k[1],len(v),v[:6]))
