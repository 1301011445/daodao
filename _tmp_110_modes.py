# 程序版本：v0.1 | 2026-11-22 | 一次性：桌面端加四种待法（满身/贴边偷看/悬浮球/收起）+ 干活时自动偷看
import io

P = r'F:\Daodao\src\桌面分身\pet.cs'
s = io.open(P, encoding='utf-8', errors='surrogateescape').read()

# ---------- 1) P/Invoke ----------
anchor = '    const uint SWP_NOACTIVATE = 0x0010;\n'
assert anchor in s
s = s.replace(anchor, anchor + '''
    [DllImport("user32.dll")]
    static extern IntPtr GetForegroundWindow();
    [DllImport("user32.dll")]
    static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint pid);
''', 1)

# ---------- 2) 字段 ----------
anchor2 = '    Point formStart;\n'
assert anchor2 in s
s = s.replace(anchor2, anchor2 + '''    // 2026-11-22 晚：桌面上的四种待法 —— 满身 / 贴边偷看（只露半边）/ 悬浮球 / 收起
    int petMode = 0;
    int peekVisPct = 34;          // 偷看时露出的宽度，占窗口宽的三分之一左右
    int peekSide = 2;             // 1 贴左边 2 贴右边
    bool autoPeek = true;         // 你在别的窗口干活时，它自己贴边
    bool autoPeekActive = false;
    System.Windows.Forms.Timer modeWatch;
    System.Windows.Forms.Timer slideTimer;
    int slideTargetX = int.MinValue;
    Point fullLoc = Point.Empty;
    NotifyIcon trayIcon;
''', 1)

