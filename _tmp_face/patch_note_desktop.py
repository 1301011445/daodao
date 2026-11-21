# -*- coding: utf-8 -*-
"""桌面端补一个记事本清单窗口：右键「记性和学问」里能点开，逐条划掉。"""
import io

SRC = r'F:\Daodao\src\桌面分身\pet.cs'
cs = io.open(SRC, encoding='utf-8').read()

menu_old = '''        gMind.DropDownItems.Add("我记住了什么", null, new EventHandler(MenuMemory));'''
menu_new = menu_old + '''
        // v0.107：记事本不再只有"说一句记一下"，右键能直接把清单摊开，逐条划掉
        gMind.DropDownItems.Add("记事本（点一下划掉）", null, new EventHandler(MenuNotes));'''
assert menu_old in cs
cs = cs.replace(menu_old, menu_new)

anchor = '''    void MenuMemory(object s, EventArgs e)'''
method = '''    // v0.107：记事本清单窗口。列表里点「✓」算做完、点「×」删掉，改完立刻回写 记事本.txt
    void MenuNotes(object s, EventArgs e)
    {
        Form f = new Form();
        f.Text = "记事本";
        f.Size = new Size(410, 560);
        f.StartPosition = FormStartPosition.CenterScreen;
        f.BackColor = Color.FromArgb(18, 24, 40);
        f.ForeColor = Color.WhiteSmoke;
        f.FormBorderStyle = FormBorderStyle.FixedDialog;
        f.MaximizeBox = false;
        f.MinimizeBox = false;
        try { f.Font = new Font("Microsoft YaHei UI", 10f); } catch { }

        FlowLayoutPanel list = new FlowLayoutPanel();
        list.Dock = DockStyle.Fill;
        list.FlowDirection = FlowDirection.TopDown;
        list.WrapContents = false;
        list.AutoScroll = true;
        list.BackColor = Color.FromArgb(18, 24, 40);
        list.Padding = new Padding(12, 10, 12, 12);

        Label tip = new Label();
        tip.Dock = DockStyle.Bottom;
        tip.Height = 32;
        tip.TextAlign = ContentAlignment.MiddleCenter;
        tip.ForeColor = Color.FromArgb(150, 165, 195);

        f.Controls.Add(list);
        f.Controls.Add(tip);

        Action render = null;
        render = delegate()
        {
            list.SuspendLayout();
            while (list.Controls.Count > 0) list.Controls[0].Dispose();
            string[] lines = NoteLines();
            int pend = 0, doneN = 0;
            for (int i = 0; i < lines.Length; i++)
            {
                string[] p = lines[i].Split('\\t');
                if (p.Length < 5) continue;
                bool done = p[2] == "1";
                if (done) doneN++; else pend++;
                Panel row = new Panel();
                row.Width = 350;
                row.Height = 62;
                row.Margin = new Padding(0, 4, 0, 0);
                row.BackColor = done ? Color.FromArgb(27, 33, 48) : Color.FromArgb(34, 44, 66);

                Label t = new Label();
                t.AutoSize = false;
                t.Left = 10; t.Top = 7;
                t.Width = 258; t.Height = 50;
                t.ForeColor = done ? Color.FromArgb(135, 146, 166) : Color.WhiteSmoke;
                t.Text = p[1] + "  " + p[4];

                Button ok = new Button();
                ok.Text = "✓";
                ok.Left = 276; ok.Top = 14;
                ok.Width = 34; ok.Height = 32;
                ok.FlatStyle = FlatStyle.Flat;
                ok.FlatAppearance.BorderColor = Color.FromArgb(110, 190, 140);
                ok.BackColor = Color.FromArgb(30, 62, 46);
                ok.ForeColor = Color.FromArgb(175, 235, 195);
                ok.Tag = p[0];
                ok.Click += new EventHandler(NoteRowDone);

                Button rm = new Button();
                rm.Text = "×";
                rm.Left = 314; rm.Top = 14;
                rm.Width = 34; rm.Height = 32;
                rm.FlatStyle = FlatStyle.Flat;
                rm.FlatAppearance.BorderColor = Color.FromArgb(190, 110, 110);
                rm.BackColor = Color.FromArgb(58, 30, 32);
                rm.ForeColor = Color.FromArgb(240, 180, 180);
                rm.Tag = p[0];
                rm.Click += new EventHandler(NoteRowDel);

                row.Controls.Add(t);
                row.Controls.Add(ok);
                row.Controls.Add(rm);
                list.Controls.Add(row);
            }
            if (pend + doneN == 0)
            {
                Label e2 = new Label();
                e2.Width = 350;
                e2.Height = 120;
                e2.TextAlign = ContentAlignment.MiddleCenter;
                e2.ForeColor = Color.FromArgb(140, 152, 176);
                e2.Text = "还没有登记的事。\\n跟我说一句「记一下 明天九点 交表」就行。";
                list.Controls.Add(e2);
            }
            tip.Text = (pend > 0 ? ("还有 " + pend + " 件没做完 · ") : "") + "点「✓」算做完，点「×」删掉这条";
            list.ResumeLayout();
            NoteRendererHook = render;      // 窗口开着的时候，外面加了一条也能刷新
        };

        f.FormClosed += new FormClosedEventHandler(delegate(object o2, FormClosedEventArgs e2) { NoteRendererHook = null; });
        render();
        f.ShowDialog();
        f.Dispose();
    }

    static Action NoteRendererHook = null;

    void NoteRowDone(object s, EventArgs e)
    {
        Button b = s as Button;
        if (b == null || b.Tag == null) return;
        NoteApi("op=done&id=" + b.Tag.ToString());
        if (NoteRendererHook != null) NoteRendererHook();
    }

    void NoteRowDel(object s, EventArgs e)
    {
        Button b = s as Button;
        if (b == null || b.Tag == null) return;
        NoteApi("op=del&id=" + b.Tag.ToString());
        if (NoteRendererHook != null) NoteRendererHook();
    }

'''
assert anchor in cs
cs = cs.replace(anchor, method + anchor, 1)

io.open(SRC, 'w', encoding='utf-8', newline='').write(cs)
print('补丁写完，pet.cs %d 字节' % len(cs))
print('  MenuNotes:', 'void MenuNotes(' in cs, '| 菜单项:', '记事本（点一下划掉）' in cs)
