# -*- coding: utf-8 -*-
# 程序版本：v0.1 | 2026-11-22 | 基线建档（此前无版本头）
"""
触控热区体检（第 34 类判据落地）
判据来源：
  Apple HIG Buttons —— 触屏按钮命中区至少 44x44 pt，按钮之间要留够空隙
  Material Design Touch Target —— 48x48 dp，相邻目标 8dp 以上间距（指针 44dp）
  WCAG 2.5.5 Target Size (AAA) —— 44x44 CSS px；2.5.8 (AA) 最低 24x24

做法：把 dao.html 复制成 ASCII 临时文件，在 </body> 前插一段探针脚本，
点开记事本，量出所有可点元素的 rect，用无头 Edge --dump-dom 把结果读回来，
再用本脚本按判据打分。这样量的是浏览器真排出来的尺寸，不是猜 CSS。
"""
import json, os, re, shutil, subprocess, sys, tempfile

HTML = r"F:\Daodao\src\_apk\assets\dao.html"
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

PROBE = """
<script>
(function(){
  function measure(){
    var sel = 'button,[data-op],input[type=button],[role="button"],.mini,.chip,.tab,.row-act';
    var els = [].slice.call(document.querySelectorAll(sel));
    var out = [];
    els.forEach(function(e){
      var r = e.getBoundingClientRect();
      var cs = getComputedStyle(e);
      if (cs.display === 'none' || cs.visibility === 'hidden' || r.width === 0 || r.height === 0) return;
      out.push({tag:e.tagName, id:e.id||'', cls:(e.className||'').toString().slice(0,40),
                txt:(e.textContent||'').replace(/\\s+/g,' ').trim().slice(0,14),
                w:Math.round(r.width*10)/10, h:Math.round(r.height*10)/10,
                x:Math.round(r.x*10)/10, y:Math.round(r.y*10)/10, fs:cs.fontSize});
    });
    var pre = document.createElement('pre');
    pre.id = 'probeOut';
    var p = document.getElementById('notePanel'), l = document.getElementById('noteList');
    var diag = 'PANEL=' + (p ? (p.className + '|display=' + getComputedStyle(p).display) : 'null') +
               '|LISTCHILD=' + (l ? l.children.length : -1) +
               '|OPEN=' + (typeof noteOpen) + '|LS=' + (localStorage.getItem('dao_note_list') || '').length;
    pre.textContent = 'PROBE_JSON' + JSON.stringify(out) + 'PROBE_DIAG' + diag;
    document.body.appendChild(pre);
  }
  setTimeout(function(){
    try {
      // headless 里 localStorage 是空的，记事本会渲染成空清单，量不到 ✓/×。
      // 先塞三条假数据（不写回电脑），再打开面板。
      localStorage.setItem('dao_note_list', JSON.stringify([
        {id:'t1', text:'给母亲打电话', when:'2026-11-21 21:30', done:'0', rep:''},
        {id:'t2', text:'交期末试卷', when:'2026-11-22 09:00', done:'0', rep:''},
        {id:'t3', text:'交水电费', when:'2026-11-20 10:00', done:'1', rep:''}
      ]));
      if (typeof noteOpen === 'function') noteOpen();
      else {
        var nb = document.getElementById('btnNote');
        if (nb) {
          // 绑定的是 pointerdown，不是 click：点 btnNote 不会开面板
          try { nb.dispatchEvent(new PointerEvent('pointerdown', {bubbles:true, cancelable:true})); }
          catch(e2) { nb.dispatchEvent(new MouseEvent('mousedown', {bubbles:true})); }
        }
      }
    } catch(e){}
    setTimeout(measure, 500);
  }, 500);
})();
</script>
"""