# ---------- 3) 方法：插到 BuildMenu 之前 ----------
anchor3 = '    void BuildMenu()\n'
assert anchor3 in s
methods = '''    // ===== 桌面待法：满身 / 贴边偷看 / 悬浮球 / 收起 =====
    // 2026-11-22 晚（用户要求）：干活时它可以在屏幕侧边只露半边（像乔巴那样探头），
    // 也可以缩成悬浮球，点一下再出来。四种模式随时可换，选过就记住。
    int FullW { get { return (int)(W * uiScale); } }
    int FullH { get { return (int)(H * uiScale); } }

    void LoadModeSettings()
    {
        try
        {
            RegistryKey k = Registry.CurrentUser.OpenSubKey("Software\\\\DaoPet");
            if (k != null)
            {
                object m = k.GetValue("PetMode"); if (m != null) petMode = Convert.ToInt32(m);
                object sd = k.GetValue("PeekSide"); if (sd != null) peekSide = Convert.ToInt32(sd);
                object ap = k.GetValue("AutoPeek"); if (ap != null) autoPeek = Convert.ToInt32(ap) != 0;
                k.Close();
            }
        }
        catch { }
        if (petMode < 0 || petMode > 3) petMode = 0;
        if (peekSide != 1 && peekSide != 2) peekSide = 2;
    }

    void SaveModeSettings()
    {
        try
        {
            RegistryKey k = Registry.CurrentUser.CreateSubKey("Software\\\\DaoPet");
            if (k != null)
            {
                k.SetValue("PetMode", petMode);
                k.SetValue("PeekSide", peekSide);
                k.SetValue("AutoPeek", autoPeek ? 1 : 0);
                k.Close();
            }
        }
        catch { }
    }

    void SetMode(int m)
    {
        if (m < 0 || m > 3) m = 0;
        if (petMode == 0 && m != 0) fullLoc = Location;   // 记住满身时站在哪儿，回来还原
        petMode = m;
        SetModeWindow();
        SaveModeSettings();
        RefreshModeChecks();
    }

    void SetModeWindow()
    {
        try
        {
            if (slideTimer != null) slideTimer.Stop();
            slideTargetX = int.MinValue;
            if (petMode == 3)
            {
                EnsureTray();
                if (trayIcon != null) trayIcon.Visible = true;
                Hide();
                return;
            }
            if (trayIcon != null) trayIcon.Visible = false;
            if (!Visible) ShowWindow(this.Handle, SW_SHOWNOACTIVATE);
            Rectangle wa = Screen.PrimaryScreen.WorkingArea;
            int y = Location.Y;
            if (y < wa.Top + 8) y = wa.Top + 8;
            if (petMode == 2)
            {
                int d = (int)(72 * uiScale);
                if (d < 40) d = 40;
                if (y > wa.Bottom - d - 8) y = wa.Bottom - d - 8;
                int x = peekSide == 1 ? wa.Left + 6 : wa.Right - d - 6;
                Bounds = new Rectangle(x, y, d, d);
            }
            else if (petMode == 1)
            {
                int vis = FullW * peekVisPct / 100;
                if (vis < 40) vis = 40;
                if (y > wa.Bottom - FullH / 2) y = wa.Bottom - FullH / 2;
                int x = peekSide == 1 ? wa.Left - (FullW - vis) : wa.Right - vis;
                Bounds = new Rectangle(x, y, FullW, FullH);
            }
            else
            {
                Bounds = new Rectangle(Location.X, Location.Y, FullW, FullH);
                if (fullLoc != Point.Empty)
                {
                    int x = Math.Max(wa.Left + 8, Math.Min(fullLoc.X, wa.Right - FullW - 8));
                    int yy = Math.Max(wa.Top + 8, Math.Min(fullLoc.Y, wa.Bottom - FullH - 8));
                    Location = new Point(x, yy);
                }
            }
            ForceLayer();
            TopMost = true;
            SetWindowPos(this.Handle, HWND_TOPMOST, Location.X, Location.Y, Bounds.Width, Bounds.Height, SWP_NOACTIVATE);
        }
        catch { }
    }

    void SlideTo(int targetX)
    {
        if (slideTimer == null)
        {
            slideTimer = new System.Windows.Forms.Timer();
            slideTimer.Interval = 16;
            slideTimer.Tick += delegate(object s, EventArgs e)
            {
                if (slideTargetX == int.MinValue) { slideTimer.Stop(); return; }
                int dx = slideTargetX - Location.X;
                if (Math.Abs(dx) <= 3)
                {
                    Location = new Point(slideTargetX, Location.Y);
                    slideTimer.Stop();
                    slideTargetX = int.MinValue;
                    return;
                }
                Location = new Point(Location.X + dx / 3, Location.Y);
            };
        }
        slideTargetX = targetX;
        if (!slideTimer.Enabled) slideTimer.Start();
    }

    int PeekRestX()
    {
        Rectangle wa = Screen.PrimaryScreen.WorkingArea;
        int vis = FullW * peekVisPct / 100;
        if (vis < 40) vis = 40;
        return peekSide == 1 ? wa.Left - (FullW - vis) : wa.Right - vis;
    }

    int PeekOutX()
    {
        Rectangle wa = Screen.PrimaryScreen.WorkingArea;
        return peekSide == 1 ? wa.Left : wa.Right - FullW;
    }

    void StartModeWatch()
    {
        if (modeWatch != null) return;
        modeWatch = new System.Windows.Forms.Timer();
        modeWatch.Interval = 900;
        modeWatch.Tick += delegate(object s, EventArgs e) { AutoPeekCheck(); };
        modeWatch.Start();
    }

    bool ForegroundIsOther()
    {
        try
        {
            IntPtr h = GetForegroundWindow();
            if (h == IntPtr.Zero) return false;
            uint pid = 0;
            GetWindowThreadProcessId(h, out pid);
            if (pid == 0) return false;
            return pid != (uint)Process.GetCurrentProcess().Id;
        }
        catch { return false; }
    }

    // 在别的窗口里干活 → 自己贴边只露半边；回到桌面/回到它身上 → 回满身
    void AutoPeekCheck()
    {
        if (mouseDown) return;
        if (!autoPeek)
        {
            if (autoPeekActive && petMode == 1) { autoPeekActive = false; SetMode(0); }
            return;
        }
        bool other = ForegroundIsOther();
        if (other && petMode == 0)
        {
            Rectangle wa = Screen.PrimaryScreen.WorkingArea;
            peekSide = (Location.X + FullW / 2) < (wa.Left + wa.Width / 2) ? 1 : 2;
            autoPeekActive = true;
            SetMode(1);
        }
        else if (!other && autoPeekActive && petMode == 1)
        {
            autoPeekActive = false;
            SetMode(0);
        }
    }

    void EnsureTray()
    {
        if (trayIcon != null) return;
        trayIcon = new NotifyIcon();
        try { trayIcon.Icon = this.Icon != null ? this.Icon : SystemIcons.Application; }
        catch { try { trayIcon.Icon = SystemIcons.Application; } catch { } }
        trayIcon.Text = "道";
        ContextMenuStrip tm = new ContextMenuStrip();
        tm.Items.Add("出来（满身）", null, new EventHandler(delegate(object s, EventArgs e) { SetMode(0); }));
        tm.Items.Add("贴边偷看（只露半边）", null, new EventHandler(delegate(object s, EventArgs e) { SetMode(1); }));
        tm.Items.Add("缩成悬浮球", null, new EventHandler(delegate(object s, EventArgs e) { SetMode(2); }));
        tm.Items.Add(new ToolStripSeparator());
        tm.Items.Add("退出道", null, new EventHandler(delegate(object s, EventArgs e) { try { trayIcon.Visible = false; } catch { } Close(); }));
        trayIcon.ContextMenuStrip = tm;
        trayIcon.DoubleClick += new EventHandler(delegate(object s, EventArgs e) { SetMode(0); });
    }

    void RefreshModeChecks()
    {
        try { if (ContextMenuStrip != null) RefreshChecksIn(ContextMenuStrip); } catch { }
    }

    void RefreshChecksIn(ToolStripItem it)
    {
        if (!(it is ToolStripMenuItem)) return;
        ToolStripMenuItem mi = (ToolStripMenuItem)it;
        if (mi.Name != null && mi.Name.StartsWith("mode")) { try { mi.Checked = (Convert.ToInt32(mi.Tag) == petMode); } catch { } }
        if (mi.Name == "autopeek") mi.Checked = autoPeek;
        foreach (ToolStripItem sub in mi.DropDownItems) RefreshChecksIn(sub);
    }

    void MenuSetMode(object s, EventArgs e)
    {
        ToolStripMenuItem it = (ToolStripMenuItem)s;
        autoPeekActive = false;
        SetMode(Convert.ToInt32(it.Tag));
    }

    void MenuToggleAutoPeek(object s, EventArgs e)
    {
        autoPeek = !autoPeek;
        ToolStripMenuItem it = (ToolStripMenuItem)s;
        it.Checked = autoPeek;
        SaveModeSettings();
        if (!autoPeek && autoPeekActive) { autoPeekActive = false; if (petMode == 1) SetMode(0); }
    }

    void MenuFlipSide(object s, EventArgs e)
    {
        peekSide = peekSide == 1 ? 2 : 1;
        SaveModeSettings();
        if (petMode == 1 || petMode == 2) SetModeWindow();
    }

'''
s = s.replace(anchor3, methods + anchor3, 1)

