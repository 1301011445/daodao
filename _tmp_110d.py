import io
p=r"F:\Daodao\src\桌面分身\pet.cs"
s=io.open(p,encoding="utf-8",errors="surrogateescape").read()

old1="""            else if (petMode == 1)
            {
                int vis = FullW * peekVisPct / 100;
                if (vis < 40) vis = 40;
                if (y > wa.Bottom - FullH / 2) y = wa.Bottom - FullH / 2;
                int x = peekSide == 1 ? wa.Left - (FullW - vis) : wa.Right - vis;
                Bounds = new Rectangle(x, y, FullW, FullH);
            }"""
new1="""            else if (petMode == 1)
            {
                // 关键：人物画在窗口正中，所以要让「窗口中心」正好压在屏幕边上，
                // 屏幕才刚好切掉一半身子。以前按窗口宽露出三成算，露出的其实是窗口左侧的空白，
                // 屏幕上什么都看不见（2026-11-22 实测踩到）。
                if (y > wa.Bottom - FullH / 2) y = wa.Bottom - FullH / 2;
                int x = peekSide == 1 ? wa.Left - FullW / 2 : wa.Right - FullW / 2;
                Bounds = new Rectangle(x, y, FullW, FullH);
            }"""
assert old1 in s
s=s.replace(old1,new1,1)

old2="""    int PeekRestX()
    {
        Rectangle wa = Screen.PrimaryScreen.WorkingArea;
        int vis = FullW * peekVisPct / 100;
        if (vis < 40) vis = 40;
        return peekSide == 1 ? wa.Left - (FullW - vis) : wa.Right - vis;
    }"""
new2="""    int PeekRestX()
    {
        Rectangle wa = Screen.PrimaryScreen.WorkingArea;
        return peekSide == 1 ? wa.Left - FullW / 2 : wa.Right - FullW / 2;
    }"""
assert old2 in s
s=s.replace(old2,new2,1)
io.open(p,"w",encoding="utf-8",errors="surrogateescape").write(s)
print("peek 定位改好")