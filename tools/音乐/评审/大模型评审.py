# -*- coding: utf-8 -*-
# 大模型评审.py | 2026-11-24 | 用 glm-4-flash 当「审听」：客观指标 → 分项打分 + 可执行改法（JSON）
"""用法：python 大模型评审.py <曲名> <伴奏wav> <人声wav> <成品wav> <时间轴json>
产出：out/评审_<曲名>.json（分数 + 维度 + 改法清单）"""
import io, json, os, sys, urllib.request, urllib.error
import numpy as np
import soundfile as sf

ROOT = r"F:\Daodao"
KEY = io.open(os.path.join(ROOT, 'key.txt'), encoding='utf-8').read().strip()
API = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
MODELS = ["glm-4-flash", "glm-4.7-flash", "glm-4-air"]   # 429 依次退
HERE = os.path.dirname(os.path.abspath(__file__))
SR = 22050


def load(p, sr=SR):
    x, s = sf.read(p, dtype='float64')
    if x.ndim > 1:
        x = x.mean(axis=1)
    if s != sr:
        x = np.interp(np.linspace(0, len(x) - 1, int(len(x) * sr / s)), np.arange(len(x)), x)
    return x


def feats(inst_p, voc_p, mix_p, tl_p, bpm):
    v, i, m = load(voc_p), load(inst_p), load(mix_p)
    it = json.load(io.open(tl_p, encoding='utf-8'))
    lines = []
    for x in it:
        if not lines or lines[-1][0] != x['line']:
            lines.append([x['line'], []])
        lines[-1][1].append(x)
    n_v = np.pad(v, (0, max(0, len(i) - len(v)))); i = np.pad(i, (0, max(0, len(v) - len(i))))
    vr = np.sqrt(np.mean(n_v ** 2)) + 1e-12
    ir = np.sqrt(np.mean(i ** 2)) + 1e-12
    midi = [x['midi'] for x in it]
    ups = downs = leaps = 0
    for li, (_, its) in enumerate(lines):
        seg = [x['midi'] for x in its]
        for a, b in zip(seg, seg[1:]):
            d = b - a
            if d >= 5 or d <= -5:
                leaps += 1
            if d > 0:
                ups += 1
            elif d < 0:
                downs += 1
    tails = [its[-1]['midi'] - its[0]['midi'] for _, its in lines]
    # 段间空窗（相邻句间隔）
    gaps = []
    for k in range(len(lines) - 1):
        a = lines[k][1][-1]; b = lines[k + 1][1][0]
        gaps.append(round(b['t'] - (a['t'] + a['dur']), 1))
    dur = max(x['t'] + x['dur'] for x in it)
    # 人声/伴奏按段比
    seg_ratio = []
    for a in range(0, int(min(len(v), len(i)) / SR) - 5, 10):
        blk_v = np.sqrt(np.mean(v[int(a * SR):int((a + 5) * SR)] ** 2))
        blk_i = np.sqrt(np.mean(i[int(a * SR):int((a + 5) * SR)] ** 2)) * 0.85
        if blk_v > 1e-4 and blk_i > 1e-4:
            seg_ratio.append(round(20 * np.log10(blk_v / blk_i), 1))
    return dict(
        曲长秒=round(dur, 1), BPM=bpm, 句数=len(lines), 每句字数=len(it) // max(1, len(lines)),
        音区=[min(midi), max(midi)], 半音跨度=max(midi) - min(midi),
        上行次数=ups, 下行次数=downs, 上行占比=round(100.0 * ups / max(1, ups + downs), 1),
        五度以上大跳次数=leaps,
        句尾净升降=[round(t, 1) for t in tails],
        最长句间空窗秒=max(gaps) if gaps else 0, 句间空窗=gaps,
        人声轨RMS=round(float(vr), 4), 伴奏轨RMS=round(float(ir), 4),
        人声比伴奏dB=round(float(20 * np.log10(vr / (ir * 0.85))), 1),
        分段人声比伴奏dB=seg_ratio[:12],
        成品LUFS=None, 成品峰值=None,
        音色分配='主歌自然声 / 副歌少年声' if True else '')


def ask(prompt, model):
    req = urllib.request.Request(
        API, data=json.dumps({"model": model, "messages": [
            {"role": "system", "content": "你是资深音乐制作人，给「道」的原创歌曲做审听。只依据给定客观数据判断，"
                                         "不许编造听到的东西；输出严格 JSON，不要多余文字。"},
            {"role": "user", "content": prompt}], "temperature": 0.3, "max_tokens": 1800}).encode(),
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + KEY})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode("utf-8"))["choices"][0]["message"]["content"]


def main():
    name = sys.argv[1] if len(sys.argv) > 1 else '积极版'
    inst, voc, mix = sys.argv[2], sys.argv[3], sys.argv[4]
    tl = sys.argv[5]
    bpm = float(sys.argv[6]) if len(sys.argv) > 6 else 122.0
    f = feats(inst, voc, mix, tl, bpm)
    # 成品响度来自响度体检.json（最近一次）
    try:
        j = json.load(io.open(os.path.join(ROOT, r'tools\音频\响度体检.json'), encoding='utf-8'))
        row = j[0] if isinstance(j, list) else j
        f['成品LUFS'] = row.get('LUFS'); f['成品峰值'] = row.get('dBTP')
    except Exception as e:
        print('响度读取失败', e)
    prompt = ("这首歌用户已经骂过两次「难听」，现在要求：曲调积极、人声不能被伴奏压住。客观指标如下，"
              "请按 旋律积极性/人声可听度/音色自然度/结构节奏/情绪统一 五个维度各打 0-20 分（合计100），"
              "然后给出 4 条「能直接改参数就落地」的改法，每条写清 项/为什么/具体数值。\n"
              "输出 JSON：{\"总分\":int,\"维度\":{\"旋律积极性\":int,\"人声可听度\":int,\"音色自然度\":int,\"结构节奏\":int,\"情绪统一\":int},"
              "\"诊断\":[str,str,str],\"改法\":[{\"项\":str,\"为什么\":str,\"参数\":str}]}\n\n指标：\n"
              + json.dumps(f, ensure_ascii=False))
    out = None
    for mdl in MODELS:
        try:
            out = ask(prompt, mdl)
            print('模型', mdl, '成功')
            break
        except urllib.error.HTTPError as e:
            print('模型', mdl, 'HTTP', e.code)
            if e.code != 429:
                raise
        except Exception as e:
            print('模型', mdl, '失败', e)
    if out is None:
        raise SystemExit('三个模型都没通')
    out = out.strip().strip('`').replace('json\n', '')
    io.open(os.path.join(HERE, 'out', '评审_%s.json' % name), 'w', encoding='utf-8').write(out)
    print(out)


if __name__ == '__main__':
    sys.exit(main())
