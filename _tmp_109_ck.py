import io
p=r"F:\Daodao\tools\两端自用体检.py"; t=io.open(p,encoding="utf-8").read()
t=t.replace("all(k in dex for k in ('playSongAsset', 'playPcm', 'assetXhr'))",
            "all(k in dex for k in ('playSongAsset', 'decodeFrame', 'songPos', 'songDiag', 'assetXhr'))")
t=t.replace("('function startHold' in html) and ('win = null' in html)",
            "('function startHold' in html) and ('win = null' in html) and ('function setStatus' in html) and ('songDiag' in html)")
io.open(p,"w",encoding="utf-8").write(t)
print("ok", "decodeFrame" in t, "setStatus" in t)