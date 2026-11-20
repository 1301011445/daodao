# -*- coding: utf-8 -*-
"""词曲对比体检（第29类配套）：导入两首歌的生成脚本，取 build() 的逐句元数据，
量 ① 曲的段落对比（主歌 vs 副歌：音高均值差、句长差）
② 词的对比（字句长短、末字押韵、重复句、具象词/抽象词）。
不重渲音频，只读结构。
"""
import sys, os, json, io, importlib.util, statistics

SONGS = [
    (r'F:\Daodao\tools\音乐\故乡歌\故乡歌.py', '归途的月光'),
    (r'F:\Daodao\tools\音乐\打工人歌\打工人歌.py', '把好日子扛在肩上'),
]

ABSTRACT = ['想', '念', '梦', '希望', '未来', '坚持', '努力', '奋斗', '梦想', '远方', '心里', '勇气', '信念']
CONCRETE_MARK = ['树', '烟', '月', '汤', '门', '路', '碗', '筷', '灯', '窗', '雨', '雪', '站', '车', '脚', '手', '田', '桥', '井', '巷']

def load(path):
    spec = importlib.util.spec_from_file_location('song_%d' % abs(hash(path)), path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m

def analyze(path, name):
    m = load(path)
    notes, mel, secs = m.build()
    verse = [x for x in mel if not x['chorus']]
    chorus = [x for x in mel if x['chorus']]
    def avg_base(items):
        return round(statistics.mean([x['base'] for x in items]), 2) if items else None
    def avg_len(items):
        return round(statistics.mean([len(x['text']) for x in items]), 2) if items else None
    # 押韵：句末字相同的比例（对汉语是粗粒度，但比"感觉押韵"强）
    ends = [x['text'][-1] for x in mel if x['text']]
    rhyme_ratio = round(sum(1 for e in ends if ends.count(e) > 1) / len(ends), 3) if ends else 0
    # 重复句
    texts = [x['text'] for x in mel if x['text']]
    dup = len(texts) - len(set(texts))
    # 具象/抽象词
    allt = ''.join(texts)
    conc = sum(allt.count(w) for w in CONCRETE_MARK)
    abst = sum(allt.count(w) for w in ABSTRACT)
    res = {
        '歌名': name,
        '句数': len(texts),
        '主歌平均字数': avg_len(verse),
        '副歌平均字数': avg_len(chorus),
        '主歌音高均值': avg_base(verse),
        '副歌音高均值': avg_base(chorus),
        '音高提升半音': (round(avg_base(chorus) - avg_base(verse), 2)
                     if verse and chorus else None),
        '句末字重复率': rhyme_ratio,
        '重复句数': dup,
        '具象词': conc,
        '抽象词': abst,
        '段落数': len(secs),
    }
    # 判据
    lift = res['音高提升半音']
    res['C1_副歌音高抬升'] = 'PASS' if lift is not None and lift >= 1.5 else 'FAIL'
    res['C2_副歌句比主歌短或等长'] = ('PASS' if res['副歌平均字数'] is not None and res['主歌平均字数'] is not None
                              and res['副歌平均字数'] <= res['主歌平均字数'] + 0.5 else 'FAIL')
    res['C3_末字押韵'] = 'PASS' if rhyme_ratio >= 0.5 else 'FAIL'
    res['C4_重复句'] = 'PASS' if dup >= 2 else 'FAIL'
    res['C5_具象词多于抽象词'] = 'PASS' if conc > abst else 'FAIL'
    return res

def main():
    out = []
    for p, n in SONGS:
        if not os.path.exists(p):
            print('缺文件', p); continue
        out.append(analyze(p, n))
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), '词曲对比.json')
    io.open(p, 'w', encoding='utf-8').write(json.dumps(out, ensure_ascii=False, indent=2))
    for r in out:
        fails = [k for k in r if k.startswith('C') and r[k] == 'FAIL']
        print('%s | 主歌%s字/副歌%s字 | 音高 %s→%s（%+.2f） | 押韵%.2f | 重复句%d | 具象%d/抽象%d | %s'
              % (r['歌名'], r['主歌平均字数'], r['副歌平均字数'], r['主歌音高均值'], r['副歌音高均值'],
                 r['音高提升半音'], r['句末字重复率'], r['重复句数'], r['具象词'], r['抽象词'],
                 ('待改 ' + ','.join(f[:2] for f in fails)) if fails else '全过'))
    print('写入', p)

if __name__ == '__main__':
    main()