# ---------- 4) 菜单：桌面组里加一项 ----------
anchor4 = '        gDesk.DropDownItems.Add("打开回收站", null, new EventHandler(MenuRecycle));\n'
assert anchor4 in s
menu = '''        ToolStripMenuItem gMode = new ToolStripMenuItem("我在桌面上的样子");
        string[] modeNames = { "满身（跟原来一样）", "贴边偷看（只露半边）", "缩成悬浮球", "收起（只在托盘）" };
        for (int mi2 = 0; mi2 < 4; mi2++)
        {
            ToolStripMenuItem mmi = new ToolStripMenuItem(modeNames[mi2]);
            mmi.Tag = mi2;
            mmi.Name = "mode" + mi2;
            mmi.Checked = (petMode == mi2);
            mmi.Click += new EventHandler(MenuSetMode);
            gMode.DropDownItems.Add(mmi);
        }
        gMode.DropDownItems.Add(new ToolStripSeparator());
        ToolStripMenuItem apm = new ToolStripMenuItem("干活时自己去边上偷看");
        apm.Name = "autopeek";
        apm.Checked = autoPeek;
        apm.ToolTipText = "你在别的窗口里做事时，它自己贴到屏幕边，只露半边；点它一下就出来";
        apm.Click += new EventHandler(MenuToggleAutoPeek);
        gMode.DropDownItems.Add(apm);
        gMode.DropDownItems.Add("换一边（左 / 右）", null, new EventHandler(MenuFlipSide));
        gDesk.DropDownItems.Add(gMode);
'''
s = s.replace(anchor4, anchor4 + menu, 1)

