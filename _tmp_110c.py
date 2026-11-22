import io
p=r"F:\Daodao\src\桌面分身\pet.cs"
s=io.open(p,encoding="utf-8",errors="surrogateescape").read()
s=s.replace("""    void RefreshModeChecks()
    {
        try { if (ContextMenuStrip != null) RefreshChecksIn(ContextMenuStrip); } catch { }
    }""","""    void RefreshModeChecks()
    {
        try
        {
            if (ContextMenuStrip == null) return;
            foreach (ToolStripItem it in ContextMenuStrip.Items) RefreshChecksIn(it);
        }
        catch { }
    }""",1)
io.open(p,"w",encoding="utf-8",errors="surrogateescape").write(s)
print("fixed")