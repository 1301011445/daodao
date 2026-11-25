# -*- coding: utf-8 -*-
"""v130 / 1：桌面端接「连着聊」（多轮实时语音）
· 念白交给 voice.py 逐句自己合成（进程内），窗口只显示气泡，避免两边抢麦克风
· 读 stdout 的 JSON 行：state=done 显示回话；state=bye 收尾
"""
P = r'F:\Daodao\src\桌面分身\pet.cs'
s = open(P, encoding='utf-8').read()
anchor = '''        voiceChatThread.IsBackground = true;
        voiceChatThread.Start();
    }'''
assert s.count(anchor) == 1, s.count(anchor)
add = anchor + '''

    // ===== v130 连着聊：多轮实时语音对话 =====
    // 一轮接一轮「听 → 想」都在 voice.py 里跑，回话也由它逐句合成播出来（同一进程，不抢麦）；
    // 窗口这边只把回话显示在气泡上，不再重复念一遍。
    System.Threading.Thread talkThread;
    Process talkProc;

    void MenuTalkChat(object s, EventArgs e)
    {
        if (talkThread != null && talkThread.IsAlive)
        {
            Say("还在聊着，先让它收个尾。");
            return;
        }
        if (!voiceOn) voiceOn = true;
        Say("好，我听着。你说「别说了」我就停。");
        talkThread = new System.Threading.Thread(delegate() { TalkLoop(); });
        talkThread.IsBackground = true;
        talkThread.Start();
    }

    void TalkLoop()
    {
        try
        {
            string py = Path.Combine(Path.GetDirectoryName(Application.ExecutablePath), "voice.py");
            if (!System.IO.File.Exists(py))
            {
                BeginInvoke(new MethodInvoker(delegate() { Say("语音模块没装上，等我更新一下自己。"); }));
                return;
            }
            ProcessStartInfo pi = new ProcessStartInfo();
            pi.FileName = PyExe();
            pi.Arguments = "\\"" + py + "\\" talk";
            pi.UseShellExecute = false;
            pi.CreateNoWindow = true;
            pi.RedirectStandardOutput = true;
            pi.RedirectStandardError = true;
            pi.StandardOutputEncoding = System.Text.Encoding.UTF8;
            pi.StandardErrorEncoding = System.Text.Encoding.UTF8;
            pi.WindowStyle = ProcessWindowStyle.Hidden;
            Process p = Process.Start(pi);
            talkProc = p;
            string line;
            while ((line = p.StandardOutput.ReadLine()) != null)
            {
                line = line.Trim();
                if (line.Length == 0) continue;
                string st = JsonStr(line, "state");
                string rep = JsonStr(line, "reply");
                int md = JsonInt(line, "mood");
                if (st == "bye") break;
                if (rep != null && rep.Length > 0)
                {
                    string rr = rep;
                    int mm = md;
                    BeginInvoke(new MethodInvoker(delegate()
                    {
                        bubble = rr;
                        bubbleFrames = 60 + rr.Length * 3;
                        if (bubbleFrames > 140) bubbleFrames = 140;
                        if (mm > 0 && mm <= 8) { moodKind = mm; moodTicks = 70; }
                        Invalidate();
                    }));
                }
            }
            try { p.StandardError.ReadToEnd(); } catch { }
            try { p.WaitForExit(3000); } catch { }
            talkProc = null;
        }
        catch { }
    }
'''
s = s.replace(anchor, add, 1)
open(P, 'w', encoding='utf-8').write(s)
print('PATCH1_OK TalkLoop')

# 菜单项：挂在语音菜单里，紧挨着「语音对话」
anchor2 = '        voiceItem.Click += new EventHandler(MenuVoiceChat);'
assert anchor2 in s
s2 = s.replace(anchor2, anchor2 + '''
        // v130：连着聊（多轮），跟单轮语音对话分开挂，别互相覆盖
        ToolStripMenuItem talkItem = new ToolStripMenuItem("连着聊几句");
        talkItem.Click += new EventHandler(MenuTalkChat);
        voiceItem.DropDownItems.Add(talkItem);''', 1)
open(P, 'w', encoding='utf-8').write(s2)
print('PATCH1_OK menu')

j = open(P, encoding='utf-8').read()
c = [('C1 TalkLoop 进代码', 'void TalkLoop()' in j),
     ('C2 菜单挂上', 'talkItem.Click += new EventHandler(MenuTalkChat);' in j),
     ('C3 回话只显示不重复念', 'bubbleFrames = 60 + rr.Length * 3;' in j and 'SpeakOut(rr)' not in j)]
for n, v in c:
    print(n, 'PASS' if v else 'FAIL')
print('SUMMARY', 'PASS' if all(v for _, v in c) else 'FAIL')
raise SystemExit(0 if all(v for _, v in c) else 1)