def run_probe():
    tmp = os.path.join(tempfile.gettempdir(), "dao_touch_probe.html")
    with open(HTML, "r", encoding="utf-8") as f:
        src = f.read()
    src = src.replace("</body>", PROBE + "</body>")
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(src)
    cmd = [EDGE, "--headless=new", "--disable-gpu", "--hide-scrollbars",
           "--window-size=504,900", "--virtual-time-budget=5000",
           "--dump-dom", "file:///" + tmp.replace("\\", "/")]
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore", timeout=90)
    dom = p.stdout or ""
    m = re.search(r"PROBE_JSON(\[.*?\])PROBE_DIAG(.*?)</pre>", dom, re.S)
    if not m:
        print("PROBE_FAIL 探针没拿到数据，dom 长度=%d" % len(dom))
        return None
    print("探针诊断：" + m.group(2).strip().replace("\n", " "))
    return json.loads(m.group(1))

def gap_of(a, b):
    dx = max(b["x"] - (a["x"] + a["w"]), a["x"] - (b["x"] + b["w"]))
    dy = max(b["y"] - (a["y"] + a["h"]), a["y"] - (b["y"] + b["h"]))
    if dx <= 0 and dy <= 0:
        return -1.0   # 有重叠
    return max(dx, dy)

def main():
    els = run_probe()
    if not els:
        print("FAIL|P0|探针失败")
        return 2
    print("量的可点元素：%d 个" % len(els))
    for e in els:
        print("  %-8s %-12s %-14s %6.1fx%-6.1f  %s" % (e["tag"], e["id"] or "-", e["cls"][:14], e["w"], e["h"], e["txt"]))

    fails = 0
    results = []

    # P1 每个可点元素都 >= 24x24（WCAG 2.5.8 AA）
    small = [e for e in els if min(e["w"], e["h"]) < 24]
    ok1 = len(small) == 0
    results.append(("P1 单目标≥24x24(WCAG2.5.8)", ok1, "%d/%d 小于24" % (len(small), len(els)),
                    [("", e["txt"], e["w"], e["h"]) for e in small]))
    # P2 主按钮（.mini / btn 开头）高度 >= 44（WCAG 2.5.5 / Apple HIG）
    mainbtn = [e for e in els if ("mini" in e["cls"]) or e["id"].startswith("btn")]
    bad2 = [e for e in mainbtn if min(e["w"], e["h"]) < 44]
    ok2 = len(bad2) == 0
    results.append(("P2 主按钮≥44x44(2.5.5/Apple)", ok2, "%d/%d 小于44" % (len(bad2), len(mainbtn)),
                    [("", e["txt"], e["w"], e["h"]) for e in bad2]))
    # P3 行内小动作（✓/× 之类，text 是 ✓ × 的）≥32x32
    act = [e for e in els if e["txt"] in ("✓", "×", "✕", "x", "X")]
    bad3 = [e for e in act if min(e["w"], e["h"]) < 32]
    ok3 = len(bad3) == 0
    results.append(("P3 行内✓/×≥32x32", ok3, "%d/%d 小于32" % (len(bad3), len(act)),
                    [("", e["txt"], e["w"], e["h"]) for e in bad3]))
    # P4 相邻可点元素间距 >= 8（Material）
    mingap = 999.0
    for i in range(len(els)):
        for j in range(i + 1, len(els)):
            g = gap_of(els[i], els[j])
            if 0 <= g < mingap:
                mingap = g
    ok4 = mingap >= 8.0
    results.append(("P4 相邻间距≥8dp(Material)", ok4, "最小间距 %.1f" % mingap, []))
    # P5 可点元素数量 >= 6 且没有 0 尺寸的漏网
    ok5 = len(els) >= 6
    results.append(("P5 可点元素≥6个", ok5, "共 %d 个" % len(els), []))

    print("\n判据：")
    for name, ok, num, detail in results:
        print(("PASS" if ok else "FAIL") + " | " + name + " | " + num)
        if not ok:
            fails += 1
            for d in detail[:8]:
                print("       {0} w={1} h={2}".format(d[1], d[2], d[3]))
    print("\n汇总：%d/%d 通过，%d 项 FAIL" % (len(results) - fails, len(results), fails))
    return 0 if fails == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
