# -*- coding: utf-8 -*-
import os, importlib.util
from importlib.util import spec_from_file_location, module_from_spec
p=r'F:\Daodao\tools\音乐\前奏钩子\前奏钩子检查.py'
s=spec_from_file_location('hook',p); h=module_from_spec(s); s.loader.exec_module(h)

def measure(path):
    fmt,div,tr=h.read_mid(path)
    ons=[]
    for t in tr:
        ev,_=h.parse_track(t)
        for x in ev:
            if x[0]=='on': ons.append((x[1],x[2],x[3]))
    chans={}
    for tick,ch,n in ons:
        if ch!=9: chans.setdefault(ch,[]).append(n)
    cand=[c for c,v in chans.items() if len(v)>=30 and (max(v)-min(v))<=20]
    mel=min(cand) if cand else max(chans,key=lambda c:len(chans[c]))
    # 和弦起音分组
    grp={}
    for tick,ch,n in ons:
        if ch!=mel and ch!=9: grp.setdefault(tick,set()).add(n%12)
    starts=sorted(t for t,pcs in grp.items() if len(pcs)>=2)
    def chord_at(tick):
        cur=None
        for st in starts:
            if st<=tick: cur=grp[st]
            else: break
        return cur
    melnotes=sorted([(tick,n) for tick,ch,n in ons if ch==mel])
    strong=[0,0]; weak=[0,0]
    for tick,n in melnotes:
        pcs=chord_at(tick)
        if not pcs: continue
        hit=(n%12) in pcs
        # 强拍：拍内位置为偶数拍（(tick/div) % 2 == 0）
        b=(tick/float(div))%2
        is_strong = abs(b)<1e-6 or abs(b-1)<1e-6
        box = strong if is_strong else weak
        box[0]+=1; box[1]+= 1 if hit else 0
    tot_s=strong[0]; tot_w=weak[0]
    print('%-34s 全音 %5.1f%% (%d/%d) | 强拍 %5.1f%% (%d/%d) | 弱拍 %5.1f%% (%d/%d)'
          % (os.path.basename(path), 100.0*(strong[1]+weak[1])/(tot_s+tot_w), strong[1]+weak[1], tot_s+tot_w,
             100.0*strong[1]/max(1,tot_s), strong[1], tot_s, 100.0*weak[1]/max(1,tot_w), weak[1], tot_w))

for f in [r'F:\Daodao\tools\音乐\故乡歌\out\归途的月光.mid',
          r'F:\Daodao\tools\音乐\旋律体检\归途的月光_改和声.mid',
          r'F:\Daodao\tools\音乐\旋律体检\归途的月光_和弦骨架.mid',
          r'F:\Daodao\tools\音乐\打工人歌\out\把好日子扛在肩上.mid']:
    measure(f)
