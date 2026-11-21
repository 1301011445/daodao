import io
p = r"F:\Daodao\src\_apk\assets\dao.html"
s = io.open(p, encoding="utf-8", errors="replace").read()
inj = """<div id="dbgout" style="position:fixed;left:0;bottom:0;z-index:9999;color:#0f0;font:11px monospace;background:#000;max-width:100%;white-space:pre-wrap"></div>
<script>
window.__E=[];window.onerror=function(m,s,l,c,e){window.__E.push((m||'ERR')+' @'+l+':'+c);return false;};
window.__F={tr:[],sc:[],sv:0,rs:0,te:0};
(function(){var P=CanvasRenderingContext2D.prototype,ot=P.translate,os=P.scale,osv=P.save,ors=P.restore;
P.translate=function(x,y){window.__F.tr.push([+x.toFixed(1),+y.toFixed(1)]);if(window.__F.tr.length>30)window.__F.tr.shift();return ot.apply(this,arguments);};
P.scale=function(x,y){window.__F.sc.push([+x.toFixed(3),+y.toFixed(3)]);if(window.__F.sc.length>30)window.__F.sc.shift();return os.apply(this,arguments);};
P.save=function(){window.__F.sv++;return osv.apply(this,arguments);};
P.restore=function(){window.__F.rs++;return ors.apply(this,arguments);};})();
setInterval(function(){var d=document.getElementById('dbgout');if(!d)return;
 d.textContent='E='+JSON.stringify(window.__E)+' save='+window.__F.sv+' restore='+window.__F.rs+' | tr='+JSON.stringify(window.__F.tr.slice(-3))+' | sc='+JSON.stringify(window.__F.sc.slice(-3));},800);
</script>"""
i = s.find("<script")
io.open(r"F:\Daodao\_tmp_face\dao_dbg.html", "w", encoding="utf-8").write(s[:i] + inj + s[i:])
print("ok")
