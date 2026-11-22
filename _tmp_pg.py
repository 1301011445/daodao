import io
p=r"F:\Daodao\src\桌面分身\pet.cs"
s=io.open(p,encoding="utf-8",errors="surrogateescape").read()
old="""    protected override void OnPaint(PaintEventArgs e)
    {
        PaintAll(e.Graphics, ClientSize.Width, ClientSize.Height);
    }"""
new="""    protected override void OnPaint(PaintEventArgs e)
    {
        try
        {
            PaintAll(e.Graphics, ClientSize.Width, ClientSize.Height);
        }
        catch (Exception ex)
        {
            try
            {
                File.AppendAllText(System.IO.Path.Combine(System.IO.Path.GetTempPath(), "pet_paint_err.txt"),
                    DateTime.Now.ToString("HH:mm:ss") + " petMode=" + petMode + " cw=" + ClientSize.Width + " " + ex.ToString() + Environment.NewLine);
            }
            catch { }
            base.OnPaint(e);
        }
    }"""
assert old in s
s=s.replace(old,new,1)
io.open(p,"w",encoding="utf-8",errors="surrogateescape").write(s)
print("paint guard added")