# ---------- 5) 悬浮球画法 ----------
anchor5 = '''        g.TranslateTransform((cw - W * s) / 2f, (ch - H * s) / 2f);'''
assert anchor5 in s
s = s.replace(anchor5, '''        if (petMode == 2)
        {
            PaintBall(g, cw, ch);
            return;
        }
''' + anchor5, 1)

anchor6 = '    public void PaintAll(Graphics g, int cw, int ch)\n'
assert anchor6 in s
ball = '''    // 悬浮球：缩到 72 像素，只剩一张脸，点一下弹回满身
    void PaintBall(Graphics g, int cw, int ch)
    {
        float r = Math.Min(cw, ch) / 2f - 2f;
        if (r < 8f) r = 8f;
        float cx = cw / 2f, cy = ch / 2f;
        r *= 1f + 0.03f * (float)Math.Sin(t * 1.6f);
        g.SmoothingMode = SmoothingMode.AntiAlias;
        using (LinearGradientBrush br = new LinearGradientBrush(new RectangleF(cx - r, cy - r, r * 2, r * 2),
            Color.FromArgb(255, 92, 128, 216), Color.FromArgb(255, 30, 46, 96), 90f))
        {
            g.FillEllipse(br, cx - r, cy - r, r * 2, r * 2);
        }
        using (Pen pen = new Pen(Color.FromArgb(255, 190, 214, 255), 1.8f))
        {
            g.DrawEllipse(pen, cx - r, cy - r, r * 2, r * 2);
        }
        float ey = cy - r * 0.14f, ex = r * 0.30f;
        using (SolidBrush wb = new SolidBrush(Color.FromArgb(255, 236, 244, 255)))
        {
            if (blinkFrames > 0)
            {
                g.FillRectangle(wb, cx - ex - 5, ey, 10, 2);
                g.FillRectangle(wb, cx + ex - 5, ey, 10, 2);
            }
            else
            {
                g.FillEllipse(wb, cx - ex - 5, ey - 5, 10, 10);
                g.FillEllipse(wb, cx + ex - 5, ey - 5, 10, 10);
            }
        }
        using (Pen mp = new Pen(Color.FromArgb(220, 236, 244, 255), 1.6f))
        {
            g.DrawArc(mp, cx - r * 0.28f, cy + r * 0.06f, r * 0.56f, r * 0.36f, 20, 140);
        }
    }

'''
s = s.replace(anchor6, ball + anchor6, 1)

# ---------- 6) 鼠标：偷看/球点一下出来；靠边滑出、离开滑回 ----------
old_up = '''            if (movedFlag) SavePos();
            else
            {'''
assert old_up in s
s = s.replace(old_up, '''            if (movedFlag) SavePos();
            else if (petMode == 1 || petMode == 2)
            {
                // 偷看/球的状态下点一下 = 叫我出来
                autoPeekActive = false;
                SetMode(0);
                waveTicks = 26;
                idleTicks = 0;
                return;
            }
            else
            {''', 1)

anchor7 = '    protected override void OnDoubleClick(EventArgs e)\n'
assert anchor7 in s
s = s.replace(anchor7, '''    protected override void OnMouseEnter(EventArgs e)
    {
        base.OnMouseEnter(e);
        if (petMode == 1) SlideTo(PeekOutX());     // 探头：鼠标过来就整个出来
    }

    protected override void OnMouseLeave(EventArgs e)
    {
        base.OnMouseLeave(e);
        if (petMode == 1 && !mouseDown) SlideTo(PeekRestX());   // 走开又缩回去
    }

''' + anchor7, 1)

# ---------- 7) 构造时读设置 + 启动看守 ----------
anchor8 = '        AutoScaleMode = AutoScaleMode.None;\n'
assert anchor8 in s
s = s.replace(anchor8, '        LoadModeSettings();\n' + anchor8, 1)

anchor9 = '        noteTimer.Start();\n'
assert anchor9 in s
s = s.replace(anchor9, anchor9 + '        StartModeWatch();\n', 1)

io.open(P, 'w', encoding='utf-8', errors='surrogateescape').write(s)
print('pet.cs OK', s.count('\n') + 1)
