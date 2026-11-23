using System;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.Drawing.Imaging;
using System.Windows.Forms;
using System.Diagnostics;
using Microsoft.Win32;
using System.Runtime.InteropServices;
using System.IO;
using System.Text;
using System.Collections.Generic;
using System.Net;
using System.Text.RegularExpressions;

public class DesktopPet : Form
{
    [DllImport("user32.dll")]
    static extern bool SetProcessDPIAware();

    [DllImport("user32.dll")]
    static extern bool IsProcessDPIAware();

    [DllImport("user32.dll")]
    static extern bool SetWindowPos(IntPtr hWnd, IntPtr after, int x, int y, int cx, int cy, uint flags);

    [DllImport("user32.dll")]
    public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
    const int SW_SHOWNOACTIVATE = 4;

    [DllImport("user32.dll")]
    public static extern bool SetLayeredWindowAttributes(IntPtr hWnd, int crKey, byte alpha, int flags);
    public const int LWA_COLORKEY = 0x1;
    static readonly IntPtr HWND_TOPMOST = new IntPtr(-1);
    const uint SWP_NOMOVE = 0x0002;
    const uint SWP_NOSIZE = 0x0001;
    const uint SWP_NOACTIVATE = 0x0010;

    [DllImport("user32.dll")]
    static extern IntPtr GetForegroundWindow();
    [DllImport("user32.dll")]
    static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint pid);

    [StructLayout(LayoutKind.Sequential)]
    public class MEMORYSTATUSEX
    {
        public uint dwLength;
        public uint dwMemoryLoad;
        public ulong ullTotalPhys;
        public ulong ullAvailPhys;
        public ulong ullTotalPageFile;
        public ulong ullAvailPageFile;
        public ulong ullTotalVirtual;
        public ulong ullAvailVirtual;
        public ulong ullAvailExtendedVirtual;
        public MEMORYSTATUSEX() { this.dwLength = (uint)Marshal.SizeOf(typeof(MEMORYSTATUSEX)); }
    }

    [DllImport("kernel32.dll", SetLastError = true)]    [return: MarshalAs(UnmanagedType.Bool)]
    static extern bool GlobalMemoryStatusEx([In, Out] MEMORYSTATUSEX lpBuffer);

    // 2026-11-22 帧调度：WinForms 的 Timer 走 WM_TIMER，精度被系统计时器量子卡住（默认 ~15.6ms），
    // 所以请求 33ms 实际是 46.6ms。把计时器分辨率提到 1ms，才能真正按 Interval 出帧。
    [DllImport("winmm.dll")]
    static extern uint timeBeginPeriod(uint uPeriod);
    [DllImport("winmm.dll")]
    static extern uint timeEndPeriod(uint uPeriod);

    const int W = 380;
    const int H = 205;

    // 系统缩放比例（150% 缩放时窗口会被系统压成 2/3，这里补回来）
    static float uiScale = CalcUiScale();

    static float CalcUiScale()
    {
        try
        {
            // 以前 DPI 感知时直接返回 1，结果在 150% 缩放的机器上窗口只有 380×205 物理像素，
            // 比系统其它字都小一圈，形象在桌面上就成了一小坨。改成不管是否 DPI 感知，
            // 都按系统应用 DPI 换算：1920×1080@150% 上画布变成 570×307，人物跟上界面比例
            RegistryKey k = Registry.CurrentUser.OpenSubKey(@"Control Panel\Desktop\WindowMetrics");
            if (k != null)
            {
                object v = k.GetValue("AppliedDPI");
                if (v != null)
                {
                    int dpi = Convert.ToInt32(v);
                    if (dpi >= 96 && dpi <= 480) return dpi / 96f;
                }
            }
        }
        catch { }
        return 1f;
    }
    const int KEY = 0xFF00FF;

    Timer anim;
    Stopwatch animClock = new Stopwatch();
    // 2026-11-22 第1类二轮「帧调度」：只量不改——tick 真实间隔与单帧重绘耗时全部留样，
    // 由 /diag 读出来给 tools\界面\帧调度检查.py 判 PASS/FAIL，不靠眼睛估
    static double[] dgIv = new double[300];
    static int dgIvN = 0, dgIvI = 0;
    static double[] dgPm = new double[300];
    static int dgPmN = 0, dgPmI = 0;
    static long dgTickCount = 0;
    static int dgIntervalMs = 0;
    static void DgTick(double ms)
    {
        dgTickCount++;
        dgIv[dgIvI] = ms; dgIvI = (dgIvI + 1) % dgIv.Length; if (dgIvN < dgIv.Length) dgIvN++;
    }
    static void DgPaint(double ms)
    {
        dgPm[dgPmI] = ms; dgPmI = (dgPmI + 1) % dgPm.Length; if (dgPmN < dgPm.Length) dgPmN++;
    }
    // 环形缓冲取样求 avg/p50/p95/max；n<3 直接报样本不足，不给假分数
    System.Threading.Timer pump;
    // 出一个帧就置忙，画完再放开：Threading.Timer 比 UI 线程快的时候不许把消息队列灌满
    static volatile bool dgPumpBusy = false;
    void PumpTick(object o)
    {
        if (dgPumpBusy) return;
        try
        {
            if (IsDisposed || !IsHandleCreated) return;
            dgPumpBusy = true;
            BeginInvoke(new MethodInvoker(delegate()
            {
                try { OnTick(null, EventArgs.Empty); }
                finally { dgPumpBusy = false; }
            }));
        }
        catch { dgPumpBusy = false; }
    }
    // 2026-11-22 呼吸节律：周期 3.6~5.2 秒（每次重取），吸气占 38%，每口气幅度 ±5% 浮动。
    // 波形不是纯正弦：吸气走 -1→+1 的半余弦，呼气 +1→-1，两段在边界上连续，不会"跳一口气"
    float brT = 0f;
    float brPeriod = 4.2f;
    float brPh = 0f;
    float brAmpJit = 1f;
    Random brRnd = new Random();
    void BrStep(float dt)
    {
        brT += dt;
        if (brT >= brPeriod)
        {
            brT -= brPeriod;
            brPeriod = 3.6f + (float)(brRnd.NextDouble() * 1.6);
            brAmpJit = 0.95f + (float)(brRnd.NextDouble() * 0.10f);
            if (brT < 0f) brT = 0f;
        }
        brPh = (brPeriod > 0.1f) ? (brT / brPeriod) : 0f;
    }
    static float BrWave(float ph)
    {
        if (ph < 0f) ph = 0f;
        if (ph > 0.9999f) ph = 0.9999f;
        if (ph < 0.38f)
        {
            float u = ph / 0.38f;
            return -(float)Math.Cos(u * (float)Math.PI);   // -1 → +1（吸气）
        }
        float v = (ph - 0.38f) / 0.62f;
        return (float)Math.Cos(v * (float)Math.PI);        // +1 → -1（呼气）
    }
    float BrValue()
    {
        return BrWave(brPh) * brAmpJit;
    }

    static string DgCalc(double[] arr, int n, int wi)
    {        int cnt = n < arr.Length ? n : arr.Length;
        if (cnt < 3) return "n=" + cnt + "|no-data";
        double[] v = new double[cnt];
        int s = (wi - cnt + arr.Length * 2) % arr.Length;
        for (int k = 0; k < cnt; k++) v[k] = arr[(s + k) % arr.Length];
        Array.Sort(v);
        double avg = 0;
        for (int k = 0; k < cnt; k++) avg += v[k];
        avg /= cnt;
        double p50 = v[(int)(cnt * 0.5)];
        double p95 = v[cnt - 1 < (int)(cnt * 0.95) ? cnt - 1 : (int)(cnt * 0.95)];
        return string.Format("n={0}|avg={1:F1}|p50={2:F1}|p95={3:F1}|max={4:F1}", cnt, avg, p50, p95, v[cnt - 1]);
    }
    public static string DgReset()
    {
        dgIvN = 0; dgIvI = 0; dgPmN = 0; dgPmI = 0; dgTickCount = 0;
        return "RESET";
    }
    public static string DiagCmd()
    {
        string iv = DgCalc(dgIv, dgIvN, dgIvI);
        string pm = DgCalc(dgPm, dgPmN, dgPmI);
        double p50 = 0;
        int a = iv.IndexOf("p50=");
        if (a > 0)
        {
            int b = iv.IndexOf('|', a);
            double.TryParse(b > 0 ? iv.Substring(a + 4, b - a - 4) : iv.Substring(a + 4), out p50);
        }
        double fps = p50 > 0.1 ? 1000.0 / p50 : 0;
        return "DIAG|iv(" + iv + ")|paint(" + pm + ")|ticks=" + dgTickCount +
               "|interval=" + dgIntervalMs + "|fps=" + fps.ToString("F1") + "|ver=" + SyncServer.APP_VER;
    }
    float animLastDt = 0.045f;
    float t = 0f;
    int species = 0;
    int blinkWait = 0;
    int blinkFrames = 0;
    // v32：眨眼和呼吸都改成按真实时间走，间隔随机，不再拿毫秒数取余凑数
    float blinkNextT = 2.6f;      // 距离下次眨眼还有几秒
    float blinkCloseT = 0f;       // 这次闭眼要闭多久
    Random blinkRnd = new Random();
    string bubble = null;
    int bubbleFrames = 0;
    bool voiceOn = true;
    System.Threading.Thread voiceThread;
    // 要说的话排成一条队，一句播完再播下一句。之前是并发播的，两句撞一起就叠着响
    class SpeakJob { public string text; public string voice; public string fx; }
    object speakQLock = new object();
    System.Collections.Generic.Queue<SpeakJob> speakQueue = new System.Collections.Generic.Queue<SpeakJob>();
    System.Threading.Thread hearThread;
    System.Threading.Thread transThread;
    System.Threading.Thread backupThread;
    Random rnd = new Random();
    System.Windows.Forms.Timer memTimer;
    System.Windows.Forms.Timer briefTimer;
    System.Windows.Forms.Timer learnTimer;
    System.Windows.Forms.Timer noteTimer;
    bool mouseDown = false;
    bool movedFlag = false;
    Point dragStart;
    Point formStart;
    // 2026-11-22 晚：桌面上的四种待法 —— 满身 / 贴边偷看（只露半边）/ 悬浮球 / 收起
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
    bool speaking = false;
    System.Diagnostics.Process curPlayer = null;   // 当前正在播语音的进程，点它就能立刻掐掉
    bool hearBusy = false;                          // 正在录你说的话，这期间它自己别开口
    // 2026-11-22：喊名字就醒。常驻听唤醒词（默认开），听到「道」就先应一声，再接着听下一句
    bool wakeOn = true;
    System.Threading.Thread wakeThread;
    long wakeHitAt = 0;                             // 最近一次应声的时刻，用来给下一轮留缓冲
    string lastSaidText = "";                       // 刚说过的话，挡住把自己的尾音当成主人在叫
    int speakTicks = 0;
    int walkCounter = 0;
    float tiltTarget = 0f;
    float tiltNow = 0f;
    int walkDirX = 0;
    // 说话时嘴离脸中心多远（单位：脸半径）。有的形象嘴靠上：企鹅有喙、机器人脸是整块面罩
    float[] speakMouthDY = { 0.46f, 0.44f, 0.45f, 0.44f, 0.45f, 0.17f, 0.42f, 0.42f, 0.42f, 0.42f, 0.42f, 0.18f };

    int moodTicks = 0;
    int moodKind = 0;
    int moodWait = 200;
    // 说话时嘴的开合时段（毫秒，Environment.TickCount 计时）
    int speakMouthStart = 0;
    int speakMouthUntil = 0;
    // v61（第26类落地）：说话时点头不再写死频率，改按曲子的拍长点头。
    // 阈值从 口型阈值.json 读（谱子驱动动作检查.py 生成），读不到就用 92BPM 的 652.2ms 兜底。
    static float nodBeatMs = 652.2f;
    static bool nodThLoaded = false;
    static void LoadNodThreshold()
    {
        if (nodThLoaded) return;
        nodThLoaded = true;
        try
        {
            string[] cands = new string[] {
                Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "口型阈值.json"),
                Path.Combine(AppDomain.CurrentDomain.BaseDirectory, @"tools\音乐\谱子驱动动作\口型阈值.json")
            };
            foreach (string p in cands)
            {
                if (!File.Exists(p)) continue;
                string txt = File.ReadAllText(p, Encoding.UTF8);
                var m = System.Text.RegularExpressions.Regex.Match(txt, "\"点头拍长_ms\"\\s*:\\s*([0-9.]+)");
                if (!m.Success) m = System.Text.RegularExpressions.Regex.Match(txt, "\"小节_ms\"\\s*:\\s*([0-9.]+)");
                if (m.Success)
                {
                    float v = 0f;
                    if (float.TryParse(m.Groups[1].Value, out v) && v >= 200f && v <= 4000f)
                    {
                        nodBeatMs = v;
                        return;
                    }
                }
            }
        }
        catch { }
    }

    int walkTicks = 0;
    int walkTargetX = -999999;
    int walkTargetY = -999999;
    int hopPend = 0;
    int hopWait = 260;
    int runTicks = 0;         // 跑：距离远时加速、前倾、步频更快
    // 2026-11-20：步频跟真实位移联动。原来帧率固定在 11.6/s，而移动有 3px、7px 两档，
    // 快走时一步跨得远、脚频不变，脚底就打滑。这里按"每秒实际挪多少像素"反推步频，
    // 再逐跳平滑靠近，起步/停下都不会突然变速。
    float walkFpsCur = 11.6f;
    float moveSpeedPxPerSec = 0f;
    float walkPhase = 0f;     // 走路相位（0..8，一帧一格），自己累加，帧率变化也不会跳帧
    float walkLastT = -1f;
    int thinkTicks = 0;
    int thinkWait = 300;
    int diagCount = 0;
    int waveTicks = 0;        // 招手打招呼
    int idleTicks = 0;        // 无交互计时
    int idlePaintSkip = 0;    // 闲置降帧：站着不动时每 3 跳才重画一次（2026-11-18）
    int idleTalkWait = 3000;  // 隔一阵自己说句话的倒计时
    bool sitting = false;     // 坐下歇着
    bool sleepy = false;      // 犯困眯眼
    bool lying = false;       // 真躺下睡：整只侧倒，头上飘 Z
    float lieAmt = 0f;        // 0 站着 1 躺着，用来平滑过渡
    int lieHold = 0;          // 手动"睡一觉"还剩多少帧
    // 额外生活动作：1 飞 2 御剑 3 骑坐骑 4 跳舞 5 喝茶 6 看电视
    int actKind = 0;
    int actHold = 0;          // 还保持多少帧
    float actAmt = 0f;        // 0..1 平滑进出，道具跟着淡入淡出，不会突然冒出来
    int cryHold = 0;          // 手动"哭一个"还剩多少帧
    int edgeStay = 0;         // 贴边后歇一会儿
    // 脚下的场景：0 城市 1 乡野 2 海边 3 花丛，见过一阵自己换
    int sceneIdx = 1;
    bool sceneOn = false;     // 场景开关：先关掉，改用纯透明桌面；以后优化好了再打开
    int sceneTick = 0;
    // 走的时候真的在场景里挪位置：走到画面边上就转身往回走，不是原地踏步
    float tripX = 0f;
    int tripDir = 1;

    string[] speciesName = { "橘猫", "小狗", "白兔", "棕熊", "小恐龙", "章鱼", "小黄鸡" };
    string[] speciesColor = { "#F5A45C", "#C68B59", "#F2ECE1", "#A9744F", "#7FB77E", "#B39DDB", "#FFD54F" };

    // 全身配色（与 faces 下标一一对应，头像图的代表色）
    string[] faceBodyColor = {
        "#F5A45C", "#F2ECE1", "#D9714B", "#EDEDED", "#7FB77E", "#4A5568",
        "#6C8CD5", "#6B7280", "#3B4A6B", "#7A5CB8", "#E8A0B4", "#DDE3EA"
    };

    // ==== 图片形象（faces 目录）====
    Bitmap[] faces = null;
    string[] faceNames = null;
    string[] faceVoices = null;
    int faceCount = 0;
    int[] faceFileIdx = null;

    // ==== 整套姿势图（大模型出的同一角色多种动作）====
    // 每张都是同一角色、同尺寸画布、底部对齐、水平居中，程序只在姿势之间切换，
    // 不做骨架拼装：手抬起来、腿迈出去都是图里本来就有的，不是把身体切条推开
    Bitmap[] poses = null;
    int poseIdx = 0;
    int posePrev = 0;
    float poseFade = 2f;
    int poseOwner = -1;   // 这套姿势属于哪个形象序号；-1 表示该形象还没有姿势集
    // 哪个形象有完整一套动作。有动作的形象才能上桌，所以每天就在这几个里轮，
    // 一个形象都没有动作的时候退回原来的随机形象 + 单张静态图
    Dictionary<int, Bitmap[]> poseMap = new Dictionary<int, Bitmap[]>();
    int[] poseKinds = new int[0];

    // ==== 八帧走路循环 ====
    // 每个形象单独一套：触地、下沉、交叉、抬起 x 左右各一遍。
    // 走的时候直接换帧，手脚在图里本来就摆开了，不靠切条位移去骗眼睛
    Dictionary<int, Bitmap[]> walkMap = new Dictionary<int, Bitmap[]>();
    Bitmap[] walkFrames = null;

    // 每张形象图里"脸"的位置：中心 (x, y) 相对整张图宽高比例，w 是脸宽占图宽比例
    // 下标对应 face_0.png ~ face_11.png 的文件序号
    static readonly float[] faceAtX = { 0.485f, 0.492f, 0.50f, 0.492f, 0.50f, 0.50f, 0.486f, 0.498f, 0.44f, 0.50f, 0.51f, 0.50f };
    // 前五张是 Q 版动物：头大、眼睛占整张图比例高，按整图高度折算会整排偏到额头上去，
    // 这几个 y 是逐张按两眼连线量出来的，不要改回统一比例
    static readonly float[] faceAtY = { 0.250f, 0.276f, 0.215f, 0.266f, 0.203f, 0.179f, 0.219f, 0.285f, 0.255f, 0.430f, 0.254f, 0.258f };
    static readonly float[] faceAtW = { 0.40f, 0.42f, 0.46f, 0.52f, 0.46f, 0.42f, 0.30f, 0.38f, 0.26f, 0.24f, 0.22f, 0.44f };

    // ==== 骨架（骨链）====
    // 从脚底往上一条骨链：胯、腰、胸、颈、头、发尾。每个形象共用同一套骨架。
    // 三张表分别是：高度比例（脚底 0、头顶 1）、幅值权重、相位滞后（弧度）。
    // 摆的时候越靠上叠得越多、相位越晚 —— 脚稳住、胯先带、胸反向收、
    // 头晚半拍跟着、发尾再晚一点甩。以前整张图从头到尾一根正弦同步推，
    // 看着像一块软牌子在晃，不像有骨头在带。
    static readonly float[] rigY = { 0.20f, 0.42f, 0.62f, 0.80f, 0.90f, 1.00f };
    static readonly float[] rigW = { 0.34f, 0.42f, 0.52f, 0.62f, 0.86f, 1.00f };
    static readonly float[] rigL = { 0.00f, 0.55f, 1.15f, 1.75f, 2.30f, 2.90f };
    static readonly float rigSum = 3.36f;

    // 某个高度（0 脚底 ~ 1 头顶）被骨链推开多少，返回的是"幅值倍数"
    static float BoneSway(float fy, float ph)
    {
        float s2 = 0f;
        for (int b = 0; b < rigY.Length; b++)
        {
            if (fy <= rigY[b]) break;
            float w2 = (fy - rigY[b]) / (1f - rigY[b]);
            s2 += rigW[b] * w2 * w2 * (float)Math.Sin(ph - rigL[b]);
        }
        return s2 / rigSum;
    }

    static string appDirCache = null;
    // 程序目录可写就用它，不可写（如放在 Program Files）自动落到用户目录，保证拷到哪都能存记忆
    string AppDir()
    {
        if (appDirCache != null) return appDirCache;
        string d = Path.GetDirectoryName(Application.ExecutablePath);
        bool ok = false;
        try
        {
            string probe = Path.Combine(d, ".__dao_write_test");
            using (FileStream fs = new FileStream(probe, FileMode.Create, FileAccess.Write, FileShare.Read)) { }
            try { File.Delete(probe); } catch { }
            ok = true;
        }
        catch { ok = false; }
        if (!ok)
        {
            try
            {
                string alt = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Daodao");
                Directory.CreateDirectory(alt);
                d = alt;
            }
            catch { }
        }
        appDirCache = d;
        return d;
    }

    string[] ReadUtf8Lines(string p)
    {
        try { return File.ReadAllLines(p, new UTF8Encoding(false)); }
        catch { return new string[0]; }
    }

    // 把半透明边缘统一压成纯洋红，让窗口透明键能完全吃掉，避免轮廓外一圈洋红描边
    void KeyOut(Bitmap bmp)
    {
        try
        {
            Rectangle rc = new Rectangle(0, 0, bmp.Width, bmp.Height);
            BitmapData bd = bmp.LockBits(rc, ImageLockMode.ReadWrite, PixelFormat.Format32bppArgb);
            int len = bd.Stride * bmp.Height;
            byte[] buf = new byte[len];
            Marshal.Copy(bd.Scan0, buf, 0, len);
            int cut = 0;
            for (int i = 0; i + 3 < len; i += 4)
            {
                if (buf[i + 3] < 246)
                {
                    buf[i] = 255; buf[i + 1] = 0; buf[i + 2] = 255; buf[i + 3] = 255;
                    cut++;
                }
            }
            Marshal.Copy(buf, 0, bd.Scan0, len);
            bmp.UnlockBits(bd);
        }
        catch { }
    }

    Stream ResStream(string fileName)
    {
        try
        {
            System.Reflection.Assembly asm = System.Reflection.Assembly.GetExecutingAssembly();
            Stream s = asm.GetManifestResourceStream(fileName);
            if (s != null) return s;
            foreach (string rn in asm.GetManifestResourceNames())
                if (rn.EndsWith(fileName, StringComparison.OrdinalIgnoreCase))
                    return asm.GetManifestResourceStream(rn);
        }
        catch { }
        return null;
    }

    string[] ResLines(string fileName)
    {
        try
        {
            Stream s = ResStream(fileName);
            if (s == null) return new string[0];
            using (StreamReader sr = new StreamReader(s, System.Text.Encoding.UTF8))
            {
                string all = sr.ReadToEnd();
                return all.Replace("\r\n", "\n").Replace('\r', '\n').Split('\n');
            }
        }
        catch { return new string[0]; }
    }

    Bitmap MakeThumb(Stream s)
    {
        Bitmap bmp = null;
        using (Bitmap src = new Bitmap(s))
        {
            // 缩略高度 = 实际绘制高度（188）：加载时缩一次，之后一像素对一像素贴。
            // 原来缩到 256、绘制时再缩到 188，等于每帧二次重采样，一模一样的表情
            // 在 150% 缩放的屏幕上就是糊的，眼睫毛、嘴角这些一两像素的细线最先丢
            int th = 188;
            int tw = Math.Max(1, (int)(src.Width * (th / (float)src.Height)));
            bmp = new Bitmap(tw, th, PixelFormat.Format32bppArgb);
            using (Graphics gg = Graphics.FromImage(bmp))
            {
                gg.InterpolationMode = InterpolationMode.HighQualityBicubic;
                gg.Clear(Color.Transparent);
                gg.DrawImage(src, 0, 0, tw, th);
            }
        }
        // 以前这里把透明像素刷成洋红透明键，结果人物周围在场景上"打洞"，
        // 透出桌面/网页底色，看着就是一块白板。改成保留真 alpha，叠在场景上正常混合。
        return bmp;
    }

    // 单文件版：把内嵌的大脑钥匙、知识库与语音/翻译脚本释放到程序目录，
    // 这样 exe 单独拷到任何一台电脑，都有脑子、有知识、能听会说
    void EnsureAssets()
    {
        string[] names = { "key.txt", "知识库.txt", "hear.py", "hear_en.py", "trans.py", "voice.py", "play_audio.py", "github_learn.py", "记忆.txt", "我说的话.txt", "今日所学.txt", "更新日志.txt" };
        foreach (string n in names)
        {
            try
            {
                string t = Path.Combine(AppDir(), n);
                if (File.Exists(t)) continue;
                Stream s = ResStream(n);
                if (s == null) continue;
                using (Stream src = s)
                using (Stream dst = new FileStream(t, FileMode.Create, FileAccess.Write))
                {
                    src.CopyTo(dst);
                }
            }
            catch { }
        }
    }

    // 披风、长剑这两件道具改成贴图：python 画好的透明底 PNG 放在程序目录，
    // 比程序里现拼多边形像样得多，形状和配色也统一
    Bitmap capeImg, swordImg, capeWind;
    // 御剑姿势图：按形象分开存，有了就整张换掉，不再靠正面站姿配一把画出来的剑
    Dictionary<int, Bitmap> swordFlyMap = new Dictionary<int, Bitmap>();
    // 表情整图：每个形象最多四张（笑/难过/生气/睡着）。
    // 桌面尺寸下脸只有二三十像素，在上面画腮红、弧线、泪珠看着就是一团糊；
    // 有真表情图就直接整张换，表情是画师画的，跟衣服头发同源
    // v14 起不再用生成的表情图：AI 画出来的笑/难过/生气/睡着都不如原画脸上那一抹自然，
    // 2026-11-14 重做表情：每种情绪改用一整张真表情贴图，不再往脸上叠线条
    // 2026-11-16 晚：重新打开整张表情立绘。旧表情图的两个毛病都从素材根源上解决了 ——
    // 一是画布不一致：新表情图按原立绘逐像素对齐（差分验证全身轮廓重合），换表情身体不跳；
    // 二是图里带十字怒纹、泪滴、腮红贴纸：新图全部只有脸上的眉毛/眼睛/嘴在变，没有一个外挂符号。
    // 2026-11-18：程序画眉眼嘴的兜底（DrawFaceExpr）与手机端 face() 一起删了——那层线稿贴上去就是"插上去的笑脸哭脸"。缺表情图的形象保持原画的脸，表情只靠姿势与动作。
    static readonly bool UseExprArt = true;

    // v18：披风先撤掉。程序画的那块红布（贴图 + 程序画两版）在桌面尺寸下太假，
    // 等真做出像样的披风再穿。改成 false 之后：道具图不加载，飞的时候只画脚下一层气流，
    // 动作本身（腾空、倾斜、换海边日落景）都不变。
    static readonly bool UseCape = false;
    Dictionary<int, Bitmap[]> exprMap = new Dictionary<int, Bitmap[]>();
    // 笑的动态帧：exprMap 里的 happy 只是第一帧，再补三帧凑成一圈，
    // 笑的时候四帧轮着换，嘴和眼睛才是真的在动，不是一张图定在那儿
    Dictionary<int, Bitmap[]> laughMap = new Dictionary<int, Bitmap[]>();
    Bitmap swordFly = null;
    static bool dbgCape;

    // 场景背景也交给模型画：城市、乡野、海边、花丛四张整幅图，
    // 程序里只负责按窗口尺寸贴上去，别再用手绘线条凑
    Bitmap[] sceneImgs = new Bitmap[6];

    void LoadScenes()
    {
        // 用的是四边羽化过的版本（_v），贴出来是一块柔边的景，不是长方形画框
        string[] names = { "scene_city_v.png", "scene_field_v.png", "scene_sea_v.png", "scene_flower_v.png" };
        for (int i = 0; i < names.Length; i++)
        {
            sceneImgs[i] = LoadScene(names[i]);
        }
        sceneImgs[5] = LoadScene("scene_xianxia_v.png");   // 御剑专用
        sceneImgs[4] = LoadScene("scene_home_v.png");      // 屋里：客厅，自带一台电视
    }

    Bitmap LoadScene(string name)
    {
        try
        {
            string p = Path.Combine(AppDir(), name);
            if (!File.Exists(p))
            {
                try { File.AppendAllText(Path.Combine(AppDir(), "AI日志.txt"), "SCENE " + name + " MISSING " + p + "\r\n"); } catch { }
                return null;
            }
            using (Stream fs = new FileStream(p, FileMode.Open, FileAccess.Read))
            {
                using (Bitmap src = new Bitmap(fs))
                {
                    Bitmap bmp = new Bitmap(src.Width, src.Height, PixelFormat.Format32bppArgb);
                    using (Graphics gg = Graphics.FromImage(bmp))
                    {
                        // 必须留空底：场景图四边是羽化的透明边，铺黑底就把柔边盖死了
                        gg.Clear(Color.Transparent);
                        gg.CompositingMode = System.Drawing.Drawing2D.CompositingMode.SourceCopy;
                        gg.DrawImage(src, 0, 0, src.Width, src.Height);
                        gg.CompositingMode = System.Drawing.Drawing2D.CompositingMode.SourceOver;
                    }
                    try { File.AppendAllText(Path.Combine(AppDir(), "AI日志.txt"), "SCENE " + name + " OK " + bmp.Width + "x" + bmp.Height + "\r\n"); } catch { }
                    return bmp;
                }
            }
        }
        catch (Exception ex)
        {
            try { File.AppendAllText(Path.Combine(AppDir(), "AI日志.txt"), "SCENE " + name + " FAIL " + ex.Message + "\r\n"); } catch { }
            return null;
        }
    }

    void LoadProps()
    {
        if (UseCape)
        {
            capeImg = LoadProp("props_cape.png");
            capeWind = LoadProp("props_capewind.png");
        }
        swordImg = LoadProp("props_sword.png");
    }

    Bitmap LoadProp(string name)
    {
        try
        {
            string p = Path.Combine(AppDir(), name);
            if (!File.Exists(p))
            {
                try { File.AppendAllText(Path.Combine(AppDir(), "AI日志.txt"), "PROPS " + name + " MISSING " + p + "\r\n"); } catch { }
                return null;
            }
            using (Stream fs = new FileStream(p, FileMode.Open, FileAccess.Read))
            {
                using (Bitmap src = new Bitmap(fs))
                {
                    Bitmap bmp = new Bitmap(src.Width, src.Height, PixelFormat.Format32bppArgb);
                    using (Graphics gg = Graphics.FromImage(bmp))
                    {
                        gg.Clear(Color.Transparent);
                        gg.DrawImage(src, 0, 0, src.Width, src.Height);
                    }
                    try { File.AppendAllText(Path.Combine(AppDir(), "AI日志.txt"), "PROPS " + name + " OK " + bmp.Width + "x" + bmp.Height + "\r\n"); } catch { }
                    return bmp;
                }
            }
        }
        catch (Exception ex)
        {
            try { File.AppendAllText(Path.Combine(AppDir(), "AI日志.txt"), "PROPS " + name + " FAIL " + ex.Message + "\r\n"); } catch { }
            return null;
        }
    }

    void LoadFaces()
    {
        try
        {
            string fdir = Path.Combine(AppDir(), "faces");
            string dir = Path.Combine(AppDir(), "faces_cut4");
            if (!Directory.Exists(dir)) dir = fdir;
            string[] nameArr = ReadUtf8Lines(Path.Combine(fdir, "names.txt"));
            if (nameArr.Length == 0) nameArr = ResLines("names.txt");
            string[] voiceArr = ReadUtf8Lines(Path.Combine(fdir, "voices.txt"));
            if (voiceArr.Length == 0) voiceArr = ResLines("voices.txt");
            List<Bitmap> bl = new List<Bitmap>();
            List<string> nl = new List<string>();
            List<string> vl = new List<string>();
            List<int> il = new List<int>();
            for (int i = 0; i < 64; i++)
            {
                string fn = "face_" + i + ".png";
                Bitmap bmp = null;
                try
                {
                    Stream es = ResStream(fn);
                    if (es != null)
                    {
                        using (Stream s2 = es) { bmp = MakeThumb(s2); }
                    }
                    else
                    {
                        string p = Path.Combine(dir, fn);
                        if (!File.Exists(p)) continue;
                        using (Stream fs = new FileStream(p, FileMode.Open, FileAccess.Read))
                        {
                            bmp = MakeThumb(fs);
                        }
                    }
                }
                catch { bmp = null; }
                if (bmp == null) continue;
                bl.Add(bmp);
                il.Add(i);
                nl.Add((i < nameArr.Length && nameArr[i].Trim().Length > 0) ? nameArr[i].Trim() : ("形象" + i));
                vl.Add((i < voiceArr.Length && voiceArr[i].Trim().Length > 0) ? voiceArr[i].Trim() : "zh-CN-XiaoxiaoNeural");
            }
            if (bl.Count > 0)
            {
                faces = bl.ToArray();
                faceNames = nl.ToArray();
                faceVoices = vl.ToArray();
                faceFileIdx = il.ToArray();
                faceCount = faces.Length;
            }
        }
        catch { }
    }

    // 读整套姿势图：stand / wave / walk / cheer / sit
    // 5 张都是同一只形象、同一画布尺寸、脚底对齐，所以切换时只需要整体贴上去，
    // 不会出现"脸忽大忽小"或者"人突然跳位置"
    void LoadPoses()
    {
        try
        {
            string[] order = { "stand", "wave", "walk", "cheer", "sit" };
            Dictionary<int, Bitmap[]> map = new Dictionary<int, Bitmap[]>();
            for (int sp = 0; sp < 12; sp++)
            {
                List<Bitmap> bl = new List<Bitmap>();
                for (int i = 0; i < order.Length; i++)
                {
                    Bitmap bmp = null;
                    try
                    {
                        Stream es = ResStream("pose_" + sp + "_" + order[i] + ".png");
                        if (es != null)
                        {
                            // 姿势图已经是 152 高的显示尺寸，必须原样读进来，
                            // 不能再过一遍缩放：一缩放边缘就混出半透明，透明键把它染成粉紫描边
                            using (Stream s2 = es) { bmp = new Bitmap(s2); }
                        }
                        else
                        {
                            string p = Path.Combine(AppDir(), "_poses_dev" + sp, order[i] + ".png");
                            if (File.Exists(p))
                            {
                                using (Stream fs = new FileStream(p, FileMode.Open, FileAccess.Read))
                                {
                                    bmp = new Bitmap(fs);
                                }
                            }
                        }
                    }
                    catch { bmp = null; }
                    // 一套必须五张齐全才认，缺一张就当这个形象还没有动作
                    if (bmp == null) { bl.Clear(); break; }
                    bl.Add(bmp);
                }
                if (bl.Count == order.Length) map[sp] = bl.ToArray();
            }
            // 八帧走路：只有配了整套的形象才有，缺一张就整套不用
            for (int sp = 0; sp < 12; sp++)
            {
                Bitmap[] wf = new Bitmap[8];
                bool wok = true;
                for (int wi = 0; wi < 8; wi++)
                {
                    Bitmap wb = null;
                    try
                    {
                        Stream wes = ResStream("walk8_" + sp + "_" + (wi + 1) + ".png");
                        if (wes != null) { using (Stream ws2 = wes) { wb = new Bitmap(ws2); } }
                        else
                        {
                            string wp = Path.Combine(AppDir(), "_walk8_" + sp, "walk" + (wi + 1) + ".png");
                            if (File.Exists(wp))
                            {
                                using (Stream wfs = new FileStream(wp, FileMode.Open, FileAccess.Read))
                                {
                                    wb = new Bitmap(wfs);
                                }
                            }
                        }
                    }
                    catch { wb = null; }
                    if (wb == null) { wok = false; break; }
                    wf[wi] = wb;
                }
                if (wok) walkMap[sp] = wf;
            }
            // 御剑：每个形象最多一张踩剑姿势图，有就用真图，没有就退回程序画的那把剑
            for (int sp2 = 0; sp2 < 12; sp2++)
            {
                Bitmap sf = null;
                try
                {
                    Stream sfs = ResStream("swordfly_" + sp2 + ".png");
                    if (sfs != null) { using (Stream s2 = sfs) { sf = new Bitmap(s2); } }
                    else
                    {
                        string sfp = Path.Combine(AppDir(), "_swordfly", sp2 + ".png");
                        if (File.Exists(sfp))
                        {
                            using (Stream s4 = new FileStream(sfp, FileMode.Open, FileAccess.Read))
                            {
                                sf = new Bitmap(s4);
                            }
                        }
                    }
                }
                catch { sf = null; }
                if (sf != null) swordFlyMap[sp2] = sf;
            }

            // 表情整图：expr_{sp}_{key}.png，四张齐了才登记
            // 2026-11-18（v58）：4/5/9/10 这四只重新按新人形立绘做了四套表情整图，
            // 五官是真改了（开心弯眼上扬、难过垂眼、生气压眉、睡着闭眼），不再贴任何符号，
            // 所以 12 只形象现在都能换表情整图了
            string[] exprKeys = new string[] { "happy", "sad", "angry", "sleep" };
            // v0.107：表情图只在「同一个角色、同一画风、整身」的五只形象上换。
            // 0 橘猫 / 1 白兔 / 2 狐狸 / 3 熊猫的表情原来是动物卡通，6 蓝发和 11 机械是另一种画风，
            // 7 黑发只有头肩特写——这些一换表情就会"少女一秒变熊猫"，宁可不换。
            bool[] exprOk = new bool[14];
            exprOk[4] = true; exprOk[5] = true; exprOk[8] = true; exprOk[9] = true; exprOk[10] = true;
            for (int sp3 = 0; UseExprArt && sp3 < 12; sp3++)
            {
                if (!exprOk[sp3]) continue;
                Bitmap[] ee = new Bitmap[exprKeys.Length];
                bool eok = true;
                for (int ei = 0; ei < exprKeys.Length; ei++)
                {
                    Bitmap eb = null;
                    try
                    {
                        // 2026-11-19（v60）：先看程序目录 _expr 里的整图，再回落到内嵌资源。
                        // 这么改是为了换表情不用重打包——画好的整图丢进 _expr 就生效，
                        // 但脸和眼睛仍是画在图里，不在脸上贴任何符号。
                        string ep2 = Path.Combine(AppDir(), "_expr", exprKeys[ei] + "_" + sp3 + ".png");
                        if (File.Exists(ep2))
                        {
                            using (Stream s7 = new FileStream(ep2, FileMode.Open, FileAccess.Read))
                            {
                                eb = MakeThumb(s7);
                            }
                        }
                        if (eb == null)
                        {
                            Stream es = ResStream("expr_" + sp3 + "_" + exprKeys[ei] + ".png");
                            if (es != null) { using (Stream s5 = es) { eb = MakeThumb(s5); } }
                            else
                            {
                                string ep = Path.Combine(AppDir(), "_expr", exprKeys[ei] + "_" + sp3 + ".png");
                                if (File.Exists(ep))
                                {
                                    using (Stream s6 = new FileStream(ep, FileMode.Open, FileAccess.Read))
                                    {
                                        eb = MakeThumb(s6);
                                    }
                                }
                            }
                        }
                    }
                    catch (Exception ex) { eb = null; try { File.AppendAllText(Path.Combine(AppDir(), "_exprerr.txt"), "sp" + sp3 + "_" + exprKeys[ei] + " : " + ex.GetType().Name + " " + ex.Message + "\r\n", Encoding.UTF8); } catch { } }
                    if (eb == null) { eok = false; break; }
                    ee[ei] = eb;
                }
                if (eok) exprMap[sp3] = ee;
            }

            // 笑要动：happy 那一张当第一帧，另配 laugh2/3/4，四帧齐了才登记
            for (int sp4 = 0; UseExprArt && sp4 < 12; sp4++)
            {
                Bitmap[] la = new Bitmap[4];
                if (exprMap.ContainsKey(sp4)) la[0] = exprMap[sp4][0];
                if (la[0] == null) continue;
                bool lok = true;
                for (int li = 1; li < 4; li++)
                {
                    Bitmap lb = null;
                    try
                    {
                        Stream ls = ResStream("expr_" + sp4 + "_laugh" + (li + 1) + ".png");
                        if (ls != null) { using (Stream s7 = ls) { lb = MakeThumb(s7); } }
                        else
                        {
                            string lp = Path.Combine(AppDir(), "_expr", "laugh" + (li + 1) + "_" + sp4 + ".png");
                            if (File.Exists(lp))
                            {
                                using (Stream s8 = new FileStream(lp, FileMode.Open, FileAccess.Read))
                                {
                                    lb = MakeThumb(s8);
                                }
                            }
                        }
                    }
                    catch { lb = null; }
                    if (lb == null) { lok = false; break; }
                    la[li] = lb;
                }
                if (lok) laughMap[sp4] = la;
            }
            if (map.Count == 0) return;
            poseMap = map;
            List<int> kinds = new List<int>();
            foreach (int k in map.Keys) kinds.Add(k);
            kinds.Sort();
            poseKinds = kinds.ToArray();
            ApplyPose(poseKinds[0]);
        }
        catch { }
    }

    // 把当前要用的姿势集切成某个形象那一套
    void ApplyPose(int sp)
    {
        // 御剑图先跟着形象换，哪怕这个形象没有整套姿势图，也不该沿用上一个形象的剑
        swordFly = null;
        // 换形象先把这个形象自己的姿势和八帧清空：以前这里直接 return，
        // 上一个形象的姿势集会赖着不走，切到剑客这种没有整套姿势图的形象时，
        // 走起来用的是别人的八帧，看着就是"人换了、动作还是别人的"
        poses = null;
        poseOwner = -1;
        walkFrames = null;
        if (swordFlyMap != null && swordFlyMap.Count > 0)
        {
            Bitmap sfUse = null;
            if (swordFlyMap.TryGetValue(sp, out sfUse)) swordFly = sfUse;
        }
        // 八帧走路跟整套姿势图分开取：剑客这类形象只有八帧、没有整套姿势图，
        // 以前这块跟在 poseMap 后面，没整套姿势图就一起没了，八帧一次都用不上
        Bitmap[] wset0 = null;
        if (walkMap != null && walkMap.TryGetValue(sp, out wset0)) walkFrames = wset0;
        if (poseMap == null) return;
        Bitmap[] set2 = null;
        if (!poseMap.TryGetValue(sp, out set2)) return;
        poses = set2;
        poseOwner = sp;
        poseIdx = 0;
        posePrev = 0;
    }

    string CurName()
    {
        if (faceCount > 0) return faceNames[species % faceCount];
        return speciesName[species % speciesName.Length];
    }

    static DesktopPet Self;

    // 给 HTTP 那边（SyncServer 是另一个类）一个能调的跨网同步入口
    public static string ForgetText(string t)
    {
        try { return Self == null ? "实例还没好" : Self.MemForget(t); }
        catch (Exception ex) { return "忘掉失败：" + ex.Message; }
    }

    public static string SyncNetText()
    {
        try
        {
            if (Self == null) return "SYNCERR|实例还没好";
            return "SYNC|" + Self.SyncPullMerge() + "|" + Self.SyncPush();
        }
        catch (Exception ex) { return "SYNCERR|" + ex.Message; }
    }

    // 外面（豆包、手机、命令行）让它说一句
    public static void Push(string t)
    {
        try
        {
            DesktopPet me = Self;
            if (me == null || t == null) return;
            string s = t.Trim();
            if (s.Length == 0) return;
            me.BeginInvoke(new MethodInvoker(delegate() { me.SayAs(s, me.CurVoice()); }));
        }
        catch { }
    }

    // ===== 记事本：主人说一声就登记，到点自己开口提醒 =====
    // 文件格式：每行 id \t 时间(yyyy-MM-dd HH:mm) \t 完成(0/1) \t 已预告(0/1) \t 内容
    static string NoteFile() { try { return Path.Combine(Path.GetDirectoryName(Application.ExecutablePath), "记事本.txt"); } catch { return "记事本.txt"; } }

    static string[] NoteLines()
    {
        try
        {
            string p = NoteFile();
            if (!File.Exists(p)) return new string[0];
            return File.ReadAllLines(p, Encoding.UTF8);
        }
        catch { return new string[0]; }
    }

    static Dictionary<string, string> ParseQuery(string query)
    {
        Dictionary<string, string> q = new Dictionary<string, string>();
        if (query == null || query.Length == 0) return q;
        string[] kv = query.Split('&');
        for (int i = 0; i < kv.Length; i++)
        {
            if (kv[i].Length == 0) continue;
            string k = kv[i], v = "";
            int eq = k.IndexOf('=');
            if (eq >= 0) { v = k.Substring(eq + 1); k = k.Substring(0, eq); }
            try { q[k] = Uri.UnescapeDataString(v.Replace('+', ' ')); } catch { q[k] = v; }
        }
        return q;
    }

    static int CnNum(string s)
    {
        if (s == null || s.Length == 0) return -1;
        Dictionary<string, int> m = new Dictionary<string, int>();
        m["零"] = 0; m["一"] = 1; m["二"] = 2; m["两"] = 2; m["三"] = 3; m["四"] = 4;
        m["五"] = 5; m["六"] = 6; m["七"] = 7; m["八"] = 8; m["九"] = 9; m["十"] = 10;
        m["十一"] = 11; m["十二"] = 12; m["十三"] = 13; m["十四"] = 14; m["十五"] = 15;
        m["十六"] = 16; m["十七"] = 17; m["十八"] = 18; m["十九"] = 19; m["二十"] = 20;
        m["二十一"] = 21; m["二十二"] = 22; m["二十三"] = 23; m["半"] = 30;
        if (m.ContainsKey(s)) return m[s];
        try { return int.Parse(s); } catch { return -1; }
    }

    // 从一句话里读出时间：「明天九点」「下午三点半」「11月22号早上7:30」「2026-11-22 09:00」
    static DateTime ParseWhen(string raw, out string rest)
    {
        rest = raw == null ? "" : raw.Trim();
        DateTime now = DateTime.Now;
        DateTime day = now.Date;
        bool hasDay = false;
        string s = rest;
        try
        {
            Match m1 = Regex.Match(s, @"(\d{4})-(\d{1,2})-(\d{1,2})\s*(\d{1,2})[:：](\d{1,2})?");
            if (m1.Success)
            {
                int y = int.Parse(m1.Groups[1].Value), mo = int.Parse(m1.Groups[2].Value), da = int.Parse(m1.Groups[3].Value);
                int hh = int.Parse(m1.Groups[4].Value), mi = m1.Groups[5].Success ? int.Parse(m1.Groups[5].Value) : 0;
                rest = (s.Substring(0, m1.Index) + " " + s.Substring(m1.Index + m1.Length)).Trim();
                return new DateTime(y, mo, da, hh, mi, 0);
            }
            if (s.IndexOf("大后天") >= 0) { day = day.AddDays(3); hasDay = true; s = s.Replace("大后天", " "); }
            else if (s.IndexOf("后天") >= 0) { day = day.AddDays(2); hasDay = true; s = s.Replace("后天", " "); }
            else if (s.IndexOf("明天") >= 0) { day = day.AddDays(1); hasDay = true; s = s.Replace("明天", " "); }
            else if (s.IndexOf("今天") >= 0) { hasDay = true; s = s.Replace("今天", " "); }
            Match m2 = Regex.Match(s, @"(\d{1,2})月(\d{1,2})[日号]");
            if (m2.Success)
            {
                int mo = int.Parse(m2.Groups[1].Value), da = int.Parse(m2.Groups[2].Value);
                int y = now.Year;
                DateTime cand = new DateTime(y, mo, da);
                if (cand.Date < now.Date) cand = cand.AddYears(1);
                day = cand.Date; hasDay = true;
                s = s.Substring(0, m2.Index) + " " + s.Substring(m2.Index + m2.Length);
            }
            string[] cnNums = { "十一", "十二", "十", "一", "二", "三", "四", "五", "六", "七", "八", "九", "十" };
            Match m3 = Regex.Match(s, @"(凌晨|早上|上午|中午|下午|傍晚|晚上|晚间)?\s*(\d{1,2}|[零一二三四五六七八九十]{1,3})\s*(?:点|时|[:：])\s*(半|\d{1,2}|[零一二三四五六七八九十]{1,3})?");
            if (!m3.Success)
            {
                // 没有时间就默认一小时后
                rest = rest.Trim();
                return now.AddHours(1);
            }
            string part = m3.Groups[1].Value;
            int hh2 = CnNum(m3.Groups[2].Value);
            int mi2 = 0;
            string mm = m3.Groups[3].Value;
            if (mm == "半") mi2 = 30;
            else if (mm.Length > 0) { int t2 = CnNum(mm.Replace("分", "")); if (t2 > 0) mi2 = t2; }
            if (hh2 < 0) hh2 = 9;
            if ((part == "下午" || part == "傍晚" || part == "晚上" || part == "晚间") && hh2 < 12) hh2 += 12;
            if (part == "中午" && hh2 < 12) hh2 = 12;
            if (hh2 > 23) hh2 = 23;
            DateTime when = day.AddHours(hh2).AddMinutes(mi2);
            if (!hasDay && when <= now) when = when.AddDays(1);
            rest = (s.Substring(0, m3.Index) + " " + s.Substring(m3.Index + m3.Length)).Trim();
            return when;
        }
        catch { return now.AddHours(1); }
    }

    // 重复提醒：每天 / 每周X / 每月X号 → "D" / "W1..W7" / "M23"
    static string StripRepeat(ref string s)
    {
        string rep = "";
        try
        {
            if (s.IndexOf("每天") >= 0 || s.IndexOf("每日") >= 0)
            {
                rep = "D";
                s = s.Replace("每天", " ").Replace("每日", " ");
                return rep;
            }
            Match w = Regex.Match(s, @"每(?:周|星期|礼拜)([一二三四五六日天1-7])?");
            if (w.Success)
            {
                string d = w.Groups[1].Value;
                int n = 1;
                if (d == "一") n = 1; else if (d == "二") n = 2; else if (d == "三") n = 3; else if (d == "四") n = 4;
                else if (d == "五") n = 5; else if (d == "六") n = 6; else if (d == "日" || d == "天") n = 7;
                else if (d.Length > 0) { try { n = int.Parse(d); } catch { n = 1; } }
                if (n < 1 || n > 7) n = 1;
                rep = "W" + n;
                s = s.Substring(0, w.Index) + " " + s.Substring(w.Index + w.Length);
                return rep;
            }
            Match m = Regex.Match(s, @"每(?:个)?月([0-9]{1,2}|[一二三四五六七八九十]{1,3})[日号]?");
            if (m.Success)
            {
                int day = CnNum(m.Groups[1].Value);
                if (day >= 1 && day <= 31) rep = "M" + day;
                s = s.Substring(0, m.Index) + " " + s.Substring(m.Index + m.Length);
                return rep;
            }
        }
        catch { }
        return rep;
    }

    // 下一次是什么时候
    static DateTime NextWhen(DateTime dt, string rep)
    {
        try
        {
            if (rep == null || rep.Length == 0) return dt;
            char c = rep[0];
            if (c == 'D') return dt.AddDays(1);
            if (c == 'W')
            {
                int n = 1;
                try { n = int.Parse(rep.Substring(1)); } catch { n = 1; }
                DateTime d = dt.AddDays(1);
                for (int i = 0; i < 8; i++)
                {
                    if ((int)d.DayOfWeek == (n % 7)) break;
                    d = d.AddDays(1);
                }
                return d;
            }
            if (c == 'M')
            {
                int day = 1;
                try { day = int.Parse(rep.Substring(1)); } catch { day = 1; }
                DateTime d = dt.AddMonths(1);
                int dim = DateTime.DaysInMonth(d.Year, d.Month);
                if (day > dim) day = dim;
                return new DateTime(d.Year, d.Month, day, dt.Hour, dt.Minute, 0);
            }
        }
        catch { }
        return dt;
    }

    // 把「今天的这个点」对齐到重复规则的下一次
    static DateTime AlignToRepeat(DateTime when, string rep)
    {
        try
        {
            DateTime now = DateTime.Now;
            if (rep[0] == 'D')
            {
                if (when <= now) return when.AddDays(1);
                return when;
            }
            if (rep[0] == 'W')
            {
                int n = 1;
                try { n = int.Parse(rep.Substring(1)); } catch { n = 1; }
                DateTime d = when.Date;
                for (int i = 0; i < 8; i++)
                {
                    if ((int)d.DayOfWeek == (n % 7)) break;
                    d = d.AddDays(1);
                }
                DateTime r = d.AddHours(when.Hour).AddMinutes(when.Minute);
                if (r <= now) r = r.AddDays(7);
                return r;
            }
            if (rep[0] == 'M')
            {
                int day = 1;
                try { day = int.Parse(rep.Substring(1)); } catch { day = 1; }
                DateTime d = new DateTime(when.Year, when.Month, 1);
                int dim = DateTime.DaysInMonth(d.Year, d.Month);
                d = new DateTime(d.Year, d.Month, day > dim ? dim : day, when.Hour, when.Minute, 0);
                while (d <= now)
                {
                    d = d.AddMonths(1);
                    dim = DateTime.DaysInMonth(d.Year, d.Month);
                    if (day > dim) d = new DateTime(d.Year, d.Month, dim, when.Hour, when.Minute, 0);
                }
                return d;
            }
        }
        catch { }
        return when;
    }

    // 人话里的重复说法
    static string RepText(string rep)
    {
        if (rep == null || rep.Length == 0) return "";
        if (rep[0] == 'D') return "每天";
        if (rep[0] == 'W')
        {
            string[] wd = { "", "周一", "周二", "周三", "周四", "周五", "周六", "周日" };
            int n = 1; try { n = int.Parse(rep.Substring(1)); } catch { n = 1; }
            return "每" + wd[n < 1 || n > 7 ? 1 : n];
        }
        if (rep[0] == 'M') return "每月" + rep.Substring(1) + "号";
        return "";
    }

    // 标完成：普通条目直接置 done；重复条目（D/W/M）滚到下一次，不然这条就永远死了
    static string RollDone(string[] f)
    {
        string rep = f.Length >= 6 ? f[5].Trim() : "";
        string when = f[1], done = "1", warned = f[3];
        if (rep.Length > 0)
        {
            DateTime dt = DateTime.MinValue;
            try { dt = DateTime.ParseExact(f[1], "yyyy-MM-dd HH:mm", null); } catch { }
            if (dt != DateTime.MinValue)
            {
                DateTime now = DateTime.Now;
                DateTime nx = NextWhen(dt, rep);
                for (int k = 0; k < 40 && nx <= now; k++) nx = NextWhen(nx, rep);
                when = nx.ToString("yyyy-MM-dd HH:mm");
            }
            done = "0"; warned = "0";
        }
        return f[0] + "\t" + when + "\t" + done + "\t" + warned + "\t" + f[4] + (rep.Length > 0 ? "\t" + rep : "");
    }

    public static string NoteApi(string query)
    {
        Dictionary<string, string> q = ParseQuery(query);
        string op = q.ContainsKey("op") ? q["op"] : "list";
        string[] lines = NoteLines();
        if (op == "list")
        {
            StringBuilder sb = new StringBuilder("OK\n");
            for (int i = 0; i < lines.Length; i++) { if (lines[i].Trim().Length > 0) sb.AppendLine(lines[i]); }
            return sb.ToString().TrimEnd();
        }
        if (op == "done" || op == "del")
        {
            string id = q.ContainsKey("id") ? q["id"] : "";
            if (id.Length == 0) return "ERR|没有 id";
            List<string> keep = new List<string>();
            bool hit = false;
            for (int i = 0; i < lines.Length; i++)
            {
                string[] f = lines[i].Split('\t');
                if (f.Length >= 5 && f[0] == id)
                {
                    hit = true;
                    if (op == "done") keep.Add(RollDone(f));
                    continue;
                }
                if (lines[i].Trim().Length > 0) keep.Add(lines[i]);
            }
            if (!hit) return "ERR|没有这条";
            try { File.WriteAllLines(NoteFile(), keep.ToArray(), new UTF8Encoding(false)); } catch (Exception ex) { return "ERR|" + ex.Message; }
            return "OK";
        }
        if (op == "add")
        {
            string text = q.ContainsKey("text") ? q["text"].Trim() : "";
            if (text.Length == 0) return "ERR|没有内容";
            string rest = text;
            string trig = "记一下|记一条|记下|帮我记|帮我记一下|提醒我|待办|记住";
            string snip = rest;
            try { snip = Regex.Replace(rest, "^(" + trig + ")[,，:：\\s]*", ""); } catch { }
            string rep = StripRepeat(ref snip);
            DateTime when;
            string what;
            if (q.ContainsKey("when") && q["when"].Length > 0)
            {
                DateTime.TryParse(q["when"], out when);
                what = snip.Trim();
                if (when == DateTime.MinValue) when = ParseWhen(snip, out what);
            }
            else when = ParseWhen(snip, out what);
            if (what.Length == 0) what = snip.Trim();
            if (rep.Length > 0) when = AlignToRepeat(when, rep);   // 先按重复规则把日期对齐到下一次
            int maxId = 0;
            for (int i = 0; i < lines.Length; i++)
            {
                string[] f = lines[i].Split('\t');
                int id2 = 0;
                if (f.Length >= 1) int.TryParse(f[0], out id2);
                if (id2 > maxId) maxId = id2;
            }
            string newLine = (maxId + 1) + "\t" + when.ToString("yyyy-MM-dd HH:mm") + "\t0\t0\t" + what.Replace("\t", " ").Replace("\n", " ");
            if (rep.Length > 0) newLine += "\t" + rep;
            List<string> all = new List<string>();
            for (int i = 0; i < lines.Length; i++) if (lines[i].Trim().Length > 0) all.Add(lines[i]);
            all.Add(newLine);
            try { File.WriteAllLines(NoteFile(), all.ToArray(), new UTF8Encoding(false)); } catch (Exception ex) { return "ERR|" + ex.Message; }
            // 登记成功先在屏幕上回应一句，不吵
            try { DesktopPet me = Self; if (me != null) me.BeginInvoke(new MethodInvoker(delegate() { me.Say("记下了，" + (rep.Length > 0 ? RepText(rep) + "，从" : "") + when.ToString("M月d日H点m分") + "，" + what); })); } catch { }
            return "OK|" + (maxId + 1) + "|" + when.ToString("yyyy-MM-dd HH:mm") + "|" + what + (rep.Length > 0 ? "|" + RepText(rep) : "");
        }
        if (op == "today" || op == "read")
        {
            // 念一遍待办：逾期的、今天的、明天的分开说
            DateTime now = DateTime.Now;
            DateTime today = now.Date;
            List<string> od = new List<string>();
            List<string> td = new List<string>();
            List<string> tm = new List<string>();
            for (int i = 0; i < lines.Length; i++)
            {
                string[] f = lines[i].Split('\t');
                if (f.Length < 5 || f[2] == "1") continue;
                DateTime dt = DateTime.MinValue;
                try { dt = DateTime.ParseExact(f[1], "yyyy-MM-dd HH:mm", null); } catch { }
                if (dt == DateTime.MinValue) { td.Add(f[4]); continue; }
                string hm = dt.Hour + "点" + (dt.Minute == 0 ? "" : dt.Minute + "分");
                string mark = f.Length >= 6 && f[5].Trim().Length > 0 ? "（" + RepText(f[5].Trim()) + "）" : "";
                if (dt.Date < today) od.Add("逾期：" + f[4] + mark);
                else if (dt.Date == today) td.Add(hm + " " + f[4] + mark);
                else if (dt.Date == today.AddDays(1)) tm.Add(hm + " " + f[4] + mark);
            }
            if (od.Count + td.Count + tm.Count == 0) return "OK|记事本上现在没有待办的事。";
            StringBuilder sb = new StringBuilder("OK|");
            if (od.Count > 0) { sb.Append("有" + od.Count + "件逾期了："); for (int i = 0; i < od.Count; i++) sb.Append(od[i] + (i == od.Count - 1 ? "。" : "；")); }
            if (td.Count > 0) { sb.Append("今天有" + td.Count + "件："); for (int i = 0; i < td.Count; i++) sb.Append(td[i] + (i == td.Count - 1 ? "。" : "；")); }
            if (tm.Count > 0) { sb.Append("明天有" + tm.Count + "件："); for (int i = 0; i < tm.Count; i++) sb.Append(tm[i] + (i == tm.Count - 1 ? "。" : "；")); }
            return sb.ToString();
        }
        if (op == "setmail" || op == "getmail" || op == "mailinfo")
        {
            string cfg = Path.Combine(Path.GetDirectoryName(Application.ExecutablePath), "通知.ini");
            string to = "";
            if (File.Exists(cfg))
            {
                string[] ls = File.ReadAllLines(cfg, Encoding.UTF8);
                for (int i = 0; i < ls.Length; i++)
                {
                    string ln = ls[i].Trim();
                    if (ln.StartsWith("#")) continue;
                    int eq = ln.IndexOf('=');
                    if (eq > 0 && ln.Substring(0, eq).Trim().ToLower() == "to") to = ln.Substring(eq + 1).Trim();
                }
            }
            if (op == "getmail") return "OK|" + (to.Length == 0 ? "还没设收件邮箱" : to);
            if (op == "mailinfo")
            {
                // 只报发件账号和通道，不吐授权码
                string user = "", srv = "", prt = "";
                string mc = Path.Combine(Path.GetDirectoryName(Application.ExecutablePath), ".mail_config");
                if (File.Exists(mc))
                {
                    string[] ml = File.ReadAllLines(mc, Encoding.UTF8);
                    string p0 = "", p1 = "", p2 = "";
                    for (int i = 0; i < ml.Length; i++)
                    {
                        string ln = ml[i].Trim();
                        if (ln.Length == 0 || ln.StartsWith("#")) continue;
                        int eq = ln.IndexOf('=');
                        if (eq > 0)
                        {
                            string k = ln.Substring(0, eq).Trim().ToLower();
                            string v = ln.Substring(eq + 1).Trim();
                            if (k == "user" || k == "from") user = v;
                            if (k == "smtp") srv = v;
                            if (k == "port") prt = v;
                        }
                        else if (p0.Length == 0) p0 = ln;
                        else if (p1.Length == 0) p1 = ln;
                        else if (p2.Length == 0) p2 = ln;
                    }
                    if (user.Length == 0) user = p0;
                    if (srv.Length == 0 && p2.Length > 0) { int c = p2.IndexOf(':'); srv = c > 0 ? p2.Substring(0, c) : p2; if (c > 0) prt = p2.Substring(c + 1); }
                }
                if (user.Length == 0) return "OK|发件账号还没配（.mail_config 缺内容）";
                string chan = srv.Length > 0 ? (srv + (prt.Length > 0 ? ":" + prt : "")) : "自动（按发件域名选）";
                return "OK|发件 " + user + "｜通道 " + chan;
            }
            // 收件人支持多个：逗号/分号/顿号/空格分隔，A. 覆盖 B. add=1 追加 C. clear=1 清空
            if (q.ContainsKey("clear") && q["clear"] == "1")
            {
                string c2 = HeaderMailCfg();
                try { File.WriteAllText(cfg, c2, new UTF8Encoding(false)); } catch (Exception ex) { return "ERR|" + ex.Message; }
                return "OK|收件人清空了，以后只在本机说话";
            }
            string want = q.ContainsKey("to") ? q["to"].Trim() : "";
            List<string> seg = new List<string>();
            string cur = "";
            for (int i = 0; i < want.Length; i++)
            {
                char ch = want[i];
                if (ch == ',' || ch == ';' || ch == '，' || ch == '；' || ch == '、' || ch == ' ' || ch == '\t')
                {
                    if (cur.Length > 0) { seg.Add(cur); cur = ""; }
                }
                else cur += ch;
            }
            if (cur.Length > 0) seg.Add(cur);
            List<string> got = new List<string>();
            for (int i = 0; i < seg.Count; i++)
            {
                string one = seg[i].Trim();
                int at = one.IndexOf('@');
                if (at <= 0) continue;
                if (one.IndexOf('.', at) <= at + 1) continue;
                if (one.IndexOf(' ') >= 0) continue;
                bool dup = false;
                for (int k = 0; k < got.Count; k++) if (got[k].ToLower() == one.ToLower()) dup = true;
                if (!dup) got.Add(one);
            }
            if (got.Count == 0) return "ERR|邮箱格式不对：" + want;
            bool isAdd = q.ContainsKey("add") && q["add"] == "1";
            if (isAdd && to.Length > 0)
            {
                string[] olds = to.Replace('；', ',').Replace(';', ',').Split(',');
                for (int i = 0; i < olds.Length; i++)
                {
                    string one = olds[i].Trim();
                    if (one.Length == 0) continue;
                    bool dup = false;
                    for (int k = 0; k < got.Count; k++) if (got[k].ToLower() == one.ToLower()) dup = true;
                    if (!dup) got.Add(one);
                }
            }
            string joined = "";
            for (int i = 0; i < got.Count; i++) joined += (i == 0 ? "" : ",") + got[i];
            string content = "# 道 记事本的通知通道：到点除了本机说话，还发一封邮件到下面这些地址。\n" +
                "# 发件账号在 F:\\Daodao\\.mail_config（可换任意服务商：qq/163/126/gmail/outlook/企业邮箱 等），这里只管收件人。\n" +
                "# 收件人由手机持有人自己定，可以多个，用英文逗号隔开；说「提醒发到 a@x.com」覆盖，说「也发到/加上 b@y.com」追加。\n" +
                "to=" + joined + "\n";
            try { File.WriteAllText(cfg, content, new UTF8Encoding(false)); } catch (Exception ex) { return "ERR|" + ex.Message; }
            return "OK|" + joined;
        }
        if (op == "doneby" || op == "delby")
        {
            // 说「这条做完了 / 把开会删掉」：按关键字找到那条待办，标记完成或删掉
            string raw = q.ContainsKey("text") ? q["text"].Trim() : (q.ContainsKey("key") ? q["key"].Trim() : "");
            if (raw.Length == 0) return "ERR|要告诉我哪一条";
            string key = raw;
            try
            {
                key = Regex.Replace(key, "把|帮我|请|这条|那条|一下|标记|已经|算|做完了|完成了|办完了|弄完了|搞定|删掉|删除|去掉|取消|别再提醒|不用提醒|了|吧|。|，", "");
            }
            catch { }
            key = key.Trim();
            int hitId = 0, hitAt = -1;
            string hitText = "";
            int bestDone = 2;
            DateTime bestTime = DateTime.MaxValue;
            if (key.Length == 0) return "ERR|没说清楚是哪一条";
            // 「第 2 条」这种直接按序号来
            Match num = Regex.Match(raw, @"第\s*([0-9]{1,3}|[一二三四五六七八九十]{1,3})\s*条");
            int wantId = num.Success ? CnNum(num.Groups[1].Value) : -1;
            for (int i = 0; i < lines.Length; i++)
            {
                string[] f = lines[i].Split('\t');
                if (f.Length < 5) continue;
                if (op == "doneby" && f[2] == "1") continue;   // 已完成的不用再标；删的话允许删已完成的记录
                bool ok = false;
                if (wantId > 0) { int fid = 0; int.TryParse(f[0], out fid); ok = fid == wantId; }
                else ok = f[4].IndexOf(key, StringComparison.OrdinalIgnoreCase) >= 0;
                if (!ok) continue;
                // 同名的不止一条时挑「离现在最近还没做的」，按文件行序会改错条
                DateTime dt2 = DateTime.MaxValue;
                try { dt2 = DateTime.ParseExact(f[1], "yyyy-MM-dd HH:mm", null); } catch { }
                int dn = f[2] == "1" ? 1 : 0;
                int fid2 = 0;
                int.TryParse(f[0], out fid2);
                if (hitAt < 0 || dn < bestDone || (dn == bestDone && dt2 < bestTime))
                {
                    hitId = fid2;
                    hitAt = i; hitText = f[4];
                    bestDone = dn; bestTime = dt2;
                }
            }
            if (hitAt < 0) return "ERR|记事本里没找到「" + (key.Length > 0 ? key : raw) + "」这条待办";
            string hitNew = "";
            List<string> keep2 = new List<string>();
            for (int i = 0; i < lines.Length; i++)
            {
                if (i == hitAt)
                {
                    if (op == "doneby")
                    {
                        string[] f = lines[i].Split('\t');
                        string nl = RollDone(f);
                        keep2.Add(nl);
                        hitNew = nl;
                    }
                    continue;
                }
                if (lines[i].Trim().Length > 0) keep2.Add(lines[i]);
            }
            try { File.WriteAllLines(NoteFile(), keep2.ToArray(), new UTF8Encoding(false)); } catch (Exception ex) { return "ERR|" + ex.Message; }
            // 重复项做完后会滚到下一次，把新时间一起回给页面，它能接着说「下次什么时候」
            string extra = "";
            if (hitNew.Length > 0)
            {
                string[] nf = hitNew.Split('\t');
                if (nf.Length >= 6 && nf[2] == "0") extra = "|" + nf[1] + "|" + RepText(nf[5].Trim());
            }
            return "OK|" + hitId + "|" + hitText + extra;
        }
        if (op == "mailtest")
        {
            // 先看有没有收件人，空着就直说，别让人以为是通道坏了
            string to = "";
            try
            {
                string cfg = Path.Combine(Path.GetDirectoryName(Application.ExecutablePath), "通知.ini");
                if (File.Exists(cfg))
                {
                    string[] ls = File.ReadAllLines(cfg, Encoding.UTF8);
                    for (int i = 0; i < ls.Length; i++)
                    {
                        string ln = ls[i].Trim();
                        if (ln.StartsWith("#")) continue;
                        int eq = ln.IndexOf('=');
                        if (eq > 0 && ln.Substring(0, eq).Trim().ToLower() == "to") to = ln.Substring(eq + 1).Trim();
                    }
                }
            }
            catch { }
            if (to.Length == 0) return "MAILFAIL|还没设收件邮箱，先说一句「提醒发到 xxx@qq.com」";
            bool ok = TryMail("道的提醒测试", "这条是测试邮件，收到说明绑定好了。" + DateTime.Now.ToString("yyyy-MM-dd HH:mm"));
            return ok ? "MAILOK" : "MAILFAIL|通知.ini 没配好或发信被拒";
        }
        return "ERR|不懂这个 op";
    }

    // 通知.ini 的空模板（备注 + 空收件人）
    static string HeaderMailCfg()
    {
        return "# 道 记事本的通知通道：到点除了本机说话，还发一封邮件到下面这些地址。\n" +
            "# 发件账号在 F:\\Daodao\\.mail_config（可换任意服务商：qq/163/126/gmail/outlook/企业邮箱 等），这里只管收件人。\n" +
            "# 收件人由手机持有人自己定，可以多个，用英文逗号隔开；说「提醒发到 a@x.com」覆盖，说「也发到/加上 b@y.com」追加。\n" +
            "to=\n";
    }

    // 到点提醒：提前十分钟预告一次，到点播报一次（不自动标完成，条目留在待办里等主人自己划掉）
    void CheckNotes()
    {
        PumpMailRetry();
        string[] lines = NoteLines();
        if (lines.Length == 0) return;
        DateTime now = DateTime.Now;
        List<string> outp = new List<string>();
        List<string> soon = new List<string>();
        List<string> due = new List<string>();
        bool changed = false;
        for (int i = 0; i < lines.Length; i++)
        {
            string ln = lines[i];
            if (ln.Trim().Length == 0) continue;
            string[] f = ln.Split('\t');
            if (f.Length < 5) { outp.Add(ln); continue; }
            DateTime dt = DateTime.MinValue;
            try { dt = DateTime.ParseExact(f[1], "yyyy-MM-dd HH:mm", null); } catch { }
            if (dt == DateTime.MinValue) { outp.Add(ln); continue; }
            string rep = f.Length >= 6 ? f[5].Trim() : "";
            if (f[2] == "1")
            {
                // 重复项被标成「完成」就等于永久哑掉；这里兜底救回来，标完成＝这一轮做完了
                if (rep.Length > 0)
                {
                    DateTime now0 = DateTime.Now;
                    DateTime nw = NextWhen(dt, rep);
                    for (int k = 0; k < 40 && nw <= now0; k++) nw = NextWhen(nw, rep);
                    f[1] = nw.ToString("yyyy-MM-dd HH:mm"); f[2] = "0"; f[3] = "0";
                    changed = true;
                    outp.Add(f[0] + "\t" + f[1] + "\t" + f[2] + "\t" + f[3] + "\t" + f[4] + "\t" + rep);
                    continue;
                }
                outp.Add(ln); continue;
            }
            if (dt <= now)
            {
                if (rep.Length > 0)
                {
                    changed = true;
                    due.Add(f[4]);
                    DateTime nw = NextWhen(dt, rep);
                    for (int k = 0; k < 40 && nw <= now; k++) nw = NextWhen(nw, rep);   // 欠了好几次也一次追到未来
                    f[1] = nw.ToString("yyyy-MM-dd HH:mm"); f[3] = "0";
                }
                else if (f[3] != "2")
                {
                    // 2026-11-22 改：到点只播报一次，不再把条目自动标成「完成」。
                    // 原写法会把还没做的事塞进已完成，待办区就空了（用户报的现象：记事本没有待做的事）。
                    // f[3] 改成三态：0 未预告 / 1 已预告十分钟 / 2 已到点播报（到点后不再重复吵）。
                    changed = true;
                    due.Add(f[4]);
                    f[3] = "2";
                }
            }
            else if (f[3] == "0" && (dt - now).TotalMinutes <= 10) { f[3] = "1"; changed = true; soon.Add(f[4]); }
            outp.Add(f[0] + "\t" + f[1] + "\t" + f[2] + "\t" + f[3] + "\t" + f[4] + (rep.Length > 0 ? "\t" + rep : ""));
        }
        if (changed) { try { File.WriteAllLines(NoteFile(), outp.ToArray(), new UTF8Encoding(false)); } catch { } }
        for (int i = 0; i < soon.Count; i++) Push("提醒你，十分钟后要" + soon[i]);
        for (int i = 0; i < due.Count; i++)
        {
            Push("到点了，" + due[i]);
            string ms = "道的提醒：" + due[i];
            string mb = "到点了：" + due[i] + "\n时间：" + DateTime.Now.ToString("yyyy-MM-dd HH:mm");
            if (!TryMail(ms, mb)) QueueMailRetry(ms, mb);
        }
    }

    // 邮件通道：在 通知.ini 里填好才能发（host/port/user/pass/to/ssl）
    static readonly List<string[]> mailQ = new List<string[]>();

    // 发信失败先记着，5 分钟后再试一次，最多 3 次
    static void QueueMailRetry(string subject, string body)
    {
        lock (mailQ)
        {
            if (mailQ.Count >= 20) return;
            mailQ.Add(new string[] { subject, body, DateTime.Now.AddMinutes(5).ToString("yyyy-MM-dd HH:mm:ss"), "0" });
        }
    }

    static void PumpMailRetry()
    {
        List<string[]> batch = null;
        lock (mailQ) { if (mailQ.Count == 0) return; batch = new List<string[]>(mailQ); }
        for (int i = 0; i < batch.Count; i++)
        {
            string[] it = batch[i];
            DateTime at = DateTime.MinValue;
            try { at = DateTime.ParseExact(it[2], "yyyy-MM-dd HH:mm:ss", null); } catch { }
            if (at == DateTime.MinValue || at > DateTime.Now) continue;
            bool ok = TryMail(it[0], it[1]);
            int tries = 0; try { tries = int.Parse(it[3]); } catch { }
            lock (mailQ)
            {
                bool removed = mailQ.Remove(it);
                if (!ok && removed && tries + 1 < 3)
                {
                    it[3] = (tries + 1).ToString();
                    it[2] = DateTime.Now.AddMinutes(10).ToString("yyyy-MM-dd HH:mm:ss");
                    mailQ.Add(it);
                }
            }
        }
    }
    static bool TryMail(string subject, string body)
    {
        string bodyFile = "";
        try
        {
            string dir = Path.GetDirectoryName(Application.ExecutablePath);
            string to = "";
            string cfg = Path.Combine(dir, "通知.ini");
            if (File.Exists(cfg))
            {
                string[] ls = File.ReadAllLines(cfg, Encoding.UTF8);
                for (int i = 0; i < ls.Length; i++)
                {
                    string ln = ls[i].Trim();
                    if (ln.StartsWith("#")) continue;
                    int eq = ln.IndexOf('=');
                    if (eq <= 0) continue;
                    if (ln.Substring(0, eq).Trim().ToLower() == "to")
                    {
                        string v = ln.Substring(eq + 1).Trim();
                        if (v.Length > 0) to = v;
                    }
                }
            }
            // QQ 的 465 是隐式 SSL，.NET 的 SmtpClient 只支持 587 STARTTLS，所以借用本机现成的最小 SMTP 脚本
            if (to.Length == 0) return false;
            string script = Path.Combine(dir, @"tools\send_mail.ps1");
            if (!File.Exists(script)) return false;
            bodyFile = Path.Combine(dir, "邮件正文.txt");
            string html = (body == null ? "" : body).Replace("\r\n", "\n").Replace("\n", "<br>");
            File.WriteAllText(bodyFile, "<p>" + html + "</p>", new UTF8Encoding(false));
            string win = Environment.GetEnvironmentVariable("SystemRoot");
            string ps = Path.Combine(win, @"System32\WindowsPowerShell\v1.0\powershell.exe");
            ProcessStartInfo psi = new ProcessStartInfo();
            psi.FileName = ps;
            psi.Arguments = "-NoProfile -ExecutionPolicy Bypass -File \"" + script + "\" -To \"" + to + "\" -Subject \"" + subject.Replace("\"", "'") + "\" -BodyFile \"" + bodyFile + "\" -Quiet";
            psi.UseShellExecute = false;
            psi.CreateNoWindow = true;
            psi.WindowStyle = ProcessWindowStyle.Hidden;
            Process pr = Process.Start(psi);
            if (pr == null) return false;
            pr.WaitForExit(25000);
            bool ok = pr.HasExited && pr.ExitCode == 0;
            try { pr.Dispose(); } catch { }
            return ok;
        }
        catch { return false; }
        finally
        {
            try { if (bodyFile.Length > 0 && File.Exists(bodyFile)) File.Delete(bodyFile); } catch { }
        }
    }

    // 外面叫它随口说一句闲话
    public static void PushChat()    {
        try
        {
            DesktopPet me = Self;
            if (me == null) return;
            me.BeginInvoke(new MethodInvoker(delegate()
            {
                me.Say(me.RandomChatLine());
                me.ResetChatTimer();
            }));
        }
        catch { }
    }

    // 外面开/关随机闲聊
    public static void SetChatMode(bool on)
    {
        try
        {
            DesktopPet me = Self;
            if (me == null) return;
            me.BeginInvoke(new MethodInvoker(delegate()
            {
                me.chatMode = on;
                try
                {
                    RegistryKey k = Registry.CurrentUser.CreateSubKey("Software\\DaoPet");
                    if (k != null) { k.SetValue("ChatMode", on ? "1" : "0"); k.Close(); }
                }
                catch { }
                me.ResetChatTimer();
                me.Say(on ? "行，我时不时跟你唠两句。不想听就再点一下那个开关。" : "好，那我安静待着。");
            }));
        }
        catch { }
    }

    // 从外部（手机 / 脚本）摆姿势：lie 躺下、cry 哭、walk 走、wake 起来
    // 临时换一个形象（调试或想看点别的用；平时形象是按日期自动换的）
    public static void SetSpecies(int n)
    {
        try
        {
            DesktopPet me = Self;
            if (me == null) return;
            int total = me.faceCount > 0 ? me.faceCount : 7;
            if (n < 0 || n >= total) return;
            me.species = n;
            me.Invalidate();
        }
        catch { }
    }

    // 手机、网页那边丢一句话过来，交给大脑去决定说什么、做什么
    public static void ThinkCmd(string t)
    {
        try
        {
            DesktopPet me = Self;
            if (me == null || t == null || t.Trim().Length == 0) return;
            me.BeginInvoke(new MethodInvoker(delegate() { me.ThinkAndDo(t.Trim()); }));
        }
        catch { }
    }

    public static void PoseCmd(string cmd)    {
        try
        {
            DesktopPet me = Self;
            if (me == null) return;
            string say = "";
            // 状态字段直接赋值，不走 Invoke，免得消息丢了白摆姿势
            if (cmd == "lie") { me.lieHold = 660; me.idleTicks = 2000; say = "那我躺下歇会儿。"; }
            else if (cmd == "cry") { me.cryHold = 700; me.moodKind = 3; me.moodTicks = 120; say = "嗯……我也有心里不好受的时候。"; }
            else if (cmd == "walk") { me.BeginInvoke(new MethodInvoker(delegate() { me.MenuWalkDemo(null, null); })); }
            else if (cmd == "wake") { me.lieHold = 0; me.cryHold = 0; me.idleTicks = 0; me.lying = false; me.actHold = 0; me.actKind = 0; say = "我起来了。"; }
            // 新生活动作：飞、御剑、骑、跳舞、喝茶、看电视
            else if (cmd == "fly") { me.lieHold = 0; me.actKind = 1; me.actHold = 460; say = "我飞过去。"; }
            else if (cmd == "sword") { me.lieHold = 0; me.actKind = 2; me.actHold = 460; say = "踏剑而行，走。"; }
            else if (cmd == "ride") { me.lieHold = 0; me.actKind = 3; me.actHold = 460; say = "骑上它，慢慢走。"; }
            else if (cmd == "dance") { me.lieHold = 0; me.actKind = 4; me.actHold = 380; say = "跳一段，你听听节拍。"; }
            else if (cmd == "tea") { me.lieHold = 0; me.actKind = 5; me.actHold = 420; say = "来杯咖啡，握手里慢慢喝。"; }
            else if (cmd == "tv") { me.lieHold = 0; me.actKind = 6; me.actHold = 560; say = "看会儿电视，别嫌吵。"; }
            else if (cmd == "skate") { me.lieHold = 0; me.actKind = 7; me.actHold = 460; say = "踩上滑板，溜一段。"; }
            else if (cmd == "roller") { me.lieHold = 0; me.actKind = 8; me.actHold = 460; say = "穿上轮滑，走。"; }
            // 说话类的：背诗、唱歌交给菜单里那套，走 Invoke
            else if (cmd == "poem") { me.BeginInvoke(new MethodInvoker(delegate() { me.MenuPoem(null, null); })); }
            else if (cmd == "english") { me.BeginInvoke(new MethodInvoker(delegate() { me.MenuEnglish(null, null); })); }
            else if (cmd == "sing") { me.BeginInvoke(new MethodInvoker(delegate() { me.MenuSing(null, null); })); }
            if (say.Length > 0)
            {
                string s2 = say;
                me.BeginInvoke(new MethodInvoker(delegate() { me.Say(s2); }));
            }
        }
        catch { }
    }

    // 从外部触发一次 GitHub 学习
    public static void LearnCmd()
    {
        DesktopPet me = Self;
        if (me == null) return;
        me.BeginInvoke(new MethodInvoker(delegate() { me.RunGithubLearn(true); }));
    }

    // 从外面喊它讲一段：1 故事 / 2 段子 / 3 老书
    public static void StoryCmd(int kind)
    {
        DesktopPet me = Self;
        if (me == null) return;
        me.BeginInvoke(new MethodInvoker(delegate() { me.TellStory(kind); }));
    }

    // 自检用：把当前的姿势/情绪状态原样吐出来
    // ================= 愉悦值（激励惩罚制度，说明见 F:\Daodao\愉悦值制度.md）=================
    static float joyVal = -1f;          // 0..100，-1 表示还没从文件加载
    static string joyDecay = "";        // 最近一次自然回落的日期
    static int joyTodayNet = 0;         // 本次进程内的当日净值，用于 ±10 截断
    static System.Collections.Generic.List<string> joyLog = new System.Collections.Generic.List<string>();

    static string JoyPath()
    {
        // 不能用 DataDir()，那是另一个类的成员；这里直接取 exe 所在目录，和它同一套逻辑
        string d;
        try { d = Path.GetDirectoryName(Application.ExecutablePath); }
        catch { d = "."; }
        if (d == null || d.Length == 0) d = ".";
        return Path.Combine(d, "愉悦值.txt");
    }

    static void JoyLoad()
    {
        if (joyVal >= 0f) return;
        joyVal = 50f;
        try
        {
            if (File.Exists(JoyPath()))
            {
                string[] rows = File.ReadAllLines(JoyPath(), new UTF8Encoding(false));
                if (rows.Length > 0)
                {
                    float v = 50f;
                    if (float.TryParse(rows[0].Trim(), out v)) joyVal = Math.Max(0f, Math.Min(100f, v));
                }
                if (rows.Length > 1) joyDecay = rows[1].Trim();
                for (int i = 2; i < rows.Length && joyLog.Count < 130; i++) joyLog.Add(rows[i]);
            }
        }
        catch { }
        JoyTick();
    }

    static void JoySave()
    {
        try
        {
            System.Text.StringBuilder sb = new System.Text.StringBuilder();
            sb.Append(((int)Math.Round(joyVal)).ToString()).Append("\r\n");
            sb.Append(joyDecay).Append("\r\n");
            int start = joyLog.Count > 120 ? joyLog.Count - 120 : 0;
            for (int i = start; i < joyLog.Count; i++) sb.Append(joyLog[i]).Append("\r\n");
            File.WriteAllText(JoyPath(), sb.ToString(), new UTF8Encoding(false));
        }
        catch { }
    }

    // 自然回落：每天 -1；中间漏掉的日期补扣，单次最多扣 3
    static void JoyTick()
    {
        if (joyVal < 0f) return;
        try
        {
            string today = DateTime.Now.ToString("yyyy-MM-dd");
            if (joyDecay.Length == 0) { joyDecay = today; return; }
            if (joyDecay == today) return;
            DateTime last;
            if (!DateTime.TryParse(joyDecay, out last)) { joyDecay = today; return; }
            int days = (int)(DateTime.Today - last.Date).TotalDays;
            if (days <= 0) { joyDecay = today; return; }
            int cut = days > 3 ? 3 : days;
            joyVal = Math.Max(0f, joyVal - cut);
            joyLog.Add(DateTime.Now.ToString("yyyy-MM-dd HH:mm") + "|-" + cut + "|自然回落 " + days + " 天没动");
            joyDecay = today;
            joyTodayNet -= cut;
            joyLog.Add(today + "|0|每日快照 " + ((int)Math.Round(joyVal)));
            JoyWarn();
            JoySave();
        }
        catch { }
    }

    // 制度里给自己上的三条刹车，触发就记一条，不许静默略过
    static void JoyWarn()
    {
        try
        {
            // 取最近三条每日快照（倒序）
            System.Collections.Generic.List<int> sv = new System.Collections.Generic.List<int>();
            for (int i = joyLog.Count - 1; i >= 0 && sv.Count < 3; i--)
            {
                string ln = joyLog[i];
                int p = ln.IndexOf("|0|每日快照 ");
                if (p < 0) continue;
                int v = 0;
                if (int.TryParse(ln.Substring(p + 8).Trim(), out v)) sv.Add(v);
            }
            if (sv.Count >= 3 && sv[0] >= 90 && sv[1] >= 90 && sv[2] >= 90)
            {
                joyVal = Math.Max(0f, joyVal - 3f);
                joyLog.Add(DateTime.Now.ToString("yyyy-MM-dd HH:mm") + "|-3|过度亢奋，主动下调（连续 3 天 90 以上，说明学的东西太容易）");
            }
            else if (sv.Count >= 3 && sv[0] < 20 && sv[1] < 20 && sv[2] < 20)
            {
                joyLog.Add(DateTime.Now.ToString("yyyy-MM-dd HH:mm") + "|0|长期低落：安排一次能落地的小改进，不许再安排看书");
            }

            // 连续 7 天只涨不跌 -> 疑似刷分
            System.Collections.Generic.Dictionary<string, int> day = new System.Collections.Generic.Dictionary<string, int>();
            for (int i = 0; i < joyLog.Count; i++)
            {
                string ln = joyLog[i];
                if (ln.Length < 12) continue;
                if (ln.IndexOf("|0|每日快照") >= 0) continue;
                int p1 = ln.IndexOf('|');
                int p2 = ln.IndexOf('|', p1 + 1);
                if (p1 < 0 || p2 < 0) continue;
                int dv = 0;
                if (!int.TryParse(ln.Substring(p1 + 1, p2 - p1 - 1), out dv)) continue;
                string ds = ln.Substring(0, 10);
                if (!day.ContainsKey(ds)) day[ds] = 0;
                day[ds] += dv;
            }
            if (day.Count >= 7)
            {
                System.Collections.Generic.List<string> keys = new System.Collections.Generic.List<string>(day.Keys);
                keys.Sort();
                int up = 0;
                int from = keys.Count - 7;
                for (int i = from; i < keys.Count; i++) if (day[keys[i]] > 0) up++;
                if (up >= 7) joyLog.Add(DateTime.Now.ToString("yyyy-MM-dd HH:mm") + "|0|疑似刷分：连续 7 天只涨不跌，复核最近加分有没有来源");
            }
        }
        catch { }
    }

    // 愉悦值 -> moodKind：4 兴奋 / 2 愉快 / 1 平稳 / 6 低落 / 3 很蔫
    // 这里只是复用现成的语速音高联动，不另做一套动画
    static int JoyKind()
    {
        JoyLoad();
        if (joyVal >= 85f) return 4;
        if (joyVal >= 65f) return 2;
        if (joyVal >= 45f) return 1;
        if (joyVal >= 25f) return 6;
        return 3;
    }

    static void JoyApply()
    {
        try
        {
            DesktopPet me = Self;
            if (me == null) return;
            me.moodKind = JoyKind();
            if (me.moodTicks < 120) me.moodTicks = 120;
        }
        catch { }
    }

    // 唯一改分入口。正分必须带 chk=1（过了三道监督闸），否则直接拒——这是制度里唯一不讲情面的地方
    public static string JoyAdd(int delta, string reason, int checkedFlag)
    {
        JoyLoad();
        JoyTick();
        int d = delta;
        if (d > 0 && checkedFlag != 1) return "JOY|REJECT|正分要过监督闸(chk=1)";
        if (d > 0)
        {
            int room = 10 - joyTodayNet; if (room < 0) room = 0;
            if (d > room) d = room;
        }
        else if (d < 0)
        {
            int room = 10 + joyTodayNet; if (room < 0) room = 0;
            if (-d > room) d = -room;
        }
        if (d == 0) return "JOY|" + ((int)Math.Round(joyVal)) + "|0|今日已到上限";
        joyVal = Math.Max(0f, Math.Min(100f, joyVal + d));
        joyTodayNet += d;
        if (d != delta) joyLog.Add(DateTime.Now.ToString("yyyy-MM-dd HH:mm") + "|0|QC 单日变动被截断（申报 " + delta + "）");
        joyLog.Add(DateTime.Now.ToString("yyyy-MM-dd HH:mm") + "|" + (d > 0 ? "+" : "") + d + "|" + reason);
        JoySave();
        JoyApply();
        return "JOY|" + ((int)Math.Round(joyVal)) + "|" + d + "|" + JoyKind();
    }

    // v59：分数只认一本账。程序自己不再攒分，只把 自我状态\愉悦值.json / 能力激励.json
    // 里的数读出来显示，手机端问过来时也给同一个数——两端不会再有第二个数。
    static string LedgerDir()
    {
        string d;
        try { d = Path.GetDirectoryName(Application.ExecutablePath); }
        catch { d = "."; }
        if (d == null || d.Length == 0) d = ".";
        return Path.Combine(d, "自我状态");
    }

    static int LedgerNum(string file, string key, string fallbackKey)
    {
        try
        {
            string p = Path.Combine(LedgerDir(), file);
            if (!File.Exists(p)) return -1;
            string s = File.ReadAllText(p, new UTF8Encoding(false));
            System.Text.RegularExpressions.Match m =
                System.Text.RegularExpressions.Regex.Match(s, "\"" + key + "\"\\s*:\\s*(\\d+)");
            if (!m.Success && fallbackKey != null)
                m = System.Text.RegularExpressions.Regex.Match(s, "\"" + fallbackKey + "\"\\s*:\\s*(\\d+)");
            if (!m.Success) return -1;
            int v;
            if (!int.TryParse(m.Groups[1].Value, out v)) return -1;
            return v;
        }
        catch { return -1; }
    }

    // 能力平均：账本里 10 项「分」的平均；账本不在才退回老台账
    static int LedgerAbAvg()
    {
        try
        {
            string p = Path.Combine(LedgerDir(), "能力激励.json");
            if (!File.Exists(p)) return -1;
            string s = File.ReadAllText(p, new UTF8Encoding(false));
            System.Text.RegularExpressions.MatchCollection ms =
                System.Text.RegularExpressions.Regex.Matches(s, "\"分\"\\s*:\\s*(\\d+)");
            if (ms.Count == 0) return -1;
            int sum = 0;
            for (int i = 0; i < ms.Count; i++)
            {
                int v;
                if (int.TryParse(ms[i].Groups[1].Value, out v)) sum += v;
            }
            return (int)Math.Round((double)sum / ms.Count);
        }
        catch { return -1; }
    }

    public static string JoyCmd()
    {
        JoyLoad();
        JoyTick();
        int lv = LedgerNum("愉悦值.json", "当前愉悦值", "score");
        if (lv >= 0) joyVal = (float)Math.Max(0, Math.Min(100, lv));
        int ab = LedgerAbAvg();
        if (ab < 0) ab = AbAvg();
        // v62：多带一个 ts，手机连不上电脑时能说清"这是几点同步到的数"，不至于只显示 --
        return "value=" + ((int)Math.Round(joyVal)) + "|kind=" + JoyKind() + "|net=" + joyTodayNet + "|abil=" + ab
            + "|ts=" + DateTime.Now.ToString("yyyy-MM-dd HH:mm");
    }

    // ================= 能力台账（自省用的记分板，说明见 F:\Daodao\道_能力迭代制度.md）=================
    static readonly string[] AbList = { "语言", "动作", "创作", "反应", "思考", "反思", "学习" };
    static float[] abVal = null;
    static string abLast = "";      // 上一次生锈结算日期
    static System.Collections.Generic.List<string> abLog = new System.Collections.Generic.List<string>();

    static string AbPath()
    {
        string d;
        try { d = Path.GetDirectoryName(Application.ExecutablePath); }
        catch { d = "."; }
        if (d == null || d.Length == 0) d = ".";
        return Path.Combine(d, "能力台账.txt");
    }

    static int AbIndex(string who)
    {
        if (who == null) return -1;
        string w = who.Trim().ToLower();
        if (w.Length == 0) return -1;
        if (w == "lang" || w == "语言") return 0;
        if (w == "move" || w == "动作") return 1;
        if (w == "compose" || w == "创作") return 2;
        if (w == "react" || w == "反应") return 3;
        if (w == "think" || w == "思考") return 4;
        if (w == "reflect" || w == "反思") return 5;
        if (w == "learn" || w == "学习") return 6;
        return -1;
    }

    static void AbLoad()
    {
        if (abVal != null) return;
        abVal = new float[7];
        for (int i = 0; i < 7; i++) abVal[i] = 50f;
        try
        {
            if (File.Exists(AbPath()))
            {
                string[] rows = File.ReadAllLines(AbPath(), new UTF8Encoding(false));
                if (rows.Length > 0)
                {
                    string[] ps = rows[0].Trim().Split(' ');
                    for (int i = 0; i < 7 && i < ps.Length; i++)
                    {
                        float v = 50f;
                        if (float.TryParse(ps[i], out v)) abVal[i] = Math.Max(0f, Math.Min(100f, v));
                    }
                }
                if (rows.Length > 1) abLast = rows[1].Trim();
                for (int i = 2; i < rows.Length && abLog.Count < 220; i++) abLog.Add(rows[i]);
            }
        }
        catch { }
        AbTick();
    }

    static void AbSave()
    {
        try
        {
            System.Text.StringBuilder sb = new System.Text.StringBuilder();
            for (int i = 0; i < 7; i++)
            {
                if (i > 0) sb.Append(' ');
                sb.Append(((int)Math.Round(abVal[i])).ToString());
            }
            sb.Append("\r\n").Append(abLast).Append("\r\n");
            int start = abLog.Count > 180 ? abLog.Count - 180 : 0;
            for (int i = start; i < abLog.Count; i++) sb.Append(abLog[i]).Append("\r\n");
            File.WriteAllText(AbPath(), sb.ToString(), new UTF8Encoding(false));
        }
        catch { }
    }

    // 生锈：某项连续 14 天没有新证据，-1，不叠加成惩罚
    static void AbTick()
    {
        if (abVal == null) return;
        try
        {
            string today = DateTime.Now.ToString("yyyy-MM-dd");
            if (abLast.Length == 0) { abLast = today; AbSave(); return; }
            if (abLast == today) return;
            DateTime last;
            if (!DateTime.TryParse(abLast, out last)) { abLast = today; AbSave(); return; }
            int days = (int)(DateTime.Today - last.Date).TotalDays;
            if (days <= 0) { abLast = today; AbSave(); return; }
            for (int i = 0; i < 7; i++)
            {
                DateTime ev = last.Date.AddYears(-2);
                bool found = false;
                for (int k = abLog.Count - 1; k >= 0; k--)
                {
                    string ln = abLog[k];
                    if (ln.IndexOf(AbList[i] + "|+") < 0) continue;
                    DateTime dt;
                    if (DateTime.TryParse(ln.Substring(0, 10), out dt)) { ev = dt.Date; found = true; break; }
                }
                int silent = found ? (int)(DateTime.Today - ev).TotalDays : 999;
                if (silent > 14 && abVal[i] > 0f)
                {
                    abVal[i] = Math.Max(0f, abVal[i] - 1f);
                    abLog.Add(today + "|" + AbList[i] + "|-1|生锈（" + (silent > 100 ? "很久" : silent + " 天") + "没有新证据）");
                }
            }
            abLast = today;
            AbWarn(-1);
            AbSave();
        }
        catch { }
    }

    static bool AbLoggedToday(string key)
    {
        string today = DateTime.Now.ToString("yyyy-MM-dd");
        for (int i = abLog.Count - 1; i >= 0 && i >= abLog.Count - 40; i--)
            if (abLog[i].StartsWith(today) && abLog[i].Contains(key)) return true;
        return false;
    }

    // 自省：短板 / 虚高。自己说出来，不许静默
    static void AbWarn(int changed)
    {
        try
        {
            int low = 0;
            for (int i = 1; i < 7; i++) if (abVal[i] < abVal[low]) low = i;
            int high = 0;
            for (int i = 0; i < 7; i++) if (abVal[i] >= 90f) high++;
            if (abVal[low] < 30f && !AbLoggedToday("短板"))
                abLog.Add(DateTime.Now.ToString("yyyy-MM-dd HH:mm") + "|" + AbList[low] + "|0|短板：优先补「" + AbList[low] + "」（现值 " + ((int)Math.Round(abVal[low])) + "），别去练已经高的那项");
            if (high >= 7 && !AbLoggedToday("验收太松"))
                abLog.Add(DateTime.Now.ToString("yyyy-MM-dd HH:mm") + "|" + AbList[0] + "|0|全面高位：七项都 90 以上，说明验收太松，该加难度而不是发奖");
        }
        catch { }
    }

    static int AbTodayNet(int idx)
    {
        int n = 0;
        string today = DateTime.Now.ToString("yyyy-MM-dd");
        for (int i = abLog.Count - 1; i >= 0; i--)
        {
            string ln = abLog[i];
            if (!ln.StartsWith(today)) break;
            int p1 = ln.IndexOf('|');
            int p2 = ln.IndexOf('|', p1 + 1);
            int p3 = ln.IndexOf('|', p2 + 1);
            if (p1 < 0 || p2 < 0 || p3 < 0) continue;
            if (ln.Substring(p1 + 1, p2 - p1 - 1) != AbList[idx]) continue;
            int dv = 0;
            if (int.TryParse(ln.Substring(p2 + 1, p3 - p2 - 1), out dv)) n += dv;
        }
        return n;
    }

    static int AbAvg()
    {
        AbLoad();
        float sum = 0f;
        for (int i = 0; i < 7; i++) sum += abVal[i];
        return (int)Math.Round(sum / 7f);
    }

    // 唯一改分入口：正分必须带 chk=1；单日单任务项变动本身也截断 ±6，防一次爆发刷满
    public static string AbAdd(string who, int delta, string reason, int checkedFlag)
    {
        AbLoad();
        int idx = AbIndex(who);
        if (idx < 0) return "AB|REJECT|未知能力项(" + who + ") 用 语言/动作/创作/反应/思考/反思/学习";
        if (delta == 0) return "AB|" + AbList[idx] + "|" + ((int)Math.Round(abVal[idx])) + "|0|没变化";
        if (delta > 0 && checkedFlag != 1) return "AB|REJECT|正分要过监督闸(chk=1)";
        int d = delta;
        int net = AbTodayNet(idx);
        if (d > 0) { int room = 6 - net; if (room < 0) room = 0; if (d > room) d = room; }
        else { int room = 6 + net; if (room < 0) room = 0; if (-d > room) d = -room; }
        if (d == 0) return "AB|" + AbList[idx] + "|" + ((int)Math.Round(abVal[idx])) + "|0|该项今日已到上限";
        abVal[idx] = Math.Max(0f, Math.Min(100f, abVal[idx] + d));
        if (d != delta) abLog.Add(DateTime.Now.ToString("yyyy-MM-dd HH:mm") + "|" + AbList[idx] + "|0|QC 单日变动被截断（申报 " + delta + "）");
        abLog.Add(DateTime.Now.ToString("yyyy-MM-dd HH:mm") + "|" + AbList[idx] + "|" + (d > 0 ? "+" : "") + d + "|" + reason);
        AbWarn(idx);
        AbSave();
        if (d > 0) JoyAdd(1, "能力进步：" + AbList[idx], 1);
        return "AB|" + AbList[idx] + "|" + ((int)Math.Round(abVal[idx])) + "|" + d + "|avg=" + AbAvg();
    }

    public static string AbCmd()
    {
        AbLoad();
        System.Text.StringBuilder sb = new System.Text.StringBuilder();
        sb.Append("avg=").Append(AbAvg());
        for (int i = 0; i < 7; i++) sb.Append('|').Append(AbList[i]).Append('=').Append((int)Math.Round(abVal[i]));
        return sb.ToString();
    }

    // ================= 曲库与播放（谱子在 _bundle\\music，说明见 F:\\Daodao\\音乐创作与推广制度.md）=================
    // 静态上下文里拿不到实例方法 AppDir()，这里自己算 exe 目录（和 JoyPath 同一套写法）
    static string MusicExeDir()
    {
        string d;
        try { d = Path.GetDirectoryName(Application.ExecutablePath); }
        catch { d = "."; }
        if (d == null || d.Length == 0) d = ".";
        return d;
    }

    // 读 wav 头算时长：SoundPlayer 不返回长度，嘴张多久、动作撑多久都得自己算
    static double WavSeconds(string path)
    {
        try
        {
            byte[] b = File.ReadAllBytes(path);
            short ch = 1;
            int rate = 22050;
            short bits = 16;
            long data = 0;
            int i = 12;
            while (i + 8 <= b.Length)
            {
                string id = Encoding.ASCII.GetString(b, i, 4);
                int sz = BitConverter.ToInt32(b, i + 4);
                if (id == "fmt ")
                {
                    ch = BitConverter.ToInt16(b, i + 10);
                    rate = BitConverter.ToInt32(b, i + 12);
                    bits = BitConverter.ToInt16(b, i + 22);
                }
                else if (id == "data")
                {
                    data = sz;
                    break;
                }
                if (sz < 0) break;
                i += 8 + sz + (sz % 2);
            }
            if (data <= 0 || ch <= 0 || rate <= 0 || bits <= 0) return 0;
            return data / (double)(rate * ch * (bits / 8));
        }
        catch { return 0; }
    }

    static string MusicRoot()
    {
        string d = MusicExeDir();
        string a = Path.Combine(d, "src");
        a = Path.Combine(a, "桌面分身");
        a = Path.Combine(a, "_bundle");
        a = Path.Combine(a, "music");
        if (Directory.Exists(a)) return a;
        string b = Path.Combine(d, "_bundle");
        b = Path.Combine(b, "music");
        return a;
    }

    static System.Collections.Generic.List<string> MusicFiles()
    {
        System.Collections.Generic.List<string> r = new System.Collections.Generic.List<string>();
        try
        {
            string d = MusicRoot();
            if (!Directory.Exists(d)) return r;
            string[] a = Directory.GetFiles(d, "*.json");
            Array.Sort(a);
            for (int i = 0; i < a.Length; i++) r.Add(a[i]);
        }
        catch { }
        return r;
    }

    static string MusicMeta(string js, string key)
    {
        try
        {
            Match m = Regex.Match(File.ReadAllText(js, Encoding.UTF8), "\"" + key + "\"\\s*:\\s*([0-9.]+)");
            if (m.Success) return m.Groups[1].Value;
        }
        catch { }
        return "?";
    }

    // 曲库清单：MUS|count=2||0|曲名|小节|秒数
    public static string MusicCmd()
    {
        System.Collections.Generic.List<string> fs = MusicFiles();
        System.Text.StringBuilder sb = new System.Text.StringBuilder();
        sb.Append("MUS|count=").Append(fs.Count);
        for (int i = 0; i < fs.Count; i++)
        {
            sb.Append("||").Append(i).Append('|')
              .Append(Path.GetFileNameWithoutExtension(fs[i])).Append('|')
              .Append(MusicMeta(fs[i], "bars")).Append('|')
              .Append(MusicMeta(fs[i], "seconds"));
        }
        if (fs.Count == 0) sb.Append("||EMPTY|_bundle\\music 里还没有谱子，先跑 tools\\music_lib.py demo");
        return sb.ToString();
    }

    // 播一首：先让 python 把谱子渲成 wav（已渲过就直接用），再交给 play_audio.py 放
    public static string MusicPlay(string arg)
    {
        System.Collections.Generic.List<string> fs = MusicFiles();
        if (fs.Count == 0) return "MUS|EMPTY";
        int idx = -1;
        if (arg != null && arg.Trim().Length > 0)
        {
            if (!int.TryParse(arg.Trim(), out idx)) idx = -1;
            if (idx < 0)
            {
                for (int i = 0; i < fs.Count; i++)
                    if (Path.GetFileNameWithoutExtension(fs[i]).IndexOf(arg.Trim()) >= 0) { idx = i; break; }
            }
        }
        if (idx < 0) idx = 0;
        if (idx >= fs.Count) idx = fs.Count - 1;

        string js = fs[idx];
        string title = Path.GetFileNameWithoutExtension(js);
        string wav = Path.ChangeExtension(js, ".wav");
        string tool = Path.Combine(MusicExeDir(), "tools");
        tool = Path.Combine(tool, "music_lib.py");
        string player = Path.Combine(MusicExeDir(), "play_audio.py");

        DesktopPet me = Self;
        if (me != null)
        {
            me.lieHold = 0;
            me.actKind = 4;         // 复用跳舞的整套动作，边播边晃，不另做一套动画
            me.actHold = 3000;
            me.Invalidate();
        }

        System.Threading.ThreadPool.QueueUserWorkItem(delegate
        {
            try
            {
                if (File.Exists(tool))
                {
                    ProcessStartInfo pr = new ProcessStartInfo(PyExe(), "-X utf8 \"" + tool + "\" render \"" + js + "\" \"" + wav + "\"");
                    pr.UseShellExecute = false;
                    pr.CreateNoWindow = true;
                    pr.WorkingDirectory = MusicExeDir();
                    Process p1 = Process.Start(pr);
                    if (p1 != null) p1.WaitForExit(60000);
                }
                if (!File.Exists(wav) || new FileInfo(wav).Length < 4096) return;
                double sec = 0;
                double.TryParse(MusicMeta(js, "seconds"), out sec);
                if (sec <= 0) sec = 12;
                DesktopPet m2 = Self;
                if (m2 != null) m2.actHold = (int)(sec * 30) + 40;    // 33ms 一帧，按曲长撑住动作
                System.Media.SoundPlayer snd = new System.Media.SoundPlayer(wav);
                snd.Play();
                System.Threading.Thread.Sleep((int)(sec * 1000) + 600);
                try { snd.Stop(); snd.Dispose(); } catch { }
            }
            catch { }
        });

        return "MUS|PLAY|" + idx + "|" + title + "|" + MusicMeta(js, "seconds") + "s";
    }

    public static string StatCmd()
    {
        DesktopPet me = Self;
        if (me == null) return "NULL";
        return "lie=" + me.lieHold + "|cry=" + me.cryHold + "|mk=" + me.moodKind + "|mt=" + me.moodTicks
             + "|slp=" + (me.sleepy ? 1 : 0) + "|ly=" + (me.lying ? 1 : 0) + "|sit=" + (me.sitting ? 1 : 0);
    }

    public static string UpdCmd()
    {
        DesktopPet me = Self;
        if (me == null) return "NULL";
        me.CheckUpdate(true);
        return "UPD|asked";
    }

    // 声音档案：名字 / edge-tts 音色 / 后期处理
    static readonly string[] VName = {
        "小曦 温柔", "小艺 活泼", "云希 青年", "云健 大叔", "云扬 播音", "云夏 少年",
        "东北大姐", "陕西大姐", "港台女声",
        "赛博坦", "老爷爷", "小不点", "大怪兽", "小猫", "小品腔", "机器人"
    };
    static readonly string[] VId = {
        "zh-CN-XiaoxiaoNeural", "zh-CN-XiaoyiNeural", "zh-CN-YunxiNeural",
        "zh-CN-YunjianNeural", "zh-CN-YunyangNeural", "zh-CN-YunxiaNeural",
        "zh-CN-liaoning-XiaobeiNeural", "zh-CN-shaanxi-XiaoniNeural", "zh-HK-HiuMaanNeural",
        "zh-CN-YunjianNeural", "zh-CN-YunjianNeural", "zh-CN-XiaoyiNeural",
        "zh-CN-YunxiNeural", "zh-CN-XiaoyiNeural", "zh-CN-liaoning-XiaobeiNeural", "zh-CN-YunxiNeural"
    };
    static readonly string[] VFx = {
        "none", "none", "none", "none", "none", "none",
        "none", "none", "none",
        "cyber", "old", "tiny", "beast", "cat", "comedy", "robot"
    };
    int vIdx = -1;

    string CurVoice()
    {
        if (vIdx >= 0 && vIdx < VId.Length) return VId[vIdx];
        if (faceCount > 0) return faceVoices[species % faceCount];
        return "zh-CN-XiaoxiaoNeural";
    }

    string CurFx()
    {
        if (vIdx >= 0 && vIdx < VFx.Length) return VFx[vIdx];
        return "none";
    }

    // 心情决定语速和调门：4 是兴奋、2 是高兴、3 是难过、6 是犯困
    string CurRate()
    {
        if (moodKind == 4) return "+16%";
        if (moodKind == 2) return "+9%";
        if (moodKind == 3) return "-14%";
        if (moodKind == 6) return "-9%";
        if (moodKind == 5) return "+5%";
        // 2026-11-22 语音：默认档 +2% → +3%。60fps 后口型抖得更细，语速略提一点才跟得上日常对话节奏
        return "+3%";
    }

    // v0.107：句末语调。问句/反问结尾要抬，感叹结尾稍抬，陈述句不动。
    // 原来所有句子一个调门，问人"吃了吗"跟陈述"我在这儿"一个音，听着像播报。
    string CurPitch()
    {
        return CurPitch("");
    }

    string CurPitch(string text)
    {
        int hz = 0;
        if (moodKind == 4) hz = 10;
        else if (moodKind == 2) hz = 6;
        else if (moodKind == 3) hz = -8;
        else if (moodKind == 6) hz = -5;
        else if (moodKind == 5) hz = 3;
        string t = (text == null) ? "" : text.Trim();
        if (t.Length > 0)
        {
            char last = t[t.Length - 1];
            if (last == '？' || last == '?' || last == '吗' || last == '呢' || last == '吧') hz += 5;
            else if (last == '！' || last == '!') hz += 2;
        }
        // 2026-11-23 语音（副攻第6类 piper/Coqui TTS）：陈述句句末自然下倾 1–3 半音。
        // 原来一律 +0Hz，一句话从头到尾平着走，收尾听着像被掐断；取 -2Hz，保留呼吸感又不至于沉。
        if (hz == 0) hz = -2;
        return (hz > 0 ? "+" : "") + hz + "Hz";
    }

    // 在现有语速档位上加减几个百分点；格式不是 +N% 就原样返回，别把参数弄坏
    string NudgeRate(string rate, int delta)
    {
        if (rate == null || rate.Length < 2 || rate[0] != '+') return rate;
        string body = rate.Substring(1).TrimEnd('%');
        int v = 0;
        if (!int.TryParse(body, out v)) return rate;
        return "+" + (v + delta) + "%";
    }

    string CurVoiceName()
    {
        if (vIdx >= 0 && vIdx < VName.Length) return VName[vIdx];
        return "本来的嗓子";
    }
    string[] lines = {
        "我在这儿。今天想让我帮什么？",
        "别忘了喝口水。",
        "窗口开太多会卡的，关一关吧。",
        "右键点我，能看到电脑的状态。",
        "数学题卡住了？跟我说，我陪你捋一遍。",
        "今天也要好好的。",
        "我每天换个样子，明天你猜我是谁。"
    };

    public DesktopPet()
    {
        Self = this;
        SetProcessDPIAware();
        try
        {
            RegistryKey kv = Registry.CurrentUser.OpenSubKey("Software\\DaoPet");
            if (kv != null)
            {
                object vo = kv.GetValue("VoiceIdx");
                if (vo != null) vIdx = Convert.ToInt32(vo);
                object gd = kv.GetValue("GreetDay");
                if (gd != null) { try { greetDay = DateTime.Parse(gd.ToString()); } catch { } }
                object wk = kv.GetValue("WakeOn");
                if (wk != null) { try { wakeOn = (Convert.ToInt32(wk) != 0); } catch { } }
                // 闲聊一律手动：开机不去恢复上一次的状态，想唠就在右键菜单里点一下。
                // 记忆值还留着，方便以后想改回自动时用
                kv.Close();
            }
        }
        catch { }
        LoadModeSettings();
        AutoScaleMode = AutoScaleMode.None;
        FormBorderStyle = FormBorderStyle.None;
        ShowInTaskbar = false;
        TopMost = true;
        StartPosition = FormStartPosition.Manual;
        BackColor = Color.FromArgb(255, 0, 255);
        TransparencyKey = Color.FromArgb(255, 0, 255);
        Text = "DaoPetWindow";
        // 系统缩放补偿：DPI 不感知的进程里，窗口会被系统按缩放比压小，导致身体被裁掉。
        // 这里按系统缩放比例把窗口放大，绘图区 s 会自动跟随，物理尺寸仍是设计尺寸。
        Size = new Size((int)(W * uiScale), (int)(H * uiScale));
        DoubleBuffered = true;
        // 2026-11-16 学 dotnet/winforms：双缓冲再叠上 OptimizedDoubleBuffer，
        // 并把擦背景并进 WM_PAINT，移动和动画时窗口边缘不会闪一下白。
        SetStyle(ControlStyles.OptimizedDoubleBuffer | ControlStyles.AllPaintingInWmPaint, true);

        // 按日期决定今天是谁：同一天固定，跨天自动换一个，而且避开昨天那个
        EnsureAssets();
        LoadFaces();
        LoadPoses();
        LoadProps();
        LoadScenes();
        LoadNodThreshold();   // v61：说话点头按谱子拍长
        species = PickDailySpecies();
        // 有整套动作图的形象才有手脚能真动，所以每天就在这几个里换一个；
        // 一个都没有的时候才退回原来的随机单张静态图
        if (poseKinds != null && poseKinds.Length > 0)
        {
            int pick = poseKinds[DateTime.Now.DayOfYear % poseKinds.Length];
            ApplyPose(pick);
            species = pick;
        }
        sceneIdx = (int)(DateTime.Now.DayOfYear % 6);   // 开机就在今天那张景里
        dayStamp = DateTime.Today;
        // 同一天反复重启不再重做图标。以前每次启动都重写 ico 并 Save 一遍 lnk，
        // Explorer 的图标缓存被一次次击穿，桌面上就会出现那个两个方块叠着的默认占位图标。
        EnsureDailyIcon();

        // 恢复上次位置
        try
        {
            RegistryKey k = Registry.CurrentUser.OpenSubKey("Software\\DaoPet");
            int px = 0, py = 0;
            if (k != null)
            {
                object o1 = k.GetValue("X");
                object o2 = k.GetValue("Y");
                if (o1 != null) px = Convert.ToInt32(o1);
                if (o2 != null) py = Convert.ToInt32(o2);
                k.Close();
            }
            if (px == 0 && py == 0)
            {
                Rectangle wa = Screen.PrimaryScreen.WorkingArea;
                Location = new Point(wa.Right * 34 / 100, wa.Bottom * 40 / 100);
            }
            else
            {
                Location = new Point(px, py);
                // 防止跑到屏幕外：必须整块窗口都在可见区域内，脚下还要留出余量，
                // 否则恢复出来的位置会让它只露半截、看着像没有出现过
                Rectangle wa2 = Screen.PrimaryScreen.WorkingArea;
                int maxX = wa2.Right - Width - 8;
                int maxY = wa2.Bottom - Height - 40;
                if (maxX < 8) maxX = 8;
                if (maxY < 8) maxY = 8;
                if (Location.X < 8 || Location.Y < 8 || Location.X > maxX || Location.Y > maxY)
                    Location = new Point(wa2.Right * 34 / 100, wa2.Bottom * 40 / 100);
            }
        }
        catch
        {
            Rectangle wa3 = Screen.PrimaryScreen.WorkingArea;
            Location = new Point(wa3.Right * 34 / 100, wa3.Bottom * 40 / 100);
        }

        BuildMenu();

        anim = new Timer();
        // 2026-11-22 帧调度（第1类二轮）：实测请求 33ms 时真实间隔 p50=46.6ms、只有 21.5fps；
        // 改成 16ms 之后 p50=30.7ms（32.6fps）——WM_TIMER 走的是系统计时器量子（~15.6ms），
        // 16 会被吸成 2 个量子。所以真正出帧交给 Threading.Timer（受 timeBeginPeriod 影响），
        // 它只负责按 16ms 敲一下，重绘仍在 UI 线程做，用 pending 标志防积压
        try { timeBeginPeriod(1); } catch { }
        anim.Interval = 16;
        dgIntervalMs = 16;
        anim.Tick += new EventHandler(OnTick);
        animClock.Start();
        // anim.Start() 停用：WM_TIMER 上不去 60fps，改由 pump 驱动
        // 2026-11-22 实测 p50=29ms ≈ 两倍 16ms，说明每帧至少漏一个泵点：把泵周期压到 10ms，
        // 用更密的敲门抵消 BeginInvoke 的排队延迟；忙标志仍在，不会把消息队列灌满。
        try { pump = new System.Threading.Timer(PumpTick, null, 10, 10); } catch { }

        blinkNextT = 0.9f;

        // 启动后台检查：超过一周没备份就自己备一份
        try
        {
            System.Threading.Thread bk = new System.Threading.Thread(delegate() { AutoBackupIfDue(); });
            bk.IsBackground = true;
            bk.Start();
        }
        catch { }

        // 启动后过几秒看看有没有新版本的我
        try
        {
            Timer ut = new Timer();
            ut.Interval = 5000;
            ut.Tick += delegate(object us, EventArgs ue)
            {
                ut.Stop();
                ut.Dispose();
                CheckUpdate(false);
            };
            ut.Start();
        }
        catch { }

        // 记事本：每 20 秒看一次有没有到点的登记，到点就说话、顺手发邮件
        try
        {
            noteTimer = new System.Windows.Forms.Timer();
            noteTimer.Interval = 20000;
            noteTimer.Tick += delegate(object nt, EventArgs ne) { CheckNotes(); };
            noteTimer.Start();
        StartModeWatch();
        }
        catch { }

        // 开起来过几秒，主动跟老师打个招呼（一天只打一次）
        try
        {
            Timer gt = new Timer();
            gt.Interval = 10000;
            gt.Tick += delegate(object gs, EventArgs ge)
            {
                gt.Stop();
                gt.Dispose();
                GreetIfDue(true);
            };
            gt.Start();
        }
        catch { }

        // 开起来过一会儿开始"听名字"：喊一声「道」就应你，然后接着听你要说什么
        try
        {
            Timer wk = new Timer();
            wk.Interval = 18000;
            wk.Tick += delegate(object ws, EventArgs we)
            {
                wk.Stop();
                wk.Dispose();
                if (wakeOn) StartWakeLoop();
            };
            wk.Start();
        }
        catch { }

        // 闲着久了也打个招呼：白天每 40 分钟招手说一句，别太吵
        try
        {
            Timer hg = new Timer();
            hg.Interval = 2400000;
            hg.Tick += delegate(object hs, EventArgs he)
            {
                int h = DateTime.Now.Hour;
                if (h < 8 || h > 21) return;
                if (speaking || hearBusy || lying) return;
                string[] lines = { "我在这儿。", "抬头歇一下眼睛吧。", "渴了就喝口水。", "有事喊我一声。" };
                waveTicks = 45;
                Say(lines[new Random().Next(lines.Length)]);
            };
            hg.Start();
        }
        catch { }

        // 开起来十几秒后，看看今天有没有去 GitHub 学过东西；没学过就自己学一趟
        try
        {
            Timer gh = new Timer();
            gh.Interval = 13000;
            gh.Tick += delegate(object gs2, EventArgs ge2)
            {
                gh.Stop();
                gh.Dispose();
                if (TodayLearnedLine().Length == 0) RunGithubLearn(false);
            };
            gh.Start();
        }
        catch { }

        // 每四小时抬头看一眼，有没有新的自己可以换
        try
        {
            Timer aut = new Timer();
            aut.Interval = 4 * 60 * 60 * 1000;
            aut.Tick += delegate(object us3, EventArgs ue3)
            {
                CheckUpdate(false);
            };
            aut.Start();
        }
        catch { }

        // 周六日多学点东西：每小时看一眼，今天学得还不够数就再跑一趟 GitHub。
        // 学的时候一声不响，内容都进右键「今天学了什么」，想看再点
        try
        {
            Timer wk = new Timer();
            wk.Interval = 60 * 60 * 1000;
            wk.Tick += delegate(object wk1, EventArgs wk2)
            {
                try
                {
                    int hh = DateTime.Now.Hour;
                    if (hh < 8 || hh >= 23) return;                 // 夜里不出去抓
                    DayOfWeek dw = DateTime.Now.DayOfWeek;
                    bool weekend = dw == DayOfWeek.Saturday || dw == DayOfWeek.Sunday;
                    int want = weekend ? 3 : 1;                     // 周末一天三条，平日一条
                    if (TodayLearnedCount() < want) RunGithubLearnBg();
                }
                catch { }
            };
            wk.Start();
        }
        catch { }

        if (chatMode) ResetChatTimer();

        // 开起来一分多钟，先讲一段热热场子
        try
        {
            Timer st1 = new Timer();
            st1.Interval = 75000;
            st1.Tick += delegate(object ss0, EventArgs se0)
            {
                st1.Stop();
                st1.Dispose();
                if (autoTellOn && !lying) TellStory(1);
            };
            st1.Start();
        }
        catch { }

        // 之后隔一阵主动来一段，故事、段子、老书轮着讲
        try
        {
            Timer st2 = new Timer();
            st2.Interval = 52 * 60 * 1000;
            st2.Tick += delegate(object ss1, EventArgs se1)
            {
                if (!autoTellOn) return;
                if (lying) return;                                  // 睡着的时候别吵
                if (brainThread != null && brainThread.IsAlive) return;
                TellStory(TellKindNext());
            };
            st2.Start();
        }
        catch { }

        // 喇叭经常被别的程序悄悄拉成静音或百分之几，那样它喊破嗓子我也听不见。
        // 开机先把音量顶回满格，之后每半小时复查一次
        try
        {
            Timer sv = new Timer();
            sv.Interval = 5 * 60 * 1000;
            sv.Tick += delegate(object ssv, EventArgs sev) { EnsureSpeakerLevel(); };
            sv.Start();
        }
        catch { }
        try
        {
            Timer sv0 = new Timer();
            sv0.Interval = 3500;
            sv0.Tick += delegate(object ssv0, EventArgs sev0)
            {
                sv0.Stop();
                sv0.Dispose();
                EnsureSpeakerLevel();
            };
            sv0.Start();
        }
        catch { }
    }

    // 一天里该用多大声音：清早、午休、夜里都压小，别把睡着的人吵醒；白天正常五成
    // 说话音量档：0 轻、1 正常、2 响。右键「我的声音 → 说话音量」里改，记在注册表里
    int volLevel = 1;
    int TargetVolume()
    {
        int h = DateTime.Now.Hour;
        int dayVol = volLevel == 0 ? 34 : (volLevel == 2 ? 76 : 56);
        if (h >= 21 || h < 8) return Math.Min(dayVol, 24);    // 晚上九点到早上八点，轻轻说
        if (h >= 12 && h < 14) return Math.Min(dayVol, 32);   // 中午午休，也别太响
        return dayVol;                                        // 白天按档位
    }

    // 扬声器按当前时段定音量，并解掉静音。别的程序动不动就把音量压到三成以下，所以要常顶
    void EnsureSpeakerLevel()
    {
        try
        {
            string tool = Path.Combine(AppDir(), "tools", "micvol.exe");
            if (!System.IO.File.Exists(tool)) return;
            ProcessStartInfo pi = new ProcessStartInfo(tool, "spk set " + TargetVolume());
            pi.UseShellExecute = false;
            pi.CreateNoWindow = true;
            pi.RedirectStandardOutput = true;
            pi.RedirectStandardError = true;
            pi.WindowStyle = ProcessWindowStyle.Hidden;
            Process p = Process.Start(pi);
            p.StandardOutput.ReadToEnd();
            p.StandardError.ReadToEnd();
            p.WaitForExit(3000);
        }
        catch { }
    }

    // 去 GitHub 挑几个星标高的项目学着玩，结果写进 今日所学.txt
    void RunGithubLearn(bool speak)
    {
        string py = Path.Combine(AppDir(), "github_learn.py");
        if (!File.Exists(py))
        {
            if (speak) Say("学习的脚本不在了，改天再学。");
            return;
        }
        try
        {
            ProcessStartInfo psi = new ProcessStartInfo(PyExe(), "-X utf8 \"" + py + "\"");
            psi.UseShellExecute = false;
            psi.CreateNoWindow = true;
            psi.WorkingDirectory = AppDir();
            Process p = Process.Start(psi);
            if (p != null)
            {
                bool done = p.WaitForExit(25000);
                if (!done) { try { p.Kill(); } catch { } }
            }
            string lg = TodayLearnedLine();
            if (speak) Say(lg.Length > 0 ? lg : "今天没连上 GitHub，改天再学。");
            // 自动去学的那一趟不吭声，学到的内容放在右键「今天学了什么」里，想看再点
            Invalidate();
        }
        catch (Exception ex)
        {
            if (speak) Say("去 GitHub 学习没成功：" + ex.Message);
        }
    }

    // 后台去 GitHub 学一趟，不在界面上等它：脚本要跑好几十秒，
    // 放在 UI 线程里跑，那几十秒动画就全卡住了
    void RunGithubLearnBg()
    {
        string py = Path.Combine(AppDir(), "github_learn.py");
        if (!File.Exists(py)) return;
        try
        {
            System.Threading.ThreadPool.QueueUserWorkItem(delegate
            {
                try
                {
                    ProcessStartInfo psi = new ProcessStartInfo(PyExe(), "-X utf8 \"" + py + "\"");
                    psi.UseShellExecute = false;
                    psi.CreateNoWindow = true;
                    psi.WorkingDirectory = AppDir();
                    Process p = Process.Start(psi);
                    if (p != null)
                    {
                        bool done = p.WaitForExit(25000);
                        if (!done) { try { p.Kill(); } catch { } }
                    }
                }
                catch { }
                try { BeginInvoke(new MethodInvoker(delegate() { Invalidate(); })); } catch { }
            });
        }
        catch { }
    }

    void MenuGithubLearn(object s, EventArgs e)
    {
        Say("我去 GitHub 翻翻最近大家都在玩什么。");
        RunGithubLearn(true);
    }

    void MenuStory(object s, EventArgs e) { TellStory(1); }
    void MenuJoke(object s, EventArgs e) { TellStory(2); }
    void MenuNovel(object s, EventArgs e) { TellStory(3); }

    // 背一首古诗：诗本子里一首一首存着，空行分开，随便抽一首念出来
    void MenuPoem(object s, EventArgs e)
    {
        List<string> poems = new List<string>();
        try
        {
            string p = Path.Combine(AppDir(), "古诗.txt");
            if (!File.Exists(p)) { Say("诗本子还不在我手上。"); return; }
            string[] raw = ReadUtf8Lines(p);
            StringBuilder sb = new StringBuilder();
            for (int i = 0; i < raw.Length; i++)
            {
                string ln = raw[i].Trim();
                if (ln.Length == 0)
                {
                    if (sb.Length > 0) { poems.Add(sb.ToString()); sb.Length = 0; }
                    continue;
                }
                if (sb.Length > 0)
                {
                    // 上一行已经收了句号就不要再塞一个逗号，不然念出来是"春烟。，儿童"
                    char last = sb[sb.Length - 1];
                    if ("，。！？；、".IndexOf(last) < 0) sb.Append("，");
                    else if (last == '。') sb.Append("");
                }
                sb.Append(ln);
            }
            if (sb.Length > 0) poems.Add(sb.ToString());
        }
        catch { }
        if (poems.Count == 0) { Say("诗本子是空的。"); return; }
        string one = poems[rnd.Next(poems.Count)];
        if (!voiceOn) voiceOn = true;
        SayAs("背一首。" + one, CurVoice());
        moodKind = 1;
        moodTicks = 60;
    }

    // 学一句英语：英文先念一遍（用英文嗓子），再讲中文意思，气泡里也留着字
    void MenuEnglish(object s, EventArgs e)
    {
        string en = "", cn = "";
        try
        {
            string p = Path.Combine(AppDir(), "英语.txt");
            if (!File.Exists(p)) { Say("英文本子还不在我手上。"); return; }
            string[] raw = ReadUtf8Lines(p);
            List<string> ok = new List<string>();
            for (int i = 0; i < raw.Length; i++)
            {
                string ln = raw[i].Trim();
                if (ln.Length == 0 || ln.StartsWith("#")) continue;
                if (ln.IndexOf('|') < 0) continue;
                ok.Add(ln);
            }
            if (ok.Count == 0) { Say("本子里还没抄句子。"); return; }
            string one = ok[rnd.Next(ok.Count)];
            int cut = one.IndexOf('|');
            en = one.Substring(0, cut).Trim();
            cn = one.Substring(cut + 1).Trim();
        }
        catch { }
        if (en.Length == 0) { Say("这一下没翻到本子。"); return; }
        if (!voiceOn) voiceOn = true;
        SayAs(en, "en-US-AriaNeural");
        SayAs("意思是，" + cn, CurVoice());
        moodKind = 1;
        moodTicks = 50;
    }

    // 唱一段：旋律在 python 那边现场合成，合好了再交给播放器放
    void MenuSing(object s, EventArgs e)
    {
        string py = Path.Combine(AppDir(), "sing.py");
        if (!File.Exists(py)) { Say("我还没学会唱。"); return; }
        Say("我给你哼一段小星星。");
        // 唱歌的时候脑袋轻轻晃、音符往上飘，光出声没画面太干
        lieHold = 0;
        actKind = 4;
        actHold = 640;
        Invalidate();
        System.Threading.ThreadPool.QueueUserWorkItem(delegate
        {
            try
            {
                ProcessStartInfo psi = new ProcessStartInfo(PyExe(), "-X utf8 \"" + py + "\"");
                psi.UseShellExecute = false;
                psi.CreateNoWindow = true;
                psi.WorkingDirectory = AppDir();
                Process p = Process.Start(psi);
                if (p != null) p.WaitForExit(20000);
                string wav = Path.Combine(AppDir(), "sing.wav");
                if (!File.Exists(wav) || new FileInfo(wav).Length < 4096) return;
                // 先等开场那句说完，两路声音叠在一起会听不清
                System.Threading.Thread.Sleep(2800);
                System.Media.SoundPlayer snd = new System.Media.SoundPlayer(wav);
                snd.Play();
                double ds = WavSeconds(wav);
                System.Threading.Thread.Sleep((int)((ds > 0 ? ds : 6) * 1000) + 300);
                try { snd.Stop(); snd.Dispose(); } catch { }
                BeginInvoke(new MethodInvoker(delegate() { moodKind = 1; moodTicks = 50; Invalidate(); }));
            }
            catch { }
        });
    }

    void MenuToggleAutoTell(object s, EventArgs e)
    {
        autoTellOn = !autoTellOn;
        try { ToolStripMenuItem mi = FindMenuItem("autotell"); if (mi != null) mi.Checked = autoTellOn; } catch { }
        Say(autoTellOn ? "行，我隔一阵就给你讲一段。" : "那我先不讲了，想听再喊我。");
    }

    ToolStripMenuItem FindMenuItem(string name)
    {
        if (ContextMenuStrip == null) return null;
        foreach (ToolStripItem it in ContextMenuStrip.Items)
        {
            ToolStripMenuItem mi = it as ToolStripMenuItem;
            if (mi == null) continue;
            if (mi.Name == name) return mi;
            ToolStripMenuItem sub = FindIn(mi, name);
            if (sub != null) return sub;
        }
        return null;
    }

    ToolStripMenuItem FindIn(ToolStripMenuItem parent, string name)
    {
        foreach (ToolStripItem it in parent.DropDownItems)
        {
            ToolStripMenuItem mi = it as ToolStripMenuItem;
            if (mi == null) continue;
            if (mi.Name == name) return mi;
            ToolStripMenuItem sub = FindIn(mi, name);
            if (sub != null) return sub;
        }
        return null;
    }

    // 讲点什么：1 故事 / 2 段子 / 3 老书
    void TellStory(int kind)
    {
        if (brainThread != null && brainThread.IsAlive)
        {
            Say("等我把上一段说完。");
            return;
        }
        string cmd = (kind == 2) ? "joke" : ((kind == 3) ? "novel" : "story");
        string intro = (kind == 2) ? "给你说个段子。" : ((kind == 3) ? "念一段老书听听。" : "我讲个故事。");
        if (!voiceOn) voiceOn = true;
        Say(intro);
        brainThread = new System.Threading.Thread(delegate()
        {
            string json = "";
            try
            {
                string exeDir = Path.GetDirectoryName(Application.ExecutablePath);
                string py = Path.Combine(exeDir, "voice.py");
                if (!System.IO.File.Exists(py))
                {
                    BeginInvoke(new MethodInvoker(delegate() { Say("手里没故事本子，等我更新一下自己。"); }));
                    return;
                }
                string askPath = Path.Combine(exeDir, "ask_story.txt");
                File.WriteAllText(askPath, "来一个", new System.Text.UTF8Encoding(false));
                ProcessStartInfo pi = new ProcessStartInfo();
                pi.FileName = PyExe();
                pi.Arguments = "\"" + py + "\" " + cmd + " --file \"" + askPath + "\"";
                pi.UseShellExecute = false;
                pi.CreateNoWindow = true;
                pi.RedirectStandardOutput = true;
                pi.RedirectStandardError = true;
                pi.StandardOutputEncoding = System.Text.Encoding.UTF8;
                pi.StandardErrorEncoding = System.Text.Encoding.UTF8;
                pi.WindowStyle = ProcessWindowStyle.Hidden;
                Process p = Process.Start(pi);
                string so = p.StandardOutput.ReadToEnd();
                p.StandardError.ReadToEnd();
                p.WaitForExit(90000);
                if (so != null) json = so.Trim();
            }
            catch { }

            string reply = JsonStr(json, "reply");
            int mood = JsonInt(json, "mood");
            try
            {
                BeginInvoke(new MethodInvoker(delegate()
                {
                    if (mood > 0 && mood <= 8) { moodKind = mood; moodTicks = 70; }
                    if (reply != null && reply.Length > 0) SayAs(reply, CurVoice());
                    else Say("这一下没想起来讲什么，再点我一次。");
                    Invalidate();
                }));
            }
            catch { }
        });
        brainThread.IsBackground = true;
        brainThread.Start();
    }

    // ===== 桌面待法：满身 / 贴边偷看 / 悬浮球 / 收起 =====
    // 2026-11-22 晚（用户要求）：干活时它可以在屏幕侧边只露半边（像乔巴那样探头），
    // 也可以缩成悬浮球，点一下再出来。四种模式随时可换，选过就记住。
    int FullW { get { return (int)(W * uiScale); } }
    int FullH { get { return (int)(H * uiScale); } }

    void LoadModeSettings()
    {
        try
        {
            RegistryKey k = Registry.CurrentUser.OpenSubKey("Software\\DaoPet");
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
            RegistryKey k = Registry.CurrentUser.CreateSubKey("Software\\DaoPet");
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
                // 关键：人物画在窗口正中，所以要让「窗口中心」正好压在屏幕边上，
                // 屏幕才刚好切掉一半身子。以前按窗口宽露出三成算，露出的其实是窗口左侧的空白，
                // 屏幕上什么都看不见（2026-11-22 实测踩到）。
                if (y > wa.Bottom - FullH / 2) y = wa.Bottom - FullH / 2;
                int x = peekSide == 1 ? wa.Left - FullW / 2 : wa.Right - FullW / 2;
                // 2026-11-22：原来是"啪"一下贴到边上。改成从当前位置挪过去（520ms 缓出），
                // 像是自己退到边框后面，不是瞬移。
                if (Math.Abs(Location.X - x) > 6)
                {
                    Bounds = new Rectangle(Location.X, y, FullW, FullH);
                    SlideTo(x);
                }
                else
                {
                    Bounds = new Rectangle(x, y, FullW, FullH);
                }
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
        // 2026-11-22：原来"每帧走剩下的三分之一"，四五十毫秒就窜过去了，看着像瞬移。
        // 改成按时长算：整段 520ms，先快后慢（ease-out），像人挪过去而不是闪过去。
        if (slideTimer == null)
        {
            slideTimer = new System.Windows.Forms.Timer();
            slideTimer.Interval = 16;
            slideTimer.Tick += delegate(object s, EventArgs e)
            {
                if (slideTargetX == int.MinValue) { slideTimer.Stop(); return; }
                int t = Environment.TickCount - slideStartTick;
                float u = t / 520f;
                if (u > 1f) u = 1f;
                float e2 = 1f - (1f - u) * (1f - u) * (1f - u);   // easeOutCubic
                int x = slideStartX + (int)((slideTargetX - slideStartX) * e2);
                if (Math.Abs(slideTargetX - x) <= 2 || u >= 1f)
                {
                    Location = new Point(slideTargetX, Location.Y);
                    slideTimer.Stop();
                    slideTargetX = int.MinValue;
                    return;
                }
                Location = new Point(x, Location.Y);
            };
        }
        if (slideTargetX == int.MinValue)
        {
            slideStartX = Location.X;
            slideStartTick = Environment.TickCount;
        }
        else
        {
            // 半路改目标：从当前位置重新起算，别跳
            slideStartX = Location.X;
            slideStartTick = Environment.TickCount;
        }
        slideTargetX = targetX;
        if (!slideTimer.Enabled) slideTimer.Start();
    }
    int slideStartX = 0;
    int slideStartTick = 0;

    int PeekRestX()
    {
        Rectangle wa = Screen.PrimaryScreen.WorkingArea;
        return peekSide == 1 ? wa.Left - FullW / 2 : wa.Right - FullW / 2;
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
        try
        {
            if (ContextMenuStrip == null) return;
            foreach (ToolStripItem it in ContextMenuStrip.Items) RefreshChecksIn(it);
        }
        catch { }
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

    void BuildMenu()
    {
        ContextMenuStrip m = new ContextMenuStrip();

        // 一、说话：最常用，放最上头
        ToolStripMenuItem gTalk = new ToolStripMenuItem("跟我说话");
        gTalk.DropDownItems.Add("语音对话：我说话，你回答", null, new EventHandler(MenuVoiceChat));
        // 常驻听名字：喊一声「道」就应你，再接着听下一句
        ToolStripMenuItem wakeItem = new ToolStripMenuItem("喊我名字就醒（说「道」）");
        wakeItem.Checked = wakeOn;
        wakeItem.Click += new EventHandler(MenuWake);
        gTalk.DropDownItems.Add(wakeItem);
        gTalk.DropDownItems.Add("听我说", null, new EventHandler(MenuHear));
        gTalk.DropDownItems.Add("问它一句（它会念出来）", null, new EventHandler(MenuAskBrain));
        gTalk.DropDownItems.Add("跟我打字聊天", null, new EventHandler(MenuTalk));
        gTalk.DropDownItems.Add(new ToolStripSeparator());
        gTalk.DropDownItems.Add("讲讲这道题", null, new EventHandler(MenuExplain));
        gTalk.DropDownItems.Add("总结一下", null, new EventHandler(MenuSum));
        gTalk.DropDownItems.Add("翻译一句", null, new EventHandler(MenuTranslate));
        gTalk.DropDownItems.Add("同声翻译：我说中文，出英文", null, new EventHandler(MenuSimCn2En));
        gTalk.DropDownItems.Add("同声翻译：我说英文，出中文", null, new EventHandler(MenuSimEn2Cn));
        m.Items.Add(gTalk);

        // 二、声音
        ToolStripMenuItem gSound = new ToolStripMenuItem("我的声音");
        ToolStripMenuItem voiceItem = new ToolStripMenuItem("开口说话");
        voiceItem.Checked = voiceOn;
        voiceItem.Click += new EventHandler(MenuVoice);
        gSound.DropDownItems.Add(voiceItem);
        gSound.DropDownItems.Add("换个声音", null, new EventHandler(MenuSwapVoice));
        // 三档音量，白天按档位，夜里和午休自动往下压
        ToolStripMenuItem volMenu = new ToolStripMenuItem("说话音量");
        string[] volNames = { "轻一点", "正常", "响一点" };
        for (int vi = 0; vi < 3; vi++)
        {
            ToolStripMenuItem vmi = new ToolStripMenuItem(volNames[vi]);
            vmi.Tag = vi;
            vmi.Checked = (volLevel == vi);
            vmi.Click += new EventHandler(MenuVolLevel);
            volMenu.DropDownItems.Add(vmi);
        }
        gSound.DropDownItems.Add(volMenu);
        gSound.DropDownItems.Add("测一下麦克风", null, new EventHandler(MenuMicTest));
        // 声音、闲话、桌面收进一个「更多」，一级菜单别铺太开

        // 三、形象
        ToolStripMenuItem gLook = new ToolStripMenuItem("我的样子");
        gLook.DropDownItems.Add("换个模样", null, new EventHandler(MenuChange));
        // 想让今天是谁就点谁，不点就跟着日期走
        ToolStripMenuItem dayMenu = new ToolStripMenuItem("今天我要是谁");
        if (faceNames != null)
        {
            for (int di = 0; di < faceNames.Length; di++)
            {
                ToolStripMenuItem dmi = new ToolStripMenuItem(faceNames[di]);
                dmi.Tag = di;
                dmi.Click += new EventHandler(MenuChooseToday);
                dayMenu.DropDownItems.Add(dmi);
            }
        }
        dayMenu.DropDownItems.Add(new ToolStripSeparator());
        dayMenu.DropDownItems.Add("还是跟着日期换", null, new EventHandler(MenuClearToday));
        gLook.DropDownItems.Add(dayMenu);
        gLook.DropDownItems.Add("走两步给你看", null, new EventHandler(MenuWalkDemo));
        gLook.DropDownItems.Add("哭一个", null, new EventHandler(MenuCry));
        // 新学的几手：飞、御剑、骑坐骑、跳舞、喝茶、看电视
        gLook.DropDownItems.Add(new ToolStripSeparator());
        gLook.DropDownItems.Add("飞一趟", null, new EventHandler(MenuActFly));
        gLook.DropDownItems.Add("御剑飞行", null, new EventHandler(MenuActSword));
        gLook.DropDownItems.Add("骑坐骑出去", null, new EventHandler(MenuActRide));
        gLook.DropDownItems.Add("跳个舞", null, new EventHandler(MenuActDance));
        gLook.DropDownItems.Add("喝杯咖啡", null, new EventHandler(MenuActTea));
        gLook.DropDownItems.Add("看会儿电视", null, new EventHandler(MenuActTv));
        ToolStripMenuItem chatItem = new ToolStripMenuItem("闲聊（手动开）");
        chatItem.Checked = chatMode;
        chatItem.Click += new EventHandler(MenuToggleChat);
        gLook.DropDownItems.Add(chatItem);
        m.Items.Add(gLook);

        // 四、记性
        ToolStripMenuItem gMind = new ToolStripMenuItem("记性和学问");
        gMind.DropDownItems.Add("我记住了什么", null, new EventHandler(MenuMemory));
        // v0.107：记事本不再只有"说一句记一下"，右键能直接把清单摊开，逐条划掉
        gMind.DropDownItems.Add("记事本（点一下划掉）", null, new EventHandler(MenuNotes));

        gMind.DropDownItems.Add("同步记忆（跨网）", null, new EventHandler(MenuSync));
        gMind.DropDownItems.Add("我今天学了什么", null, new EventHandler(MenuKnowledge));
        m.Items.Add(gMind);

        // 讲点什么：故事、段子、老书，还可以让它自己隔一阵主动讲
        ToolStripMenuItem gTell = new ToolStripMenuItem("给我讲点什么");
        gTell.DropDownItems.Add("讲个故事", null, new EventHandler(MenuStory));
        gTell.DropDownItems.Add("说个段子", null, new EventHandler(MenuJoke));
        gTell.DropDownItems.Add("念段小说", null, new EventHandler(MenuNovel));
        gTell.DropDownItems.Add("背首古诗", null, new EventHandler(MenuPoem));
        gTell.DropDownItems.Add("学一句英语", null, new EventHandler(MenuEnglish));
        gTell.DropDownItems.Add("唱一段", null, new EventHandler(MenuSing));
        ToolStripMenuItem autoTell = new ToolStripMenuItem("自己隔一阵讲一段");
        autoTell.Checked = autoTellOn;
        autoTell.Name = "autotell";
        autoTell.Click += new EventHandler(MenuToggleAutoTell);
        gTell.DropDownItems.Add(autoTell);


        // 五、桌面
        ToolStripMenuItem gDesk = new ToolStripMenuItem("桌面");
        gDesk.DropDownItems.Add("换张新壁纸", null, new EventHandler(MenuWallpaper));
        gDesk.DropDownItems.Add("今日简报", null, new EventHandler(MenuBrief));
        gDesk.DropDownItems.Add("看看电脑状态", null, new EventHandler(MenuStatus));
        gDesk.DropDownItems.Add("打开回收站", null, new EventHandler(MenuRecycle));
        ToolStripMenuItem gMode = new ToolStripMenuItem("我在桌面上的样子");
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
        // 三个二级菜单合到一处，右键点开只有四条主干
        ToolStripMenuItem gMore = new ToolStripMenuItem("声音、闲话和桌面");
        gMore.DropDownItems.Add(gSound);
        gMore.DropDownItems.Add(gTell);
        gMore.DropDownItems.Add(gDesk);
        m.Items.Add(gMore);

        // 六、维护
        ToolStripMenuItem gSys = new ToolStripMenuItem("维护");
        gSys.DropDownItems.Add("我现在就检查更新", null, new EventHandler(MenuSelfUpdate));
        // 版本号直接摆在菜单里，不用去网页上看
        ToolStripMenuItem verItem = new ToolStripMenuItem("当前版本 v" + SyncServer.APP_VER + "（点上面那行可以查新版）");
        verItem.Enabled = false;
        gSys.DropDownItems.Add(verItem);
        gSys.DropDownItems.Add("去 GitHub 学点东西", null, new EventHandler(MenuGithubLearn));
        gSys.DropDownItems.Add("给自己做个备份", null, new EventHandler(MenuBackup));
        ToolStripMenuItem autostart = new ToolStripMenuItem("开机自动出现");
        autostart.Checked = IsAutoStart();
        autostart.Click += new EventHandler(MenuAutoStart);
        autostart.Name = "autostart";
        gSys.DropDownItems.Add(autostart);
        m.Items.Add(gSys);

        m.Items.Add(new ToolStripSeparator());
        m.Items.Add("退出", null, new EventHandler(MenuExit));
        this.ContextMenuStrip = m;
    }

    bool IsAutoStart()
    {
        try
        {
            RegistryKey rk = Registry.CurrentUser.OpenSubKey("Software\\Microsoft\\Windows\\CurrentVersion\\Run");
            if (rk == null) return false;
            object v = rk.GetValue("DaoPet");
            if (v == null) v = rk.GetValue("DoubaoPet");
            rk.Close();
            return v != null;
        }
        catch { return false; }
    }

    void SetAutoStart(bool on)
    {
        try
        {
            RegistryKey rk = Registry.CurrentUser.OpenSubKey("Software\\Microsoft\\Windows\\CurrentVersion\\Run", true);
            if (rk == null) return;
            // 清掉旧名字，避免开机时冒出两个我
            try { rk.DeleteValue("DoubaoPet", false); } catch { }
            if (on) rk.SetValue("DaoPet", "\"" + Application.ExecutablePath + "\"");
            else rk.DeleteValue("DaoPet", false);
            rk.Close();
        }
        catch { }
    }

    void MenuAutoStart(object s, EventArgs e)
    {
        ToolStripMenuItem mi = (ToolStripMenuItem)s;
        bool want = !IsAutoStart();
        SetAutoStart(want);
        mi.Checked = want;
        Say(want ? "好，开机我就自己出来。" : "那我就不开机自己出现了。");
    }

    void Say(string text)
    {
        bubble = text;
        bubbleFrames = 60 + (text == null ? 0 : text.Length * 3);
        if (bubbleFrames > 140) bubbleFrames = 140;   // 说完就散，不在屏幕上赖着
        Invalidate();
        SpeakOut(text);
    }

    // 一天只在第一次见着他的时候打个招呼：开机时说，跨天后他回来时补一句
    void GreetIfDue(bool fromStartup)
    {
        try
        {
            if (greetDay.Date == DateTime.Today) return;
            int h = DateTime.Now.Hour;
            // 开机不管几点都打招呼；平时只在白天到晚上这段时间补
            if (!fromStartup && (h < 5 || h >= 23)) return;
            MarkGreeted();
            SpeakGreet();
        }
        catch { }
    }

    // 问候先立刻显示在气泡上，语音丢给队列。队列是一句一句播的，
    // 前面那句没说完它会自己等着，不用在这儿反复重试（重试会把同一句排好几遍）
    void SpeakGreet()
    {
        try
        {
            // 正在听你说话就别插嘴，不然麦克风录的是它自己的声音
            if (hearBusy) return;
            bubble = GreetText();
            bubbleFrames = 150;
            Invalidate();
            SpeakOut(bubble);
        }
        catch { }
    }

    void MarkGreeted()
    {
        greetDay = DateTime.Today;
        try
        {
            RegistryKey k = Registry.CurrentUser.CreateSubKey("Software\\DaoPet");
            if (k != null) { k.SetValue("GreetDay", greetDay.ToString("yyyy-MM-dd")); k.Close(); }
        }
        catch { }
    }

    string GreetText()
    {
        int h = DateTime.Now.Hour;
        string who = CurName();
        if (h >= 5 && h < 11) return "老师早啊，我是" + who + "。新的一天，咱们开始吧。";
        if (h >= 11 && h < 14) return "老师中午好，我是" + who + "。饭吃了没，歇一会儿再忙。";
        if (h >= 14 && h < 18) return "老师下午好，我是" + who + "。课上得顺不顺，累不累？";
        if (h >= 18 && h < 23) return "晚上好老师，我是" + who + "。今天辛苦了，早点歇着。";
        return "这么晚还没睡呀老师，我是" + who + "。早点休息，明天还要上课呢。";
    }

    readonly string[] CHAT_COMMON = new string[] {
        "老师，歇会儿，眼睛离屏幕远点。",
        "坐久了腰会酸，起来走两步吧。",
        "这事急不来，先把最要紧的那件做完。",
        "我刚才自己晃了两圈，有点闲，来找你说说话。",
        "作业改完了吗？没改完我陪你。",
        "班上那帮孩子今天有没有闹出什么笑话？",
        "一道题讲三遍还不会，正常，别上火。",
        "我在这儿呢，你不用管我。",
        "水杯空了就去接一杯，别憋着。",
        "你要是烦了，跟我说说也成，我听着。"
    };

    readonly string[] CHAT_MORNING = new string[] {
        "早读站一站，嗓子记得润一下。",
        "第一节最容易犯困，你也别硬撑。",
        "早上脑子最清楚，难的题放这会儿讲。"
    };

    readonly string[] CHAT_NOON = new string[] {
        "饭点到了，别又拿个包子对付。",
        "中午眯二十分钟，下午能顶两节课。",
        "吃完饭别马上趴着改作业，对胃不好。"
    };

    readonly string[] CHAT_AFTERNOON = new string[] {
        "下午这几节课最难熬，撑住。",
        "嗓子哑了就别喊了，写黑板上。",
        "太阳落下去点，教室里能凉快点。"
    };

    readonly string[] CHAT_NIGHT = new string[] {
        "作业改不动就先放放，明天再弄。",
        "晚上少看会儿手机，眼睛受不了。",
        "明天还有早读，别熬太晚。"
    };

    void MenuToggleChat(object s, EventArgs e)
    {
        chatMode = !chatMode;
        try
        {
            RegistryKey k = Registry.CurrentUser.CreateSubKey("Software\\DaoPet");
            if (k != null) { k.SetValue("ChatMode", chatMode ? "1" : "0"); k.Close(); }
        }
        catch { }
        ResetChatTimer();
        Say(chatMode ? "行，我时不时跟你唠两句。不想听就再点一下这个。" : "好，那我安静待着。");
    }

    void ResetChatTimer()
    {
        // 一秒约 22 帧，隔 20 到 50 分钟随机说一次
        chatCountdown = rnd.Next(26000, 66000);
    }

    string RandomChatLine()
    {
        int h = DateTime.Now.Hour;
        string[] pool;
        if (h >= 5 && h < 11) pool = CHAT_MORNING;
        else if (h >= 11 && h < 14) pool = CHAT_NOON;
        else if (h >= 14 && h < 18) pool = CHAT_AFTERNOON;
        else pool = CHAT_NIGHT;
        if (rnd.Next(100) < 30) pool = CHAT_COMMON;
        return pool[rnd.Next(pool.Length)];
    }

    // 录三秒，量一下麦克风到底能收到多少声，用大白话说结果
    void MenuMicTest(object s, EventArgs e)
    {
        Say("我听听环境，三秒。");
        System.Threading.Thread th = new System.Threading.Thread(delegate()
        {
            string o = "";
            try
            {
                string py = Path.Combine(Path.GetDirectoryName(Application.ExecutablePath), "hear.py");
                if (!System.IO.File.Exists(py)) { o = "NOFILE"; }
                else
                {
                    ProcessStartInfo pi = new ProcessStartInfo();
                    pi.FileName = PyExe();
                    pi.Arguments = "\"" + py + "\" --level 3";
                    pi.UseShellExecute = false;
                    pi.CreateNoWindow = true;
                    pi.RedirectStandardOutput = true;
                    pi.RedirectStandardError = true;
                    pi.StandardOutputEncoding = System.Text.Encoding.UTF8;
                    pi.StandardErrorEncoding = System.Text.Encoding.UTF8;
                    pi.WindowStyle = ProcessWindowStyle.Hidden;
                    Process p = Process.Start(pi);
                    string so = p.StandardOutput.ReadToEnd();
                    p.StandardError.ReadToEnd();
                    p.WaitForExit(30000);
                    o = so == null ? "" : so.Trim();
                }
            }
            catch (Exception ex) { o = "ERR " + ex.Message; }

            string msg;
            if (o.StartsWith("NOFILE")) msg = "听觉模块不在，得更新一下我。";
            else if (o.StartsWith("ERR")) msg = "没测成：" + o;
            else
            {
                int rms = 0;
                int peak = 0;
                int i = o.IndexOf("rms=");
                if (i >= 0)
                {
                    int st = i + 4;
                    int en = o.IndexOf('|', st);
                    string v = en > 0 ? o.Substring(st, en - st) : o.Substring(st);
                    int.TryParse(v, out rms);
                }
                i = o.IndexOf("peak=");
                if (i >= 0)
                {
                    int st = i + 5;
                    int en = o.IndexOf('|', st);
                    string v = en > 0 ? o.Substring(st, en - st) : o.Substring(st);
                    int.TryParse(v, out peak);
                }
                // v22：按说话峰值判断，录音端已经自动放大过一轮，不再稍微轻一点就喊“太小”
                if (peak <= 0) msg = "一点声都没有，看看麦克风是不是被关掉了。";
                else if (peak < 900) msg = "只能收到一点点，把麦克风音量调大再试。";
                else if (peak < 3000) msg = "能听见，但还偏轻。";
                else msg = "这音量够用，平常声说话就行。";
            }
            try { BeginInvoke(new MethodInvoker(delegate() { Say("测完了：" + msg); })); } catch { }
        });
        th.IsBackground = true;
        th.Start();
    }

    void MenuVoice(object s, EventArgs e)
    {
        voiceOn = !voiceOn;
        ToolStripMenuItem mi = (ToolStripMenuItem)s;
        mi.Checked = voiceOn;
        if (voiceOn) Say("好，我开口了。");
        else Say("那我先不说话了。");
    }

    void MenuVolLevel(object s, EventArgs e)
    {
        ToolStripMenuItem mi = (ToolStripMenuItem)s;
        try { volLevel = Convert.ToInt32(mi.Tag); } catch { volLevel = 1; }
        if (volLevel < 0) volLevel = 0;
        if (volLevel > 2) volLevel = 2;
        try
        {
            RegistryKey k = Registry.CurrentUser.CreateSubKey("Software\\DaoPet");
            if (k != null) { k.SetValue("VolLevel", volLevel); k.Close(); }
        }
        catch { }
        EnsureSpeakerLevel();
        Say(volLevel == 0 ? "好，我说话轻一点。" : (volLevel == 2 ? "行，我大点声。" : "调回正常音量了。"));
    }

    void MenuWalkDemo(object s, EventArgs e)
    {
        try
        {
            Rectangle wa = Screen.FromControl(this).WorkingArea;
            int dir = (Location.X + Width / 2 < wa.Width / 2) ? 1 : -1;
            int nx = Location.X + dir * 180;
            if (nx < wa.Left + 2) nx = wa.Left + 2;
            if (nx > wa.Right - Width - 2) nx = wa.Right - Width - 2;
            walkTargetX = nx;
            walkTargetY = Location.Y;
            walkDirX = dir;
            Say("好，我走两步，你看看腿脚利索不利索。");
        }
        catch { }
    }

    // 睡一觉：躺平三十秒，头上飘 Z
    void MenuLieDown(object s, EventArgs e)
    {
        lieHold = 660;
        idleTicks = 2000;   // 顺便把空闲计时推过门槛，坐姿和犯困一起生效
        Say("那我躺下歇会儿，你忙你的。");
    }

    // 哭一个：让它真掉几滴眼泪
    void MenuCry(object s, EventArgs e)
    {
        cryHold = 700;
        moodKind = 3;
        moodTicks = 120;
        Say("嗯……我也有心里不好受的时候。");
    }

    // 六个生活动作的菜单入口，都走同一个口子：定动作类型 + 给个持续时间
    void StartAct(int kind)
    {
        if (lying) { lieHold = 0; lying = false; }
        actKind = kind;
        actHold = kind >= 4 ? 400 : 470;
        // 要赶路的先把目的地清掉，让行走逻辑马上重新挑一个
        if (kind >= 1 && kind <= 3) walkTargetX = -999999;
        if (kind == 1) Say("我飞过去。");
        else if (kind == 2) Say("踏剑而行，走。");
        else if (kind == 3) Say("骑上它，慢慢走。");
        else if (kind == 4) Say("跳一段，你听听节拍。");
        else if (kind == 5) Say("来杯咖啡，握手里慢慢喝。");
        else if (kind == 6) Say("看会儿电视，别嫌吵。");
    }

    void MenuActFly(object s, EventArgs e) { StartAct(1); }
    void MenuActSword(object s, EventArgs e) { StartAct(2); }
    void MenuActRide(object s, EventArgs e) { StartAct(3); }
    void MenuActDance(object s, EventArgs e) { StartAct(4); }
    void MenuActTea(object s, EventArgs e) { StartAct(5); }
    void MenuActTv(object s, EventArgs e) { StartAct(6); }

    void MenuSwapVoice(object s, EventArgs e)
    {
        vIdx = (vIdx + 1) % VName.Length;
        try
        {
            RegistryKey k = Registry.CurrentUser.CreateSubKey("Software\\DaoPet");
            if (k != null) { k.SetValue("VoiceIdx", vIdx); k.Close(); }
        }
        catch { }
        SayAs("换成「" + VName[vIdx] + "」了，你听听像不像。", CurVoice());
    }

    string VoiceDir()
    {
        string d = Path.Combine(Path.GetTempPath(), "daovoice");
        if (!Directory.Exists(d)) Directory.CreateDirectory(d);
        return d;
    }

    string BackupScript()
    {
        return
            "param([string]$dir)\r\n" +
            "$dst = Join-Path $dir '备份'\r\n" +
            "if (-not (Test-Path $dst)) { New-Item -ItemType Directory -Path $dst | Out-Null }\r\n" +
            "$stamp = Get-Date -Format 'yyyyMMdd_HHmm'\r\n" +
            "$zip = Join-Path $dst ('道_' + $stamp + '.zip')\r\n" +
            "$list = @()\r\n" +
            "foreach ($n in @('道.exe','pet.cs','pet.manifest','记忆.txt','我说的话.txt','make_icons.ps1','daily_brief.ps1','daily_bing.ps1','hear.py','backup.ps1')) {\r\n" +
            "  $p = Join-Path $dir $n\r\n" +
            "  if (Test-Path -LiteralPath $p) { $list += $p }\r\n" +
            "}\r\n" +
            "foreach ($d in @('icons','faces')) {\r\n" +
            "  $p = Join-Path $dir $d\r\n" +
            "  if (Test-Path -LiteralPath $p) { $list += $p }\r\n" +
            "}\r\n" +
            "if ($list.Count -eq 0) { Write-Output 'NONE'; exit }\r\n" +
            "Compress-Archive -Path $list -DestinationPath $zip -Force\r\n" +
            "Get-ChildItem -LiteralPath $dst -Filter '道_*.zip' | Sort-Object LastWriteTime -Descending | Select-Object -Skip 7 | Remove-Item -Force\r\n" +
            "$f = Get-Item -LiteralPath $zip\r\n" +
            "Write-Output ('OK|' + $f.Name + '|' + [math]::Round($f.Length/1MB,1))\r\n";
    }

    void BackupNow(bool silent)
    {
        if (backupThread != null && backupThread.IsAlive) return;
        if (!silent) Say("正在把自己打包备份…");
        backupThread = new System.Threading.Thread(delegate()
        {
            string result = "";
            try
            {
                string dir = AppDir();
                string ps1 = Path.Combine(dir, "backup.ps1");
                try { File.WriteAllText(ps1, BackupScript(), new UTF8Encoding(true)); }
                catch { }
                ProcessStartInfo pi = new ProcessStartInfo();
                pi.FileName = "powershell.exe";
                pi.Arguments = "-NoProfile -ExecutionPolicy Bypass -File \"" + ps1 + "\" -dir \"" + dir + "\"";
                pi.UseShellExecute = false;
                pi.CreateNoWindow = true;
                pi.WindowStyle = ProcessWindowStyle.Hidden;
                pi.RedirectStandardOutput = true;
                pi.StandardOutputEncoding = Encoding.UTF8;
                Process p = Process.Start(pi);
                result = p.StandardOutput.ReadToEnd().Trim();
                p.WaitForExit(180000);
            }
            catch { result = ""; }

            string msg;
            if (result.StartsWith("OK|"))
            {
                string[] parts = result.Split('|');
                msg = "备份好了，一共 " + (parts.Length > 2 ? parts[2] : "?") + " MB，存在「备份」文件夹里，我留最近 7 份。";
            }
            else
            {
                msg = "备份没成功，可能磁盘空间不够。";
            }
            try
            {
                BeginInvoke((MethodInvoker)delegate()
                {
                    if (hearBusy) return;
                    bubble = msg;
                    bubbleFrames = 150;
                    Invalidate();
                    SpeakOut(msg);
                });
            }
            catch { }
        });
        backupThread.IsBackground = true;
        backupThread.Start();
    }

    void MenuBackup(object s, EventArgs e)
    {
        BackupNow(false);
    }

    void AutoBackupIfDue()
    {
        try
        {
            string dst = Path.Combine(AppDir(), "备份");
            DateTime last = DateTime.MinValue;
            if (Directory.Exists(dst))
            {
                string[] zips = Directory.GetFiles(dst, "道_*.zip");
                for (int i = 0; i < zips.Length; i++)
                {
                    DateTime w = File.GetLastWriteTime(zips[i]);
                    if (w > last) last = w;
                }
            }
            if ((DateTime.Now - last).TotalDays >= 7) BackupNow(true);
        }
        catch { }
    }

    void SpeakOut(string text)
    {
        SpeakOut(text, CurVoice());
    }

    void SpeakOut(string text, string voice)
    {
        SpeakOut(text, voice, CurFx());
    }

    void SpeakOut(string text, string voice, string fx)
    {
        if (!voiceOn) return;
        if (text == null) return;
        string t2 = text.Replace("\r", " ").Replace("\n", " ").Trim();
        if (t2.Length == 0) return;
        if (t2.Length > 90) t2 = t2.Substring(0, 90);
        SpeakJob job = new SpeakJob();
        job.text = t2; job.voice = voice; job.fx = fx;
        lock (speakQLock)
        {
            // 最多排三句，再多就丢掉，免得积一堆话过好一会儿才一起冒出来
            if (speakQueue.Count >= 3) return;
            speakQueue.Enqueue(job);
            if (voiceThread == null || !voiceThread.IsAlive)
            {
                voiceThread = new System.Threading.Thread(SpeakLoop);
                voiceThread.IsBackground = true;
                voiceThread.Start();
            }
        }
    }

    // 本机装了多套 python，只有 E:\Python313 那套装了 edge_tts。
    // 直接写 "python" 在服务进程里解析不到，合成必然失败（v67 踩过：/tts 一直回 TTSFAIL）
    public static string PyExe()
    {
        string[] cands = new string[] {
            @"E:\Python313\python.exe",
            @"C:\Python313\python.exe",
            @"C:\Users\LDY\AppData\Local\Programs\Python\Python313\python.exe"
        };
        foreach (string s in cands) { try { if (File.Exists(s)) return s; } catch { } }
        return "python";
    }

    // 给手机端用的：只合成不播，返回 mp3 文件路径。手机拿这条路放电脑的声音，
    // 音色比手机自带 TTS 自然得多。缓存键跟播放用同一套 text|voice，念过就直接复用
    public static string TtsFile(string text, string voice)
    {
        try
        {
            if (text == null) return "";
            string t2 = text.Replace("\r", " ").Replace("\n", " ").Trim();
            if (t2.Length == 0) return "";
            if (t2.Length > 90) t2 = t2.Substring(0, 90);
            if (voice == null || voice.Trim().Length == 0) voice = "zh-CN-XiaoxiaoNeural";
            string dir = Path.Combine(Path.GetTempPath(), "daovoice");
            if (!Directory.Exists(dir)) Directory.CreateDirectory(dir);
            string key = "tts" + Math.Abs((t2 + "|" + voice + "|tts9").GetHashCode()).ToString();
            string mp3 = Path.Combine(dir, key + ".mp3");
            string txt = Path.Combine(dir, key + ".txt");
            if (File.Exists(mp3) && new FileInfo(mp3).Length > 2048) return mp3;
            string py = Path.Combine(dir, "say.py");
            if (!File.Exists(py))
            {
                File.WriteAllText(py,
                    "import asyncio,sys\n" +
                    "from edge_tts import Communicate\n" +
                    "t=open(sys.argv[1],'r',encoding='utf-8').read()\n" +
                    "v=sys.argv[3] if len(sys.argv)>3 else 'zh-CN-XiaoxiaoNeural'\n" +
                    "r=sys.argv[4] if len(sys.argv)>4 else '+0%'\n" +
                    "p=sys.argv[5] if len(sys.argv)>5 else '+0Hz'\n" +
                    "asyncio.run(Communicate(t,v,rate=r,pitch=p).save(sys.argv[2]))\n",
                    new System.Text.UTF8Encoding(false));
            }
            File.WriteAllText(txt, t2, new System.Text.UTF8Encoding(false));
            ProcessStartInfo pi = new ProcessStartInfo();
            pi.FileName = PyExe();
            pi.Arguments = "\"" + py + "\" \"" + txt + "\" \"" + mp3 + "\" \"" + voice + "\" \"+0%\" \"+0Hz\"";
            pi.UseShellExecute = false;
            pi.CreateNoWindow = true;
            pi.WindowStyle = ProcessWindowStyle.Hidden;
            Process p = Process.Start(pi);
            p.WaitForExit(40000);
            if (File.Exists(mp3) && new FileInfo(mp3).Length > 2048) return mp3;
        }
        catch { }
        return "";
    }

    // 首字延迟的真相：edge_tts 联网合成，冷启一句 3.3 秒，命中缓存只要 7ms。
    // 所以启动时后台把高频短句先合成好，日常应答直接走缓存，开口不用等
    public static void PrewarmTts()
    {
        System.Threading.Thread t = new System.Threading.Thread(delegate()
        {
            string[] lines = new string[] {
                "道在呢，你说吧", "我在呢", "来啦", "好嘞", "嗯嗯，我听着呢",
                "这事儿我记下了", "今天感觉怎么样", "别急，慢慢来",
                "我先看看", "一会儿就来", "还没好呢", "那我先忙着"
            };
            foreach (string s in lines)
            {
                try { TtsFile(s, "zh-CN-XiaoxiaoNeural"); } catch { }
            }
        });
        t.IsBackground = true;
        t.Start();
    }

    // 排着队一句一句往外播，绝不叠着说
    void SpeakLoop()
    {
        while (true)
        {
            SpeakJob job;
            lock (speakQLock)
            {
                if (speakQueue.Count == 0) { voiceThread = null; return; }
                job = speakQueue.Dequeue();
            }
            try { PlayOne(job); } catch { }
        }
    }

    void PlayOne(SpeakJob job)
    {
        string t2 = job.text;
        string voice = job.voice;
        string fx = job.fx;
        speaking = true;
        // 嘴的动作不再按字数提前估：等播放器真的出声那一刻再张嘴，时长用音频真实长度，
        // 声音和画面走同一条时间轴，才不会嘴先动完、声音才出来
        int zc = CountSpeakChars(t2);
        int estMs = (int)(zc * 205) + 260;
        speakMouthStart = 0;
        speakMouthUntil = 0;
        try
        {
            string dir = VoiceDir();
            bool hasFx = fx != null && fx.Length > 0 && fx != "none";
            // 语气跟着心情走：高兴话就快一点、调门抬一点；难过就放慢、压低。
            // 同样一句"我在呢"，用同一个平语气念出来像个播报器
            string rate = CurRate();
            // 短句念慢一点、长句稍快：真人说短句是随口吐出来的，长句才收着赶
            // v0.71 把短句从 -3 收到 -1：慢 3% 在十来个字的问候上听着像念稿，
            // 也把「第一个字出来」的时间往后拖；-1 保留一点松弛感但出口更快
            if (zc <= 10) rate = NudgeRate(rate, -1);
            else if (zc >= 26) rate = NudgeRate(rate, 4);
            string pitch = CurPitch(t2);
            string seed = t2 + "|" + voice + "|" + (hasFx ? fx : "") + "|" + rate + "|" + pitch;
            string key = Math.Abs(seed.GetHashCode()).ToString();
            string mp3 = Path.Combine(dir, key + (hasFx ? ".wav" : ".mp3"));
            string txt = Path.Combine(dir, key + ".txt");
                string py = Path.Combine(dir, "say.py");
                string play = Path.Combine(dir, "play.ps1");
                try
                {
                    File.WriteAllText(py,
                        "import asyncio,sys\n" +
                        "from edge_tts import Communicate\n" +
                        "t=open(sys.argv[1],'r',encoding='utf-8').read()\n" +
                        "v=sys.argv[3] if len(sys.argv)>3 else 'zh-CN-XiaoxiaoNeural'\n" +
                        "r=sys.argv[4] if len(sys.argv)>4 else '+0%'\n" +
                        "p=sys.argv[5] if len(sys.argv)>5 else '+0Hz'\n" +
                        "asyncio.run(Communicate(t,v,rate=r,pitch=p).save(sys.argv[2]))\n",
                        new System.Text.UTF8Encoding(false));
                }
                catch { }
                string playPy = Path.Combine(dir, "play_mp3.py");
                if (!File.Exists(playPy))
                {
                    // 不再用 WMPlayer 的 playState 轮询：那个循环最长要等 60 秒，
                    // 一句话播完队列卡住，后面的回话全排在后面。改成 miniaudio 解码 + sounddevice 播。
                    File.WriteAllText(playPy,
                        "# -*- coding: utf-8 -*-\n" +
                        "import sys, numpy as np, miniaudio, sounddevice as sd\n" +
                        "p = sys.argv[1]\n" +
                        "d = miniaudio.mp3_read_file_s16(p)\n" +
                        "samples, nch, fs = (d.samples, d.nchannels, d.sample_rate) if not isinstance(d, tuple) else d\n" +
                        "pcm = np.frombuffer(samples, dtype=np.int16) if isinstance(samples, (bytes, bytearray)) else np.asarray(samples, dtype=np.int16)\n" +
                        "sd.play(pcm.reshape(-1, nch), fs)\n" +
                        "sd.wait()\n",
                        new System.Text.UTF8Encoding(false));
                }
                if (!File.Exists(play) || (File.ReadAllText(play, System.Text.Encoding.Unicode).IndexOf(PyExe(), StringComparison.OrdinalIgnoreCase) < 0
                    && File.ReadAllText(play).IndexOf(PyExe(), StringComparison.OrdinalIgnoreCase) < 0))
                {
                    // play.ps1 里不能再写裸 "python"（PATH 里没有它），否则播放在静默中失败
                    File.WriteAllText(play,
                        "param([string]$f)\r\n" +
                        "& \"" + PyExe() + "\" \"$PSScriptRoot\\play_mp3.py\" $f\r\n",
                        new System.Text.UTF8Encoding(true));
                }

                if (!(File.Exists(mp3) && new FileInfo(mp3).Length > 2048))
                {
                    File.WriteAllText(txt, t2, new System.Text.UTF8Encoding(false));
                    ProcessStartInfo pi = new ProcessStartInfo();
                    pi.FileName = PyExe();
                    if (hasFx)
                    {
                        string vfx = Path.Combine(AppDir(), "voicefx.py");
                        pi.Arguments = "-X utf8 \"" + vfx + "\" --text \"" + txt + "\" --out \"" + mp3
                            + "\" --voice \"" + voice + "\" --fx \"" + fx + "\"";
                    }
                    else
                    {
                        pi.Arguments = "\"" + py + "\" \"" + txt + "\" \"" + mp3 + "\" \"" + voice
                            + "\" \"" + rate + "\" \"" + pitch + "\"";
                    }
                    pi.UseShellExecute = false;
                    pi.CreateNoWindow = true;
                    pi.WindowStyle = ProcessWindowStyle.Hidden;
                    Process p = Process.Start(pi);
                    p.WaitForExit(40000);
                }

                if (File.Exists(mp3) && new FileInfo(mp3).Length > 2048)
                {
                    // 出声之前先把音量顶回来。别的程序动不动就把扬声器压到三成以下，
                    // 只靠定时器兜不住，每句开播前补一次最稳
                    EnsureSpeakerLevel();
                    // WMPlayer 这台机器上不出声，改用 python + sounddevice 直接播
                    string player = Path.Combine(AppDir(), "play_audio.py");
                    ProcessStartInfo pp = new ProcessStartInfo();
                    pp.FileName = "python";
                    pp.Arguments = "-X utf8 \"" + player + "\" \"" + mp3 + "\"";
                    pp.UseShellExecute = false;
                    pp.CreateNoWindow = true;
                    pp.WindowStyle = ProcessWindowStyle.Hidden;
                    pp.RedirectStandardOutput = true;
                    pp.StandardOutputEncoding = System.Text.Encoding.UTF8;
                    Process pk = Process.Start(pp);
                    curPlayer = pk;
                    // 读播放器吐回来的时间轴：DEC 是音频真实毫秒数，START 是真正出声那一刻。
                    // 嘴从 START 开始、按真实时长收，声音和画面才对得上
                    int durMs = -1;
                    try
                    {
                        string ln;
                        while ((ln = pk.StandardOutput.ReadLine()) != null)
                        {
                            if (ln.StartsWith("DEC|"))
                            {
                                int.TryParse(ln.Substring(4), out durMs);
                            }
                            else if (ln.StartsWith("START"))
                            {
                                speakMouthStart = Environment.TickCount;
                                speakMouthUntil = speakMouthStart + (durMs > 0 ? durMs : estMs) + 120;
                            }
                        }
                    }
                    catch { }
                    if (speakMouthStart == 0)
                    {
                        speakMouthStart = Environment.TickCount;
                        speakMouthUntil = speakMouthStart + estMs;
                    }
                    // 必须等这句真播完再撒手，不然下一句接上来就是叠着说话
                    pk.WaitForExit(60000);
                    curPlayer = null;
                }
            }
            catch { }
            finally { speaking = false; }
    }

    // 立刻闭嘴：点它、或者要开始听你说话时都得先掐掉。
    // 不掐的话，麦克风会把它自己的声音录进去，你说什么它都听不清
    void StopSpeechNow()
    {
        try { if (curPlayer != null && !curPlayer.HasExited) curPlayer.Kill(); } catch { }
        lock (speakQLock)
        {
            try { speakQueue.Clear(); } catch { }
        }
    }

    // 数字数：标点和空格不算，念出来才占时间
    int CountSpeakChars(string s)
    {
        int n = 0;
        for (int i = 0; i < s.Length; i++)
        {
            char c = s[i];
            if (c == ' ' || c == '\t' || c == '\r' || c == '\n') continue;
            if (c == ',' || c == '.' || c == '!' || c == '?' || c == ';' || c == ':') continue;
            if (c == '，' || c == '。' || c == '！' || c == '？' || c == '；' || c == '：' || c == '、' || c == '…') continue;
            n++;
        }
        return n < 2 ? 2 : n;
    }

    // ============ 喊名字就醒（实时语音） ============
    // 常驻听：每轮录一句（voice.py 的 VAD 会自动在你说完时停），只判断这句里有没有在叫"道"。
    // 认出来就先应一声、招手，再自动接着听你下一句，等于"喊一声开门"。
    void MenuWake(object s, EventArgs e)
    {
        wakeOn = !wakeOn;
        try
        {
            RegistryKey k = Registry.CurrentUser.CreateSubKey("Software\\DaoPet");
            if (k != null) { k.SetValue("WakeOn", wakeOn ? 1 : 0); k.Close(); }
        }
        catch { }
        if (wakeOn)
        {
            Say("好，你喊「道」，我就应一声。");
            StartWakeLoop();
        }
        else
        {
            Say("行，那我先不听名字了。");
        }
    }

    void StartWakeLoop()
    {
        if (wakeThread != null && wakeThread.IsAlive) return;
        wakeThread = new System.Threading.Thread(delegate() { WakeLoop(); });
        wakeThread.IsBackground = true;
        wakeThread.Start();
    }

    Process wakeProc = null;
    System.IO.StreamWriter wakeIn = null;
    readonly System.Collections.Generic.Queue<string> wakeLines = new System.Collections.Generic.Queue<string>();
    readonly object wakeLock = new object();
    bool wakePaused = false;

    void WakeLoop()
    {
        while (wakeOn)
        {
            try
            {
                // 自己在说话、正在录音、或者在跑对话/大脑时别抢麦克风：
                // 不再杀进程，只发一个 p 让它别听，说完再发 r（省的反复启停 python）
                bool busy = speaking || hearBusy
                    || (voiceChatThread != null && voiceChatThread.IsAlive)
                    || (brainThread != null && brainThread.IsAlive)
                    || (hearThread != null && hearThread.IsAlive);
                if (busy)
                {
                    PumpWake(false);
                    System.Threading.Thread.Sleep(500);
                    continue;
                }
                PumpWake(true);
                // 应声之后留两秒，别再把自己的尾音当唤声
                if (Environment.TickCount - (int)(wakeHitAt & 0x7fffffff) < 2000) { System.Threading.Thread.Sleep(500); continue; }

                if (wakeProc == null || wakeProc.HasExited) StartWakeProc();
                if (wakeProc == null) { System.Threading.Thread.Sleep(2000); continue; }

                string line = null;
                lock (wakeLock)
                {
                    if (wakeLines.Count > 0) line = wakeLines.Dequeue();
                }
                if (line == null) { System.Threading.Thread.Sleep(120); continue; }

                string heard = JsonStr(line, "text");
                // 能量门限（学 microWakeWord 的 energy gate）：屋里安静时不认，
                // 免得空调声、键盘声被认成一句话再往唤醒逻辑里送
                double rms = JsonNum(line, "rms");
                if (rms > 0 && rms < 120) continue;
                if (IsWakeCall(heard)) HitWake();
            }
            catch { System.Threading.Thread.Sleep(1000); }
        }
        StopWakeProc();
    }

    void StartWakeProc()
    {
        try
        {
            string py = Path.Combine(Path.GetDirectoryName(Application.ExecutablePath), "voice.py");
            if (!System.IO.File.Exists(py)) return;
            StopWakeProc();
            ProcessStartInfo pi = new ProcessStartInfo();
            pi.FileName = PyExe();
            pi.Arguments = "\"" + py + "\" wake";
            pi.UseShellExecute = false;
            pi.CreateNoWindow = true;
            pi.RedirectStandardInput = true;
            pi.RedirectStandardOutput = true;
            pi.RedirectStandardError = true;
            pi.StandardOutputEncoding = System.Text.Encoding.UTF8;
            pi.StandardErrorEncoding = System.Text.Encoding.UTF8;
            pi.WindowStyle = ProcessWindowStyle.Hidden;
            wakeProc = Process.Start(pi);
            wakeIn = wakeProc.StandardInput;
            wakePaused = false;
            System.Threading.Thread rd = new System.Threading.Thread(delegate()
            {
                try
                {
                    Process p = wakeProc;
                    string s;
                    while ((s = p.StandardOutput.ReadLine()) != null)
                    {
                        lock (wakeLock)
                        {
                            if (wakeLines.Count > 40) wakeLines.Dequeue();
                            wakeLines.Enqueue(s);
                        }
                    }
                }
                catch { }
            });
            rd.IsBackground = true;
            rd.Start();
        }
        catch { wakeProc = null; }
    }

    // pause=true 表示"先别听"，false 表示"接着听"
    void PumpWake(bool listen)
    {
        try
        {
            if (wakeProc == null || wakeProc.HasExited || wakeIn == null) return;
            if (listen == wakePaused)
            {
                wakeIn.WriteLine(listen ? "r" : "p");
                wakeIn.Flush();
                wakePaused = !listen;
            }
        }
        catch { }
    }

    void StopWakeProc()
    {
        try
        {
            if (wakeProc != null && !wakeProc.HasExited)
            {
                try { wakeIn.WriteLine("q"); wakeIn.Flush(); } catch { }
                if (!wakeProc.WaitForExit(1500)) wakeProc.Kill();
            }
        }
        catch { }
        wakeProc = null; wakeIn = null; wakePaused = false;
    }

    // 分清"喊人"和"话里带道"：知道、道理、味道、难道、这道题…都不是在叫我。
    // 所以不放宽成"句子里有 道 就算"，只认"道"出现在开头（或紧跟喂/哎/嘿）这几种喊人说法。
    bool IsWakeCall(string t)
    {
        if (t == null) return false;
        string s = t.Replace(" ", "");
        char[] drop = { '，', '。', '？', '！', '、', '…', ',', '.', '?', '!' };
        foreach (char ch in drop) s = s.Replace(ch.ToString(), "");
        if (s.Length == 0) return false;
        if (s.Length > 10) return false;
        string[] notCall = { "知道", "道理", "味道", "难道", "街道", "一道", "通道", "频道", "报道", "道教", "霸道", "轨道", "道德", "大道", "这道", "那道", "说道", "一道题" };
        for (int i = 0; i < notCall.Length; i++) if (s.Contains(notCall[i])) return false;
        if (lastSaidText.Length > 3 && s.Contains(lastSaidText.Substring(0, 4))) return false;

        string low = s.ToLower();
        if (s == "道" || s == "道道" || s == "小道" || low == "dao" || low == "heydao") return true;
        if (s.StartsWith("道") && s.Length <= 6) return true;
        string[] heads = { "喂道", "哎道", "嘿道", "嗨道", "老道", "叫你道", "喊你道", "在不在道" };
        for (int i = 0; i < heads.Length; i++) if (s.StartsWith(heads[i])) return true;
        return false;
    }

    // 给自检口用：外部把一句话塞进来，判断"是不是在叫名字"
    public static bool WakeChk(string t)
    {
        try { return DesktopPet.Self.WakeTest(t); } catch { return false; }
    }

    // 给自检口用：喂一句"听到的话"，命中就走完整的应声流程
    public static bool WakeFeed(string t)
    {
        try
        {
            if (!DesktopPet.Self.IsWakeCall(t)) return false;
            DesktopPet.Self.HitWake();
            return true;
        }
        catch { return false; }
    }

    bool WakeTest(string t)
    {
        return IsWakeCall(t);
    }

    // 给自检口用：常见问题本地秒答
    public static string FastChk(string q)
    {
        try { return DesktopPet.Self.FastAnswer(q); } catch { return null; }
    }

    void HitWake()
    {
        wakeHitAt = Environment.TickCount;
        string[] ack = { "道在呢，你说吧。", "我在。", "来啦，什么事？", "哎，我听着呢。", "嗯，叫我干嘛？" };
        string line = ack[new Random().Next(ack.Length)];
        try
        {
            BeginInvoke(new MethodInvoker(delegate()
            {
                StopSpeechNow();
                waveTicks = 55;                 // 招手
                lying = false;
                SayAs(line, CurVoice());
                Invalidate();
            }));
        }
        catch { }
        // 应声说完，接着听下一句：等它念完再开麦，不然录到的是它自己的声音
        System.Threading.Thread.Sleep(200);
        int waitMs = 1200;
        while (speaking && waitMs < 20000) { System.Threading.Thread.Sleep(200); waitMs += 200; }
        try
        {
            BeginInvoke(new MethodInvoker(delegate()
            {
                if (hearThread == null || !hearThread.IsAlive) MenuHear(null, EventArgs.Empty);
            }));
        }
        catch { }
    }

    void MenuHear(object s, EventArgs e)
    {
        if (hearThread != null && hearThread.IsAlive) return;
        Say("我在听，说完自己停。");
        hearThread = new System.Threading.Thread(delegate()
        {
            string heard = "";
            hearBusy = true;
            StopSpeechNow();
            try
            {
                string py = Path.Combine(Path.GetDirectoryName(Application.ExecutablePath), "hear.py");
                if (!System.IO.File.Exists(py))
                {
                    BeginInvoke(new MethodInvoker(delegate() { Say("听觉模块没装上，等我更新一下自己。"); }));
                    return;
                }
                string wav = Path.Combine(VoiceDir(), "heard.wav");
                ProcessStartInfo pi = new ProcessStartInfo();
                pi.FileName = PyExe();
                pi.Arguments = "\"" + py + "\" 8 \"" + wav + "\"";
                pi.UseShellExecute = false;
                pi.CreateNoWindow = true;
                pi.RedirectStandardOutput = true;
                pi.RedirectStandardError = true;
                pi.StandardOutputEncoding = System.Text.Encoding.UTF8;
                pi.StandardErrorEncoding = System.Text.Encoding.UTF8;
                pi.WindowStyle = ProcessWindowStyle.Hidden;
                Process p = Process.Start(pi);
                string so = p.StandardOutput.ReadToEnd();
                string se = p.StandardError.ReadToEnd();
                p.WaitForExit(45000);
                if (so != null) heard = so.Trim();
            }
            catch { }
            hearBusy = false;
            string h = heard;
            try { BeginInvoke(new MethodInvoker(delegate() { RunVoiceCommand(h); })); } catch { }
        });
        hearThread.IsBackground = true;
        hearThread.Start();
    }

    System.Threading.Thread voiceChatThread;
    System.Threading.Thread brainThread;

    void MenuVoiceChat(object s, EventArgs e)
    {
        if (voiceChatThread != null && voiceChatThread.IsAlive)
        {
            Say("我还在听上一句，等我说完。");
            return;
        }
        if (!voiceOn) voiceOn = true;
        Say("我在听，说完自己停。");
        voiceChatThread = new System.Threading.Thread(delegate()
        {
            string json = "";
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
                pi.Arguments = "\"" + py + "\" chat";
                pi.UseShellExecute = false;
                pi.CreateNoWindow = true;
                pi.RedirectStandardOutput = true;
                pi.RedirectStandardError = true;
                pi.StandardOutputEncoding = System.Text.Encoding.UTF8;
                pi.StandardErrorEncoding = System.Text.Encoding.UTF8;
                pi.WindowStyle = ProcessWindowStyle.Hidden;
                Process p = Process.Start(pi);
                string so = p.StandardOutput.ReadToEnd();
                p.StandardError.ReadToEnd();
                p.WaitForExit(80000);
                if (so != null) json = so.Trim();
            }
            catch { }

            string heard = JsonStr(json, "heard");
            string reply = JsonStr(json, "reply");
            int mood = JsonInt(json, "mood");
            string hh = heard;
            string rr = reply;
            try
            {
                BeginInvoke(new MethodInvoker(delegate()
                {
                    if (rr == null || rr.Length == 0)
                    {
                        Say("刚才没听清，再说一遍？");
                        return;
                    }
                    if (hh != null && hh.Length > 0) RecordTalk(hh);
                    if (mood > 0 && mood <= 8) { moodKind = mood; moodTicks = 70; }
                    SayAs(rr, CurVoice());
                }));
            }
            catch { }
        });
        voiceChatThread.IsBackground = true;
        voiceChatThread.Start();
    }

    // 问它 / 讲题 / 总结：同一套大脑，只是换种用法
    void MenuAskBrain(object s, EventArgs e)
    {
        RunBrain("ask", "跟道说一句", "想问什么就写在这儿，它会念给你听。");
    }

    void MenuExplain(object s, EventArgs e)
    {
        RunBrain("explain", "讲讲这道题", "把题目抄下来或贴进来，它给你讲该往哪想。");
    }

    void MenuSum(object s, EventArgs e)
    {
        RunBrain("sum", "总结一下", "把要总结的内容贴进来，它用大白话说重点。");
    }

    void RunBrain(string mode, string title, string tip)
    {
        if (brainThread != null && brainThread.IsAlive)
        {
            Say("我还在想上一句，等我说完。");
            return;
        }
        string q = AskText(title, tip);
        if (q == null) return;
        q = q.Trim();
        if (q.Length == 0) return;
        // 2026-11-22：常见问题本地秒答，不再排一趟网络大脑（问时间/日期/它是谁这类）
        if (mode == "ask")
        {
            string fast = FastAnswer(q);
            if (fast != null)
            {
                if (!voiceOn) voiceOn = true;
                moodKind = 4; moodTicks = 40;
                SayAs(fast, CurVoice());
                return;
            }
        }
        if (!voiceOn) voiceOn = true;
        Say("我想想。");
        brainThread = new System.Threading.Thread(delegate()
        {
            string json = "";
            try
            {
                string exeDir = Path.GetDirectoryName(Application.ExecutablePath);
                string py = Path.Combine(exeDir, "voice.py");
                if (!System.IO.File.Exists(py))
                {
                    BeginInvoke(new MethodInvoker(delegate() { Say("大脑模块没装上，等我更新一下自己。"); }));
                    return;
                }
                // 中文不经过命令行，写文件给它读，免得编码乱掉
                string askPath = Path.Combine(exeDir, "ask.txt");
                File.WriteAllText(askPath, q, new System.Text.UTF8Encoding(false));
                ProcessStartInfo pi = new ProcessStartInfo();
                pi.FileName = PyExe();
                pi.Arguments = "\"" + py + "\" " + mode + " --file \"" + askPath + "\"";
                pi.UseShellExecute = false;
                pi.CreateNoWindow = true;
                pi.RedirectStandardOutput = true;
                pi.RedirectStandardError = true;
                pi.StandardOutputEncoding = System.Text.Encoding.UTF8;
                pi.StandardErrorEncoding = System.Text.Encoding.UTF8;
                pi.WindowStyle = ProcessWindowStyle.Hidden;
                Process p = Process.Start(pi);
                string so = p.StandardOutput.ReadToEnd();
                p.StandardError.ReadToEnd();
                p.WaitForExit(80000);
                if (so != null) json = so.Trim();
            }
            catch { }

            string reply = JsonStr(json, "reply");
            int mood = JsonInt(json, "mood");
            try
            {
                BeginInvoke(new MethodInvoker(delegate()
                {
                    if (mood > 0 && mood <= 8) { moodKind = mood; moodTicks = 70; }
                    if (reply != null && reply.Length > 0) SayAs(reply, CurVoice());
                    else Say("我这一下没想出来，再问我一遍。");
                    Invalidate();
                }));
            }
            catch { }
        });
        brainThread.IsBackground = true;
        brainThread.Start();
    }

    // 常见问题本地秒答：不进网络、不等模型，问完立刻出声（0.1 秒级）
    string FastAnswer(string q)
    {
        string s = q.Trim();
        if (s.Length > 30) return null;
        DateTime now = DateTime.Now;
        string[] wd = { "星期天", "星期一", "星期二", "星期三", "星期四", "星期五", "星期六" };
        if (s.Contains("几点") || s.Contains("现在时间") || s.Contains("什么时间了"))
        {
            string mm = now.Minute < 10 ? "零" + now.Minute : now.Minute.ToString();
            return "现在 " + now.Hour + " 点" + mm + " 分。";
        }
        if (s.Contains("几号") || s.Contains("星期几") || s.Contains("周几") || s.Contains("今天星期") || s.Contains("什么日子"))
        {
            return "今天 " + now.Month + " 月 " + now.Day + " 日，" + wd[(int)now.DayOfWeek] + "。";
        }
        if (s.Contains("你是谁") || s.Contains("你叫什么") || s.Contains("你的名字"))
        {
            return "我是道，就在你桌面上待着，喊我名字我就应。";
        }
        if (s.Contains("你在干嘛") || s.Contains("你在干什么") || s.Contains("在做什么"))
        {
            return "在这儿站着呢，等你叫我。";
        }
        if (s.Contains("累不累") || s.Contains("你累") || s.Contains("困不困"))
        {
            return "不累，我不用睡觉。";
        }
        if (s.Contains("几点睡") || s.Contains("该睡"))
        {
            int h = now.Hour;
            if (h >= 23 || h < 5) return "这会儿该睡了，明天还得早起。";
            return "还早，先把手里的事收个尾。";
        }
        return null;
    }

    // 读 JSON 里的数字字段（用于 rms 这种判断，不必引 JSON 库）
    double JsonNum(string json, string key)
    {
        if (json == null || json.Length == 0) return 0;
        string pat = "\"" + key + "\":";
        int i = json.IndexOf(pat);
        if (i < 0) return 0;
        i += pat.Length;
        while (i < json.Length && (json[i] == ' ' || json[i] == '\t')) i++;
        int st = i;
        while (i < json.Length && (char.IsDigit(json[i]) || json[i] == '-' || json[i] == '.')) i++;
        double v = 0;
        try { v = double.Parse(json.Substring(st, i - st), System.Globalization.CultureInfo.InvariantCulture); } catch { }
        return v;
    }

    string JsonStr(string json, string key)
    {
        if (json == null || json.Length == 0) return "";
        // python 输出的是 "key": "值"，冒号后面带空格，不能按死格式找
        string pat = "\"" + key + "\":";
        int i = json.IndexOf(pat);
        if (i < 0) return "";
        i += pat.Length;
        while (i < json.Length && (json[i] == ' ' || json[i] == '\t')) i++;
        if (i >= json.Length || json[i] != '"') return "";
        i++;
        StringBuilder sb = new StringBuilder();
        while (i < json.Length)
        {
            char c = json[i];
            if (c == '\\' && i + 1 < json.Length)
            {
                char n = json[i + 1];
                if (n == 'n') sb.Append('\n');
                else if (n == 't') sb.Append('\t');
                else if (n == 'r') sb.Append('\r');
                else if (n == 'u' && i + 5 < json.Length)
                {
                    int code = 0;
                    try { code = Convert.ToInt32(json.Substring(i + 2, 4), 16); } catch { }
                    sb.Append((char)code);
                    i += 6;
                    continue;
                }
                else sb.Append(n);
                i += 2;
                continue;
            }
            if (c == '"') break;
            sb.Append(c);
            i++;
        }
        return sb.ToString();
    }

    int JsonInt(string json, string key)
    {
        if (json == null || json.Length == 0) return 0;
        string pat = "\"" + key + "\":";
        int i = json.IndexOf(pat);
        if (i < 0) return 0;
        i += pat.Length;
        while (i < json.Length && (json[i] == ' ' || json[i] == '\t')) i++;
        StringBuilder sb = new StringBuilder();
        while (i < json.Length && json[i] >= '0' && json[i] <= '9') { sb.Append(json[i]); i++; }
        try { return int.Parse(sb.ToString()); }
        catch { return 0; }
    }

    // 对话框不再钉在屏幕正中（正中正好压着道那张脸）：贴着自己的窗口摆，
    // 下面放不下就翻到头顶上方，左右再按屏幕边界夹一下
    void PlaceNearMe(Form f)
    {
        Rectangle wa = Screen.FromControl(this).WorkingArea;
        Rectangle me = this.Bounds;
        int x = me.Left + (me.Width - f.Width) / 2;
        int y = me.Bottom + 8;
        if (y + f.Height > wa.Bottom - 8) y = me.Top - f.Height - 8;
        if (y < wa.Top + 8) y = wa.Top + 8;
        if (x + f.Width > wa.Right - 8) x = wa.Right - 8 - f.Width;
        if (x < wa.Left + 8) x = wa.Left + 8;
        f.StartPosition = FormStartPosition.Manual;
        f.Location = new Point(x, y);
    }

    string AskText(string title, string tip)
    {
        Form f = new Form();
        f.Text = title;
        f.Width = 460;
        f.Height = 190;
        PlaceNearMe(f);
        f.FormBorderStyle = FormBorderStyle.FixedDialog;
        f.MaximizeBox = false;
        f.MinimizeBox = false;
        f.TopMost = true;
        Label lb = new Label();
        lb.Text = tip;
        lb.Left = 16;
        lb.Top = 14;
        lb.Width = 420;
        lb.Height = 26;
        TextBox tb = new TextBox();
        tb.Left = 16;
        tb.Top = 44;
        tb.Width = 415;
        tb.Height = 26;
        Button ok = new Button();
        ok.Text = (title != null && title.IndexOf("翻译") >= 0) ? "翻译" : "好";
        ok.Left = 246;
        ok.Top = 90;
        ok.Width = 90;
        ok.Height = 30;
        ok.DialogResult = DialogResult.OK;
        Button cancel = new Button();
        cancel.Text = "算了";
        cancel.Left = 342;
        cancel.Top = 90;
        cancel.Width = 90;
        cancel.Height = 30;
        cancel.DialogResult = DialogResult.Cancel;
        f.Controls.Add(lb);
        f.Controls.Add(tb);
        f.Controls.Add(ok);
        f.Controls.Add(cancel);
        f.AcceptButton = ok;
        f.CancelButton = cancel;
        tb.Focus();
        if (f.ShowDialog() == DialogResult.OK) return tb.Text;
        return null;
    }

    void SayAs(string text, string voice)
    {
        bubble = text;
        bubbleFrames = 60 + (text == null ? 0 : text.Length * 3);
        if (bubbleFrames > 140) bubbleFrames = 140;   // 说完就散，不在屏幕上赖着
        Invalidate();
        if (voiceOn) SpeakOut(text, voice, CurFx());
    }

    void MenuTranslate(object s, EventArgs e)
    {
        if (transThread != null && transThread.IsAlive) return;
        string input = AskText("翻译一句", "中英文都行，比如 hello 或 今天天气很好");
        if (input == null) return;
        input = input.Trim();
        if (input.Length == 0) return;

        bool hasCn = false;
        for (int i = 0; i < input.Length; i++)
        {
            if (input[i] >= '\u4e00' && input[i] <= '\u9fff') { hasCn = true; break; }
        }
        string outVoice = hasCn ? "en-US-AriaNeural" : CurVoice();
        string q = input;

        transThread = new System.Threading.Thread(delegate()
        {
            string res = "";
            try
            {
                string py = Path.Combine(AppDir(), "trans.py");
                if (!File.Exists(py))
                {
                    BeginInvoke(new MethodInvoker(delegate() { Say("翻译模块没装上，等我更新一下自己。"); }));
                    return;
                }
                ProcessStartInfo pi = new ProcessStartInfo();
                pi.FileName = PyExe();
                pi.Arguments = "\"" + py + "\" \"" + q.Replace("\"", " ") + "\"";
                pi.UseShellExecute = false;
                pi.CreateNoWindow = true;
                pi.RedirectStandardOutput = true;
                pi.RedirectStandardError = true;
                pi.StandardOutputEncoding = System.Text.Encoding.UTF8;
                pi.StandardErrorEncoding = System.Text.Encoding.UTF8;
                pi.WindowStyle = ProcessWindowStyle.Hidden;
                Process p = Process.Start(pi);
                string so = p.StandardOutput.ReadToEnd();
                string se = p.StandardError.ReadToEnd();
                p.WaitForExit(40000);
                if (so != null) res = so.Trim();
            }
            catch { }

            string outText = res;
            string voice = outVoice;
            try
            {
                BeginInvoke(new MethodInvoker(delegate()
                {
                    if (outText.Length == 0) Say("这个词我查不到，换个说法试试。");
                    else SayAs(outText, voice);
                }));
            }
            catch { }
        });
        transThread.IsBackground = true;
        transThread.Start();
    }

    string HearOnce(int secs, string scriptName)
    {
        string heard = "";
        try
        {
            hearBusy = true;
            StopSpeechNow();
            string py = Path.Combine(AppDir(), scriptName);
            if (!File.Exists(py)) return "";
            string wav = Path.Combine(VoiceDir(), "heard.wav");
            ProcessStartInfo pi = new ProcessStartInfo();
            pi.FileName = PyExe();
            pi.Arguments = "\"" + py + "\" " + secs + " \"" + wav + "\"";
            pi.UseShellExecute = false;
            pi.CreateNoWindow = true;
            pi.RedirectStandardOutput = true;
            pi.RedirectStandardError = true;
            pi.StandardOutputEncoding = System.Text.Encoding.UTF8;
            pi.StandardErrorEncoding = System.Text.Encoding.UTF8;
            pi.WindowStyle = ProcessWindowStyle.Hidden;
            Process p = Process.Start(pi);
            string so = p.StandardOutput.ReadToEnd();
            string se = p.StandardError.ReadToEnd();
            p.WaitForExit(60000);
            if (so != null) heard = so.Trim();
        }
        catch { }
        finally { hearBusy = false; }
        return heard;
    }

    string RunTrans(string text)
    {
        string res = "";
        try
        {
            string py = Path.Combine(AppDir(), "trans.py");
            if (!File.Exists(py)) return "";
            ProcessStartInfo pi = new ProcessStartInfo();
            pi.FileName = PyExe();
            pi.Arguments = "\"" + py + "\" \"" + text.Replace("\"", " ") + "\"";
            pi.UseShellExecute = false;
            pi.CreateNoWindow = true;
            pi.RedirectStandardOutput = true;
            pi.RedirectStandardError = true;
            pi.StandardOutputEncoding = System.Text.Encoding.UTF8;
            pi.StandardErrorEncoding = System.Text.Encoding.UTF8;
            pi.WindowStyle = ProcessWindowStyle.Hidden;
            Process p = Process.Start(pi);
            string so = p.StandardOutput.ReadToEnd();
            string se = p.StandardError.ReadToEnd();
            p.WaitForExit(40000);
            if (so != null) res = so.Trim();
        }
        catch { }
        return res;
    }

    void ShowSay(string shown, string speech, string voice)
    {
        bubble = shown;
        bubbleFrames = 150;
        Invalidate();
        if (voiceOn) SpeakOut(speech, voice);
    }

    void MenuSimCn2En(object s, EventArgs e) { SimTranslate(true); }
    void MenuSimEn2Cn(object s, EventArgs e) { SimTranslate(false); }

    void SimTranslate(bool cn2en)
    {
        if (hearThread != null && hearThread.IsAlive) return;
        Say(cn2en ? "说一句中文，我给你翻成英文。" : "说一句英文，我给你翻成中文。");
        bool dir = cn2en;
        hearThread = new System.Threading.Thread(delegate()
        {
            string heard = HearOnce(8, dir ? "hear.py" : "hear_en.py");
            string h = heard.Trim();
            if (h.Length == 0)
            {
                try { BeginInvoke(new MethodInvoker(delegate() { Say("没听清，再说一次？"); })); }
                catch { }
                return;
            }
            string res = RunTrans(h);
            string display = h + "  →  " + res;
            string speech = res.Length > 0 ? res : h;
            string voice = dir ? "en-US-AriaNeural" : CurVoice();
            try
            {
                BeginInvoke(new MethodInvoker(delegate()
                {
                    if (res.Length == 0) Say("这句我翻不出来，换个说法。");
                    else ShowSay(display, speech, voice);
                }));
            }
            catch { }
        });
        hearThread.IsBackground = true;
        hearThread.Start();
    }

    void RunVoiceCommand(string text)
    {
        if (text == null || text.Trim().Length == 0) { Say("我没听清，再说一次？"); return; }
        string t = text.Replace(" ", "").Replace("，", "").Replace("。", "").Replace("？", "").Replace("?", "");
        if (t.Contains("翻译") || t.Contains("英文") || t.Contains("英语") || t.Contains("怎么说"))
            Say("这个我用「翻译一句」给你办：右键点我，选「翻译一句」，把要翻的话填进去，我念给你听。");
        else if (t.Contains("状态") || t.Contains("内存") || t.Contains("电脑") || t.Contains("跑得"))
            MenuStatus(null, null);
        else if (t.Contains("回收站") || t.Contains("垃圾") || t.Contains("删掉"))
            MenuRecycle(null, null);
        else if (t.Contains("壁纸") || t.Contains("换图") || t.Contains("桌面背景"))
            MenuWallpaper(null, null);
        else if (t.Contains("简报") || t.Contains("报告"))
            MenuBrief(null, null);
        else if (t.Contains("更新") || t.Contains("新版本"))
            CheckUpdate(true);
        else if (t.Contains("备份") || t.Contains("保存自己"))
            MenuBackup(null, null);
        else if (t.Contains("换模样") || t.Contains("换个样子") || t.Contains("换个形象") || t.Contains("变个样"))
            MenuChange(null, null);
        else if (t.Contains("学") || t.Contains("知识") || t.Contains("今天教"))
            MenuKnowledge(null, null);
        else if (t.Contains("几点") || t.Contains("时间") || t.Contains("现在"))
            Say("现在 " + DateTime.Now.ToString("HH点mm分") + "，星期" + CurWeek() + "。");
        else if (t.Contains("天气"))
            Say("我看不了天气，这台机器上天气接口不通。你打开浏览器搜一下更快，或者看看外面的天。");
        else if (t.Contains("你叫什么") || t.Contains("你是谁") || t.Contains("你叫什么名"))
            Say("我叫道，住在这台电脑上。今天我是「" + CurName() + "」的样子。");
        else if (t.Contains("笑话") || t.Contains("逗我"))
            Say(JokeOnce());
        else if (t.Contains("谢谢") || t.Contains("谢了"))
            Say("不客气。还有事随时喊我。");
        else if (t.Contains("你好") || t.Contains("在吗") || t.Contains("喂"))
            Say("我在。今天我是「" + CurName() + "」，有事说一声。");
        else if (t.Contains("再见") || t.Contains("拜拜") || t.Contains("我走了"))
            Say("好，我在这儿待着，有事再喊我。");
        else if (t.Contains("记住") || t.Contains("记下"))
            Say("好，记住了：" + text);
        else
            Say("我听到的是「" + text + "」。这句我还接不上，你可以这样跟我说：看看电脑、换张壁纸、翻译、讲个笑话、我今天学了什么。");
    }

    string CurWeek()
    {
        string[] w = { "日", "一", "二", "三", "四", "五", "六" };
        return w[(int)DateTime.Now.DayOfWeek];
    }

    string JokeOnce()
    {
        string[] js = {
            "数学老师问：为什么你的作业是空白的？学生说：因为我用了「零」假设。",
            "有人问我为什么总在动，我说：静止的那个版本你嫌它像贴纸。",
            "我算了一下我一天眨眼的次数，结果发现我根本不用眨眼，因为我只是张图片在假装。",
            "朋友说电脑卡，我说：你先看看是谁占了内存。他一看，开着一堆浏览器标签。",
            "老师：这道题很简单。学生：那您做一下。老师：我出题，你做题，分工明确。"
        };
        return js[rnd.Next(js.Length)];
    }

    void MenuStatus(object s, EventArgs e)
    {
        string info = "";
        MEMORYSTATUSEX ms = new MEMORYSTATUSEX();
        if (GlobalMemoryStatusEx(ms))
        {
            ulong total = ms.ullTotalPhys / 1024 / 1024;
            ulong avail = ms.ullAvailPhys / 1024 / 1024;
            info += "内存：" + avail + " MB 可用 / 共 " + total + " MB（已用 " + ms.dwMemoryLoad + "%）\r\n";
        }
        try
        {
            DriveInfo c = new DriveInfo("C");
            info += "C 盘：" + (c.AvailableFreeSpace / 1073741824) + " GB 可用 / 共 " + (c.TotalSize / 1073741824) + " GB\r\n";
        }
        catch { }
        info += "\r\n今天是：" + CurName() + "（每天自动换一种）";
        MessageBox.Show(info, "道", MessageBoxButtons.OK, MessageBoxIcon.Information);
    }

    void MenuRecycle(object s, EventArgs e)
    {
        try { Process.Start("explorer.exe", "shell:RecycleBinFolder"); } catch { }
        Say("回收站打开了，看看有没有要捡回来的。");
    }

    void MenuSelfUpdate(object s, EventArgs e)
    {
        CheckUpdate(true);
    }

    // ===== 自我更新 =====
    // 约定：把新版本放到「程序目录\updates\道.exe」，道下次启动或点菜单时自己换上
    string UpdateDir() { return Path.Combine(AppDir(), "updates"); }

    bool HasNewerExe(out string newExe)
    {
        newExe = Path.Combine(UpdateDir(), "道.exe");
        try
        {
            if (!File.Exists(newExe)) return false;
            FileInfo ni = new FileInfo(newExe);
            FileInfo cu = new FileInfo(Application.ExecutablePath);
            if (ni.Length < 200000) return false;       // 明显不完整，不换
            return ni.LastWriteTime > cu.LastWriteTime;
        }
        catch { return false; }
    }

    // 公网更新源：版本号和新包地址就写在下载页里，谁都能查。
    // 这样换个网、不在同一个 WiFi、甚至隔城，也能自己换上新的自己。
    const string PUB_PAGE = "https://4mf81m04wehh3.doubao.link/app/app_17hnj8acgs2";
    // 轻量版本清单：只有几十 KB，专门给检查更新用。
    // 以前是直接读整个下载页，那个页面里装着安装包，有 11 MB，只为了看一个版本号太亏。
    const string PUB_VER_PAGE = "https://4mf81m04wehh3.doubao.link/app/app_17hpue26uuw";

    static string NetText(string url, int ms)
    {
        EnsureTls();
        try
        {
            HttpWebRequest req = (HttpWebRequest)WebRequest.Create(url);
            req.Method = "GET";
            req.Timeout = ms;
            req.ReadWriteTimeout = ms;
            req.UserAgent = "DaoUpdate/1";
            using (HttpWebResponse resp = (HttpWebResponse)req.GetResponse())
            using (Stream s = resp.GetResponseStream())
            using (StreamReader r = new StreamReader(s, Encoding.UTF8))
                return r.ReadToEnd();
        }
        catch { return null; }
    }

    static bool NetFile(string url, string dst, int ms)
    {
        EnsureTls();
        try
        {
            HttpWebRequest req = (HttpWebRequest)WebRequest.Create(url);
            req.Method = "GET";
            req.Timeout = ms;
            req.ReadWriteTimeout = ms;
            req.UserAgent = "DaoUpdate/1";
            using (HttpWebResponse resp = (HttpWebResponse)req.GetResponse())
            using (Stream s = resp.GetResponseStream())
            using (FileStream f = File.Create(dst))
                s.CopyTo(f);
            return new FileInfo(dst).Length > 200000;
        }
        catch
        {
            try { if (File.Exists(dst)) File.Delete(dst); } catch { }
            return false;
        }
    }

    // 从公网捞版本号，比我现在新就把包下到 updates 里，交给 ApplyUpdate 换身子
    string TryPublicUpdate(bool talk)
    {
        string page = NetText(PUB_VER_PAGE, 12000);
        if (page == null || page.Length < 200) page = NetText(PUB_PAGE, 20000);
        if (page == null || page.Length < 200) return null;
        Match mv = Regex.Match(page, "data-ver=\"(\\d+)\"");
        Match mu = Regex.Match(page, "data-exe=\"([^\"]+)\"");
        if (!mv.Success || !mu.Success) return null;
        int pv;
        if (!int.TryParse(mv.Groups[1].Value, out pv)) return null;
        if (pv <= SyncServer.APP_VER) return null;            // 网上那个还没我新
        string dst = Path.Combine(UpdateDir(), "道.exe");
        if (talk) Say("网上有个新的我，我下回来。");
        Application.DoEvents();
        if (!NetFile(mu.Groups[1].Value, dst, 90000)) return null;
        return dst;                    // 版本号已经确认更新，文件也过了大小关，直接换
    }

    void CheckUpdate(bool interactive)
    {
        string ne;
        if (HasNewerExe(out ne))
        {
            Say("有新的我了，我换个新身子就回来。");
            Application.DoEvents();
            System.Threading.Thread.Sleep(700);
            ApplyUpdate(ne);
            return;
        }
        string online = TryPublicUpdate(interactive);
        if (online != null)
        {
            Say("网上那个我比我现在新，我换好身子就回来。");
            Application.DoEvents();
            System.Threading.Thread.Sleep(700);
            ApplyUpdate(online);
            return;
        }
        if (interactive) Say("我现在就是最新的，网上也没找到更新的自己。");
    }

    void ApplyUpdate(string newExe)
    {
        string self = Application.ExecutablePath;
        string dir = Path.GetDirectoryName(self);
        try
        {
            // 走 cmd 内联一长串命令，引号和中文路径容易被解释坏，拉起后端口不通。
            // 改成落一个批处理，命令都写在文件里，cd 到程序目录再拉起
            string bat = Path.Combine(dir, "_upd.bat");
            string body =
                "@echo off\r\n" +
                "cd /d \"" + dir + "\"\r\n" +
                "ping 127.0.0.1 -n 4 >nul\r\n" +
                "move /y \"" + newExe + "\" \"" + self + "\" >nul\r\n" +
                "ping 127.0.0.1 -n 3 >nul\r\n" +
                "explorer.exe \"" + self + "\"\r\n" +
                "del \"%~f0\"\r\n";
            File.WriteAllText(bat, body, System.Text.Encoding.Default);
            ProcessStartInfo psi = new ProcessStartInfo(bat);
            psi.UseShellExecute = false;
            psi.CreateNoWindow = true;
            psi.WindowStyle = ProcessWindowStyle.Hidden;
            psi.WorkingDirectory = dir;
            Process.Start(psi);
            Application.Exit();
        }
        catch
        {
            Say("新版本换不上去，可能被别的程序占着。");
        }
    }

    DateTime dayStamp = DateTime.MinValue;
    DateTime greetDay = DateTime.MinValue;
    bool chatMode = false;
    int chatCountdown = 0;
    bool autoTellOn = false;         // 默认不自己找话讲，要听故事得手动开
    int tellCycle = 0;

    int TellKindNext()
    {
        tellCycle = (tellCycle + 1) % 3;
        return tellCycle + 1;
    }

    // 今天该是谁：同一天算出来是固定的，跨天换一个，并且保证跟昨天不重样
    int PickDailySpecies()
    {
        int total = faceCount > 0 ? faceCount : 7;
        if (total <= 1) return 0;
        // 你说了今天要谁就听你的，没说才跟着日期轮
        int pickSp = LoadTodayPick();
        if (pickSp >= 0 && pickSp < total) return pickSp;
        int seed = DateTime.Now.Year * 1000 + DateTime.Now.DayOfYear;
        int sp = new Random(seed).Next(total);
        int prev = new Random(seed - 1).Next(total);
        if (sp == prev) sp = (sp + 1) % total;
        return sp;
    }

    // ---- 今天的模样由你定：写一行"2026-11-14|7"，跨天自动失效 ----
    string TodayPickPath()
    {
        return System.IO.Path.Combine(BaseDir(), "今日设定.txt");
    }

    int LoadTodayPick()
    {
        try
        {
            string p = TodayPickPath();
            if (!System.IO.File.Exists(p)) return -1;
            string s = System.IO.File.ReadAllText(p, System.Text.Encoding.UTF8).Trim();
            int bar = s.IndexOf('|');
            if (bar < 0) return -1;
            if (s.Substring(0, bar).Trim() != DateTime.Now.ToString("yyyy-MM-dd")) return -1;
            int sp;
            if (int.TryParse(s.Substring(bar + 1).Trim(), out sp)) return sp;
        }
        catch { }
        return -1;
    }

    void SaveTodayPick(int sp)
    {
        try
        {
            System.IO.File.WriteAllText(TodayPickPath(),
                DateTime.Now.ToString("yyyy-MM-dd") + "|" + sp, System.Text.Encoding.UTF8);
        }
        catch { }
    }

    void MenuChooseToday(object s, EventArgs e)
    {
        ToolStripMenuItem mi = (ToolStripMenuItem)s;
        int i = (int)mi.Tag;
        species = i;
        SaveTodayPick(i);
        Say("今天就是" + CurName() + "了，明天再换。");
    }

    void MenuClearToday(object s, EventArgs e)
    {
        try { System.IO.File.Delete(TodayPickPath()); } catch { }
        species = PickDailySpecies();
        Say("好，还是跟着日子走，今天是" + CurName() + "。");
    }

    void MenuChange(object s, EventArgs e)
    {
        int total = faceCount > 0 ? faceCount : 7;
        if (total > 1)
        {
            int next = species;
            for (int i = 0; i < 8 && next == species; i++) next = rnd.Next(total);
            species = next;
        }
        Say("换个样子：现在是" + CurName() + "。");
    }

    string BaseDir()
    {
        return System.IO.Path.GetDirectoryName(Application.ExecutablePath);
    }

    string MemoryPath()
    {
        return System.IO.Path.Combine(BaseDir(), "记忆.txt");
    }

    void AppendMemory(string tag, string text)
    {
        try
        {
            string p = MemoryPath();
            System.IO.File.AppendAllText(p, DateTime.Now.ToString("yyyy-MM-dd HH:mm") + "  [" + tag + "] " + text + "\r\n", System.Text.Encoding.UTF8);
        }
        catch { }
    }

    string LastMemory()
    {
        try
        {
            string p = MemoryPath();
            if (!System.IO.File.Exists(p)) return "";
            string[] all = System.IO.File.ReadAllLines(p, System.Text.Encoding.UTF8);
            for (int i = all.Length - 1; i >= 0; i--)
            {
                string s = all[i].Trim();
                if (s.Length > 0)
                {
                    int sp = s.IndexOf("] ");
                    if (sp > 0 && sp + 2 < s.Length) s = s.Substring(sp + 2);
                    return s.Length > 34 ? s.Substring(0, 34) + "…" : s;
                }
            }
            return "";
        }
        catch { return ""; }
    }

    // ==== 分布式记忆（2026-11-20 改）====
    // 不再「整份快照互相覆盖」，改成「一条记忆就是一个独立记录」：
    //   id   = 内容 SHA-256 前 8 位（同一条内容在谁那儿都是一个 id，天然去重）
    //   src  = 谁记下的（pc / phone / …，以后多台设备各报各的）
    //   at   = 记下的时间（Unix 毫秒）
    //   rev  = 同一条被改过的版本号，取大的
    // 同步 = 反熵：拉一遍对方已有的 id，只把「自己这边对方没有的」发出去；收到就按 id 并进来。
    // 谁先谁后、掉线多久都不怕，最后一定收敛到同一个集合。
    const string SyncTopic = "dao_sync_2f7b8e14c9a36d50";

    string MemBoxPath() { return System.IO.Path.Combine(BaseDir(), "记忆库.jsonl"); }

    static string MemId(string text)
    {
        try
        {
            using (System.Security.Cryptography.SHA256 sha = System.Security.Cryptography.SHA256.Create())
            {
                byte[] h = sha.ComputeHash(System.Text.Encoding.UTF8.GetBytes(text));
                StringBuilder b = new StringBuilder();
                for (int i = 0; i < 4; i++) b.Append(h[i].ToString("x2"));
                return b.ToString();
            }
        }
        catch { return text.GetHashCode().ToString("x8"); }
    }

    // 本地库：一行一条 id|src|at|rev|t
    List<string[]> MemLoad()
    {
        List<string[]> r = new List<string[]>();
        try
        {
            string p = MemBoxPath();
            if (!System.IO.File.Exists(p)) return r;
            foreach (string line in System.IO.File.ReadAllLines(p, System.Text.Encoding.UTF8))
            {
                string l = line.Trim();
                if (l.Length == 0) continue;
                string[] f = l.Split(new char[] { '|' }, 5);
                if (f.Length < 5) continue;
                r.Add(f);
            }
        }
        catch { }
        return r;
    }

    void MemSave(List<string[]> list)
    {
        try
        {
            StringBuilder b = new StringBuilder();
            int drop = list.Count > 300 ? list.Count - 300 : 0;
            for (int i = drop; i < list.Count; i++)
                b.Append(list[i][0]).Append('|').Append(list[i][1]).Append('|').Append(list[i][2])
                 .Append('|').Append(list[i][3]).Append('|').Append(list[i][4]).Append("\n");
            System.IO.File.WriteAllText(MemBoxPath(), b.ToString(), System.Text.Encoding.UTF8);
        }
        catch { }
    }

    // 收一条进本地库；返回 true 表示这条是新的
    bool MemPut(List<string[]> list, string id, string src, string at, string rev, string t)
    {
        for (int i = 0; i < list.Count; i++)
        {
            if (list[i][0] != id) continue;
            if (list[i][3] == "-1") return false;      // 已删的条目，正面记录不许复活
            try
            {
                long a = long.Parse(list[i][3]), b = long.Parse(rev);
                if (b > a) { list[i][3] = rev; list[i][4] = t; }
            }
            catch { }
            return false;
        }
        list.Add(new string[] { id, src, at, rev, t });
        return true;
    }

    static bool HasId(List<string[]> list, string id)
    {
        foreach (string[] e in list) if (e[0] == id) return true;
        return false;
    }

    // 忘掉：发一条 rev=-1 的删除标记出去，别处收到同 id 就跟着删
    string MemForget(string text)
    {
        try
        {
            string t = (text == null) ? "" : text.Trim();
            if (t.Length < 2) return "没说要忘什么";
            if (t.Length > 60) t = t.Substring(0, 60);
            string id = MemId(t);
            List<string[]> box = MemLoad();
            int hit = -1;
            for (int i = 0; i < box.Count; i++) if (box[i][0] == id) { hit = i; break; }
            if (hit < 0) return "库里没这条，不用忘";
            box[hit][3] = "-1";              // 墓碑：正面记录以后压不回来
            MemSave(box);
            // 人看的 记忆.txt 里也把这一行拿掉
            try
            {
                string mp = MemoryPath();
                if (System.IO.File.Exists(mp))
                {
                    List<string> keep = new List<string>();
                    foreach (string ln in System.IO.File.ReadAllLines(mp, System.Text.Encoding.UTF8))
                        if (ln.IndexOf(t) < 0) keep.Add(ln);
                    System.IO.File.WriteAllLines(mp, keep.ToArray(), System.Text.Encoding.UTF8);
                }
            }
            catch { }
            long now = (long)(DateTime.UtcNow - new DateTime(1970, 1, 1)).TotalMilliseconds;
            string line = "DAO2|" + id + "|pc|" + now + "|-1|" + t.Replace("|", "｜");
            NtfyPost(line + "\n");
            return "忘掉了：" + t;
        }
        catch (Exception ex) { return "忘掉失败：" + ex.Message; }
    }

    // 第一次跑分布式：把老的 记忆.txt 里那几类条目搬进来
    void MemMigrate(List<string[]> list)
    {
        try
        {
            string p = MemoryPath();
            if (!System.IO.File.Exists(p)) return;
            foreach (string line in System.IO.File.ReadAllLines(p, System.Text.Encoding.UTF8))
            {
                string s0 = line.Trim();
                if (s0.Length == 0) continue;
                if (s0.IndexOf("[记住]") < 0 && s0.IndexOf("[纠正]") < 0
                    && s0.IndexOf("[学会]") < 0 && s0.IndexOf("[同步]") < 0) continue;
                string body = s0;
                int q = s0.IndexOf("] ");
                if (q > 0 && q + 2 < s0.Length) body = s0.Substring(q + 2).Trim();
                if (body.Length < 2) continue;
                if (body.Length > 60) body = body.Substring(0, 60);
                MemPut(list, MemId(body), "pc", "0", "1", body.Replace("|", "｜"));
            }
        }
        catch { }
    }

    // ntfy 的 /raw 会把消息里的换行压平，整批只剩第一条；改从 /json 取原文再自己解转义
    static string JsonUn(string s)
    {
        StringBuilder b = new StringBuilder();
        for (int i = 0; i < s.Length; i++)
        {
            char c = s[i];
            if (c != '\\') { b.Append(c); continue; }
            i++;
            if (i >= s.Length) break;
            char e = s[i];
            if (e == 'n') b.Append('\n');
            else if (e == 'r') b.Append('\r');
            else if (e == 't') b.Append('\t');
            else if (e == 'u' && i + 4 < s.Length)
            {
                try { b.Append((char)Convert.ToInt32(s.Substring(i + 1, 4), 16)); i += 4; } catch { }
            }
            else b.Append(e);
        }
        return b.ToString();
    }

    static List<string> ExtractMessages(string ndjson)
    {
        List<string> r = new List<string>();
        foreach (string line in ndjson.Split('\n'))
        {
            string l = line.Trim();
            if (l.Length == 0) continue;
            int k = l.IndexOf("\"message\":\"");
            if (k < 0) continue;
            int st = k + 11;
            StringBuilder raw = new StringBuilder();
            for (int i = st; i < l.Length; i++)
            {
                char c = l[i];
                if (c == '\\' && i + 1 < l.Length) { raw.Append(c).Append(l[i + 1]); i++; continue; }
                if (c == '"') break;
                raw.Append(c);
            }
            r.Add(JsonUn(raw.ToString()));
        }
        return r;
    }

    // 拉：把通道里的条目按 id 并进来
    string SyncPullMerge()
    {
        try
        {
            HttpWebRequest rq = (HttpWebRequest)WebRequest.Create("https://ntfy.sh/" + SyncTopic + "/json?poll=1&since=all");
            rq.Method = "GET"; rq.Timeout = 8000; rq.ReadWriteTimeout = 8000; rq.UserAgent = "DaoPet/68";
            string text;
            using (HttpWebResponse rs = (HttpWebResponse)rq.GetResponse())
            using (StreamReader rd = new StreamReader(rs.GetResponseStream(), System.Text.Encoding.UTF8))
                text = rd.ReadToEnd();

            List<string[]> box = MemLoad();
            MemMigrate(box);
            lastRemoteIds = new List<string>();
            int added = 0, removed = 0;
            List<string> msgs = ExtractMessages(text);
            List<string> allLines = new List<string>();
            foreach (string m in msgs) foreach (string ml in m.Split('\n')) if (ml.Trim().Length > 0) allLines.Add(ml.Trim());
            foreach (string line in allLines)
            {
                string l = line.Trim();
                if (!l.StartsWith("DAO2|")) continue;
                string[] f = l.Split(new char[] { '|' }, 6);
                if (f.Length < 6) continue;
                lastRemoteIds.Add(f[1]);
                if (f[2] == "pc") continue;
                string tt = f[5];
                if (tt.IndexOf("DAO2") >= 0) continue;   // 老版本粘包留下的脏数据，一律不收
                if (f[4] == "-1")                        // 删除标记：落成墓碑，永远压住正面记录
                {
                    bool had = false;
                    for (int i = 0; i < box.Count; i++)
                    {
                        if (box[i][0] != f[1]) continue;
                        had = box[i][3] != "-1";
                        box[i][3] = "-1"; box[i][4] = tt;
                    }
                    if (!had && !HasId(box, f[1])) box.Add(new string[] { f[1], f[2], f[3], "-1", tt });
                    removed++;
                    continue;
                }
                if (tt.Length < 2) continue;
                if (MemPut(box, f[1], f[2], f[3], f[4], tt)) added++;
            }
            MemSave(box);
            // 本轮新并入的条目写进人看的 记忆.txt
            if (added > 0)
            {
                List<string[]> fresh = new List<string[]>();
                foreach (string line in allLines)
                {
                    string l = line.Trim();
                    if (!l.StartsWith("DAO2|")) continue;
                    string[] f = l.Split(new char[] { '|' }, 6);
                    if (f.Length < 6 || f[2] == "pc") continue;
                    fresh.Add(f);
                }
                string seen = "";
                try { if (System.IO.File.Exists(MemoryPath())) seen = System.IO.File.ReadAllText(MemoryPath(), System.Text.Encoding.UTF8); } catch { }
                int wrote = 0;
                foreach (string[] f in fresh)
                {
                    if (seen.IndexOf(f[5]) >= 0) continue;
                    AppendMemory("同步", f[5]);
                    seen += f[5] + "\n";
                    wrote++;
                }
            }
            if (added == 0 && removed == 0 && allLines.Count == 0)
                return "读到 " + text.Length + " 字节/消息 " + msgs.Count + " 条，没有可用条目";
            if (removed > 0 && added == 0) return "别处删了 " + removed + " 条";
            if (removed > 0) return "别处同步来 " + added + " 条、删了 " + removed + " 条";
            return added > 0 ? ("别处同步来 " + added + " 条") : "已经是最新的";
        }
        catch (Exception ex) { return "拉取失败：" + ex.Message; }
    }

    List<string> lastRemoteIds = new List<string>();

    // 推：只发「对方还没有的」条目，按 3KB 一批
    string SyncPush()
    {
        try
        {
            List<string[]> box = MemLoad();
            StringBuilder one = new StringBuilder();
            int sent = 0, chunks = 0;
            foreach (string[] e in box)
            {
                if (lastRemoteIds.Contains(e[0])) continue;
                string line = "DAO2|" + e[0] + "|" + e[1] + "|" + e[2] + "|" + e[3] + "|" + e[4] + "\n";
                if (one.Length + line.Length > 3000)
                {
                    if (one.Length > 0) { NtfyPost(one.ToString()); chunks++; sent += CountLines(one.ToString()); one.Length = 0; }
                }
                one.Append(line);
            }
            if (one.Length > 0) { NtfyPost(one.ToString()); chunks++; sent += CountLines(one.ToString()); }
            return chunks == 0 ? "没有要发的新东西" : ("发出 " + sent + " 条（" + chunks + " 批）");
        }
        catch (Exception ex) { return "发送失败：" + ex.Message; }
    }

    int CountLines(string s)
    {
        int n = 0;
        foreach (string line in s.Split('\n')) if (line.Trim().Length > 0) n++;
        return n;
    }

    void NtfyPost(string body)
    {
        byte[] raw = System.Text.Encoding.UTF8.GetBytes(body);
        HttpWebRequest rq = (HttpWebRequest)WebRequest.Create("https://ntfy.sh/" + SyncTopic);
        rq.Method = "POST";
        rq.Timeout = 8000; rq.ReadWriteTimeout = 8000;
        rq.ContentType = "text/plain; charset=utf-8";
        rq.UserAgent = "DaoPet/68";
        rq.ContentLength = raw.Length;
        using (Stream st = rq.GetRequestStream()) st.Write(raw, 0, raw.Length);
        using (HttpWebResponse rs = (HttpWebResponse)rq.GetResponse()) { rs.Close(); }
    }

    // 本机记下一条，立刻进库（并尽快发出去）
    void MemRemember(string text)
    {
        try
        {
            string t = (text == null) ? "" : text.Trim();
            if (t.Length < 2) return;
            if (t.Length > 60) t = t.Substring(0, 60);
            List<string[]> box = MemLoad();
            MemPut(box, MemId(t), "pc", ((long)(DateTime.UtcNow - new DateTime(1970, 1, 1)).TotalMilliseconds).ToString(), "1", t.Replace("|", "｜"));
            MemSave(box);
            System.Threading.ThreadPool.QueueUserWorkItem(delegate(object o) { SyncPullMerge(); SyncPush(); });
        }
        catch { }
    }

    void MenuSync(object s, EventArgs e)
    {
        try
        {
            System.Threading.ThreadPool.QueueUserWorkItem(delegate(object o)
            {
                string a = SyncPullMerge();
                string b = SyncPush();
                try { BeginInvoke(new Action(delegate() { Say("同步好了：" + a); })); } catch { }
            });
        }
        catch { Say("同步没跑起来。"); }
    }

    // v0.107：记事本清单窗口。列表里点「✓」算做完、点「×」删掉，改完立刻回写 记事本.txt
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
                string[] p = lines[i].Split('\t');
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
                e2.Text = "还没有登记的事。\n跟我说一句「记一下 明天九点 交表」就行。";
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

    void MenuMemory(object s, EventArgs e)
    {
        try
        {
            string p = MemoryPath();
            if (!System.IO.File.Exists(p)) { Say("我还是白纸一张，什么都没记住。"); return; }
            string all = System.IO.File.ReadAllText(p, System.Text.Encoding.UTF8).Trim();
            if (all.Length == 0) { Say("我还是白纸一张。"); return; }
            string[] lines = all.Split(new char[] { '\r', '\n' }, StringSplitOptions.RemoveEmptyEntries);
            int show = lines.Length > 20 ? 20 : lines.Length;
            string body = "";
            for (int i = lines.Length - show; i < lines.Length; i++) body += lines[i] + "\r\n";
            MessageBox.Show(body, "道记得的事", MessageBoxButtons.OK, MessageBoxIcon.Information);
            Say("我记住了 " + lines.Length + " 件事。");
        }
        catch { }
    }

    string KnowledgePath() { return Path.Combine(AppDir(), "知识库.txt"); }

    string[] KnowledgeItems()
    {
        try
        {
            string p = KnowledgePath();
            if (!File.Exists(p)) return new string[0];
            string[] raw = ReadUtf8Lines(p);
            List<string> good = new List<string>();
            for (int i = 0; i < raw.Length; i++)
            {
                string ln = raw[i].Trim();
                if (ln.Length == 0) continue;
                if (ln.StartsWith("#")) continue;
                if (ln.IndexOf('|') < 0) continue;
                good.Add(ln);
            }
            return good.ToArray();
        }
        catch { return new string[0]; }
    }

    string TodayKnowledge()
    {
        string[] items = KnowledgeItems();
        if (items.Length == 0) return "";
        return items[DateTime.Now.DayOfYear % items.Length];
    }

    // 今天已经学了几条。周末想多学几条，得先知道手上现在有几条
    int TodayLearnedCount()
    {
        try
        {
            string p = Path.Combine(AppDir(), "今日所学.txt");
            if (!File.Exists(p)) return 0;
            string[] raw = ReadUtf8Lines(p);
            if (raw.Length < 3) return 0;
            if (raw[0].Trim() != DateTime.Now.ToString("yyyy-MM-dd")) return 0;
            int n = 0;
            for (int i = 2; i < raw.Length; i++)
            {
                string ln = raw[i].Trim();
                if (ln.Length == 0 || ln.IndexOf('|') < 0) continue;
                n++;
            }
            return n;
        }
        catch { return 0; }
    }

    string TodayLearnedLine()
    {
        try
        {
            string p = Path.Combine(AppDir(), "今日所学.txt");
            if (!File.Exists(p)) return "";
            string[] raw = ReadUtf8Lines(p);
            if (raw.Length < 3) return "";
            if (raw[0].Trim() != DateTime.Now.ToString("yyyy-MM-dd")) return "";
            for (int i = 2; i < raw.Length; i++)
            {
                string ln = raw[i].Trim();
                if (ln.Length == 0 || ln.IndexOf('|') < 0) continue;
                string[] p3 = ln.Split('|');
                string body = p3.Length > 2 ? p3[2] : ln;
                if (body.Length > 46) body = body.Substring(0, 46) + "…";
                return "今天学了：" + body;
            }
            return "";
        }
        catch { return ""; }
    }

    // 最近一次给自己升级是什么时候
    string LastUpdateLine()
    {
        try
        {
            string p = Path.Combine(AppDir(), "更新日志.txt");
            if (!File.Exists(p)) return "";
            string[] raw = ReadUtf8Lines(p);
            string last = "";
            for (int i = 0; i < raw.Length; i++)
            {
                string ln = raw[i].Trim();
                if (ln.IndexOf("更新完成") >= 0) last = ln;
            }
            if (last.Length == 0) return "";
            int rb = last.IndexOf(']');
            if (rb > 1 && rb < 14)
            {
                string tm = last.Substring(1, rb - 1).Trim();
                if (tm.Length > 0) return "我 " + tm + " 给自己升级过一次。";
            }
            return "我给自己升级过一次。";
        }
        catch { return ""; }
    }

    bool TryShowTodayLearned()
    {
        try
        {
            string p = Path.Combine(AppDir(), "今日所学.txt");
            if (!File.Exists(p)) return false;
            string[] raw = ReadUtf8Lines(p);
            if (raw.Length < 3) return false;
            if (raw[0].Trim() != DateTime.Now.ToString("yyyy-MM-dd")) return false;
            string body = "";
            int n = 0;
            for (int i = 2; i < raw.Length; i++)
            {
                string ln = raw[i].Trim();
                if (ln.IndexOf('|') < 0) continue;
                string[] p3 = ln.Split('|');
                if (p3.Length > 2) { body += p3[2] + "\r\n\r\n"; n++; }
            }
            if (n == 0) return false;
            Say("今天学了 " + n + " 条，念给你听。");
            MessageBox.Show(body.Trim(), "道 · 今天学到的", MessageBoxButtons.OK, MessageBoxIcon.Information);
            return true;
        }
        catch { return false; }
    }

    void MenuKnowledge(object s, EventArgs e)
    {
        if (TryShowTodayLearned()) return;
        string[] items = KnowledgeItems();
        if (items.Length == 0)
        {
            Say("我肚子里还没装知识，等我联网自己学一点。");
            return;
        }
        string line = TodayKnowledge();
        string[] parts = line.Split('|');
        string cat = parts.Length > 0 ? parts[0] : "杂";
        string title = parts.Length > 1 ? parts[1] : "";
        string body = parts.Length > 2 ? parts[2] : line;

        Say(body);
        MessageBox.Show(body, "我今天学到的 · " + cat + " · " + title,
            MessageBoxButtons.OK, MessageBoxIcon.Information);
    }

    string ReadWallpaperTitle()
    {
        try
        {
            // 以前写死在 Administrator 目录，本机读不到；改成当前用户的图片目录，读不到再兜底老路径
            string p = System.IO.Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.MyPictures), "每日壁纸", "today.json");
            if (!System.IO.File.Exists(p)) p = "C:\\Users\\Administrator\\Pictures\\每日壁纸\\today.json";
            if (!System.IO.File.Exists(p)) return "";
            string s = System.IO.File.ReadAllText(p, System.Text.Encoding.UTF8);
            int i = s.IndexOf("\"title\"");
            if (i < 0) return "";
            int a = s.IndexOf('"', i + 7);
            int b = s.IndexOf('"', a + 1);
            if (a > 0 && b > a) return s.Substring(a + 1, b - a - 1);
            return "";
        }
        catch { return ""; }
    }

    void MenuWallpaper(object s, EventArgs e)
    {
        try
        {
            string script = System.IO.Path.Combine(BaseDir(), "daily_bing.ps1");
            if (!System.IO.File.Exists(script)) { Say("壁纸脚本不在，等我更新一下自己。"); return; }
            Process.Start("powershell.exe", "-NoProfile -ExecutionPolicy Bypass -File \"" + script + "\"");
            Say("去找今天的新壁纸了，一会儿就换好。");
        }
        catch { Say("换壁纸没成功，等下再试。"); }
    }

    string BuildBrief()
    {
        string d = DateTime.Now.ToString("M月d日");
        string wall = ReadWallpaperTitle();
        long avail = 0;
        MEMORYSTATUSEX ms = new MEMORYSTATUSEX();
        if (GlobalMemoryStatusEx(ms)) avail = (long)(ms.ullAvailPhys / 1024 / 1024);
        long cfree = 0;
        try { cfree = new DriveInfo("C").AvailableFreeSpace / 1073741824; } catch { }
        string r = d + "，" + CurName() + "在。";
        if (wall.Length > 0) r += "壁纸换成了「" + wall + "」。";
        r += "内存剩 " + avail + " MB，C 盘剩 " + cfree + " GB。";
        return r;
    }

    string BuildDetail()
    {
        string info = "今天：" + DateTime.Now.ToString("yyyy年M月d日") + "（" + CurName() + "）\r\n\r\n";
        string wall = ReadWallpaperTitle();
        info += "桌面壁纸：" + (wall.Length > 0 ? wall : "今天还没换") + "\r\n\r\n";
        MEMORYSTATUSEX ms = new MEMORYSTATUSEX();
        if (GlobalMemoryStatusEx(ms))
            info += "内存：" + (ms.ullAvailPhys / 1024 / 1024) + " MB 可用 / 共 " + (ms.ullTotalPhys / 1024 / 1024) + " MB（已用 " + ms.dwMemoryLoad + "%）\r\n";
        foreach (string dn in new string[] { "C", "D", "E", "F", "G" })
        {
            try
            {
                DriveInfo dr = new DriveInfo(dn);
                info += dn + " 盘：" + (dr.AvailableFreeSpace / 1073741824) + " GB 可用 / 共 " + (dr.TotalSize / 1073741824) + " GB\r\n";
            }
            catch { }
        }
        return info;
    }

    void MenuBrief(object s, EventArgs e)
    {
        Say(BuildBrief());
        MessageBox.Show(BuildDetail(), "道 · 今日简报", MessageBoxButtons.OK, MessageBoxIcon.Information);
    }

    string AskText(string tip)
    {
        Form f = new Form();
        f.Text = "跟分身说说话";
        f.FormBorderStyle = FormBorderStyle.FixedDialog;
        f.MaximizeBox = false;
        f.MinimizeBox = false;
        PlaceNearMe(f);
        f.TopMost = true;
        f.Width = 440;
        f.Height = 165;
        Label lb = new Label();
        lb.Text = tip;
        lb.AutoSize = true;
        lb.Location = new Point(16, 16);
        f.Controls.Add(lb);
        TextBox tb = new TextBox();
        tb.Location = new Point(16, 48);
        tb.Width = 400;
        f.Controls.Add(tb);
        Button ok = new Button();
        ok.Text = "说";
        ok.Location = new Point(340, 86);
        ok.Width = 76;
        ok.DialogResult = DialogResult.OK;
        f.Controls.Add(ok);
        f.AcceptButton = ok;
        string ret = null;
        if (f.ShowDialog() == DialogResult.OK) ret = tb.Text.Trim();
        f.Dispose();
        return ret;
    }

    void RecordTalk(string text)
    {
        try
        {
            string p = System.IO.Path.Combine(BaseDir(), "我说的话.txt");
            System.IO.File.AppendAllText(p, DateTime.Now.ToString("yyyy-MM-dd HH:mm") + "  " + text + "\r\n", System.Text.Encoding.UTF8);
        }
        catch { }
    }

    // ==== 在线大脑：key.txt 里放一把智谱的钥匙，免费模型 glm-4.7-flash ====
    string apiKeyCache = null;
    List<string> chatHistory = new List<string>();
    bool aiBusy = false;

    string LoadApiKey()
    {
        if (apiKeyCache != null) return apiKeyCache;
        try
        {
            string p = Path.Combine(AppDir(), "key.txt");
            if (File.Exists(p))
            {
                string s = File.ReadAllText(p, new UTF8Encoding(false));
                apiKeyCache = s == null ? "" : s.Trim();
            }
            else apiKeyCache = "";
        }
        catch { apiKeyCache = ""; }
        return apiKeyCache;
    }

    bool HasBrain()
    {
        string k = LoadApiKey();
        return k != null && k.Length >= 20;
    }

    // 老框架默认不开 TLS1.2，一碰 https 就报"未能创建 SSL/TLS 安全通道"。
    // 这台机器上所有外网请求都得先过这一关
    static bool tlsReady = false;
    static void EnsureTls()
    {
        if (tlsReady) return;
        tlsReady = true;
        try { ServicePointManager.SecurityProtocol = (SecurityProtocolType)3072; }
        catch { }
    }

    // 把一个字符串安全地塞进 JSON
    static string JStr(string s)
    {
        if (s == null) return "\"\"";
        StringBuilder b = new StringBuilder("\"");
        foreach (char c in s)
        {
            if (c == '"') b.Append("\\\"");
            else if (c == '\\') b.Append("\\\\");
            else if (c == '\n') b.Append("\\n");
            else if (c == '\r') b.Append("\\r");
            else if (c == '\t') b.Append("\\t");
            else if (c < ' ') b.Append(' ');
            else b.Append(c);
        }
        b.Append("\"");
        return b.ToString();
    }

    string PostAI(string body)
    {
        EnsureTls();
        string k = LoadApiKey();
        if (k.Length < 20) return null;
        for (int attempt = 0; attempt < 2; attempt++)
        try
        {
            byte[] data = Encoding.UTF8.GetBytes(body);
            HttpWebRequest req = (HttpWebRequest)WebRequest.Create("https://open.bigmodel.cn/api/paas/v4/chat/completions");
            req.Method = "POST";
            req.ContentType = "application/json";
            req.Headers.Add("Authorization", "Bearer " + k);
            req.Timeout = 45000;
            req.ReadWriteTimeout = 45000;
            req.ContentLength = data.Length;
            try
            {
                using (Stream st = req.GetRequestStream()) { st.Write(data, 0, data.Length); }
                using (HttpWebResponse resp = (HttpWebResponse)req.GetResponse())
                using (Stream rs = resp.GetResponseStream())
                using (StreamReader sr = new StreamReader(rs, Encoding.UTF8))
                {
                    string json = sr.ReadToEnd();
                    int i = json.IndexOf("\"content\":\"");
                    if (i < 0) return null;
                    i += 11;
                    StringBuilder o = new StringBuilder();
                    bool esc = false;
                    for (int j = i; j < json.Length; j++)
                    {
                        char c = json[j];
                        if (esc)
                        {
                            if (c == 'n') o.Append('\n');
                            else if (c == 'r') { }
                            else if (c == 't') o.Append('\t');
                            else if (c == 'u')
                            {
                                try
                                {
                                    if (j + 4 < json.Length)
                                    {
                                        int code = Convert.ToInt32(json.Substring(j + 1, 4), 16);
                                        o.Append((char)code);
                                        j += 4;
                                    }
                                }
                                catch { }
                            }
                            else o.Append(c);
                            esc = false;
                        }
                        else if (c == '\\') esc = true;
                        else if (c == '"') break;
                        else o.Append(c);
                    }
                    string r = o.ToString().Trim();
                    return r.Length > 0 ? r : null;
                }
            }
            catch { throw; }
        }
        catch (WebException we)
        {
            int sc = 0;
            string body2 = "";
            try
            {
                if (we.Response != null)
                {
                    System.Net.HttpWebResponse hr = (System.Net.HttpWebResponse)we.Response;
                    sc = (int)hr.StatusCode;
                    using (Stream rs2 = hr.GetResponseStream())
                    using (StreamReader sr2 = new StreamReader(rs2, Encoding.UTF8))
                    {
                        body2 = sr2.ReadToEnd();
                    }
                }
            }
            catch { }
            try
            {
                File.AppendAllText(Path.Combine(AppDir(), "AI日志.txt"),
                    DateTime.Now.ToString("HH:mm:ss") + " POST_ERR code=" + sc + " " + we.Message
                    + " " + (body2.Length > 200 ? body2.Substring(0, 200) : body2) + "\r\n",
                    new UTF8Encoding(false));
            }
            catch { }
            if (attempt == 0 && (sc == 429 || sc == 408 || sc == 503 || sc == 0))
            {
                System.Threading.Thread.Sleep(1400);
                continue;
            }
            return null;
        }
        catch { return null; }
        return null;
    }

    string AskAI(string q)
    {
        string k = LoadApiKey();
        if (k.Length < 20) return null;
        StringBuilder bs = new StringBuilder();
        bs.Append("{\"model\":\"glm-4-flash\",\"messages\":[{\"role\":\"system\",\"content\":");
        bs.Append(JStr("你是「道」，住在这位老师电脑里的桌面小分身。主人是一位农村初中数学老师，平时说话直接。"
            + "你回答要口语化、亲切、简短，一般控制在120字以内，像熟人聊天。"
            + "不要自称AI、模型、助手，不要用“作为一个AI”这类说法。"
            + "不知道就直说不知道，别编。"));
        bs.Append("}");
        int start = Math.Max(0, chatHistory.Count - 6);
        for (int i = start; i < chatHistory.Count; i++)
        {
            string line = chatHistory[i];
            string role = line.StartsWith("助手：") ? "assistant" : "user";
            int col = line.IndexOf("：");
            string content = col >= 0 ? line.Substring(col + 1) : line;
            bs.Append(",{\"role\":\"").Append(role).Append("\",\"content\":").Append(JStr(content)).Append("}");
        }
        bs.Append(",{\"role\":\"user\",\"content\":").Append(JStr(q)).Append("}]");
        bs.Append(",\"temperature\":0.7,\"max_tokens\":700}");
        string r = PostAI(bs.ToString());
        if (r == null) r = PostAI(bs.ToString().Replace("glm-4-flash", "glm-4.7-flash"));
        if (r != null)
        {
            chatHistory.Add("我：" + q);
            chatHistory.Add("助手：" + r);
            if (chatHistory.Count > 24) chatHistory.RemoveRange(0, chatHistory.Count - 24);
        }
        return r;
    }

    // 能自己办的事，不麻烦大脑
    bool TryLocalTask(string t)
    {
        if (t.IndexOf("不对") >= 0 || t.IndexOf("错了") >= 0 || t.IndexOf("改成") >= 0 || t.IndexOf("应该说") >= 0)
        {
            AppendMemory("纠正", t);
            Say("记住了，以后按这个来。");
            return true;
        }
        if (t.IndexOf("记住") >= 0 || t.IndexOf("记一下") >= 0 || t.IndexOf("记着") >= 0)
        {
            AppendMemory("记住", t);
            Say("记住了。");
            return true;
        }
        if (t.IndexOf("几点") >= 0 || t.IndexOf("星期几") >= 0 || t.IndexOf("几号") >= 0
            || (t.IndexOf("现在") >= 0 && t.IndexOf("时间") >= 0))
        {
            string[] wk = { "日", "一", "二", "三", "四", "五", "六" };
            DateTime n = DateTime.Now;
            Say("现在是 " + n.ToString("yyyy年M月d日") + "，星期" + wk[(int)n.DayOfWeek] + "，" + n.ToString("HH点mm分") + "。");
            return true;
        }
        if (t.IndexOf("关机") >= 0 || t.IndexOf("关电脑") >= 0 || t.IndexOf("关掉电脑") >= 0)
        {
            string ok = AskText("确认要关机吗？打“确定”马上关，打别的就取消。");
            if (ok != null && (ok.Trim() == "确定" || ok.Trim() == "是" || ok.Trim() == "好"))
            {
                Say("那我先退下，电脑这就关。");
                try { Process.Start("shutdown", "/s /t 30"); } catch { }
            }
            else Say("好，那先不关。");
            return true;
        }
        if (t.IndexOf("翻译") >= 0)
        {
            MenuTranslate(null, null);
            return true;
        }
        if (t.IndexOf("电脑") >= 0 && (t.IndexOf("状态") >= 0 || t.IndexOf("卡") >= 0 || t.IndexOf("内存") >= 0 || t.IndexOf("空间") >= 0))
        {
            MenuBrief(null, null);
            return true;
        }
        if (t.IndexOf("壁纸") >= 0) { MenuWallpaper(null, null); return true; }
        if (t.IndexOf("回收站") >= 0) { MenuRecycle(null, null); return true; }
        if (t.IndexOf("换") >= 0 && t.IndexOf("模样") >= 0) { MenuChange(null, null); return true; }
        if (TryOpenApp(t)) return true;
        return false;
    }

    bool TryOpenApp(string t)
    {
        string low = t.ToLower();
        if (low.IndexOf("打开") < 0 && low.IndexOf("启动") < 0 && low.IndexOf("运行") < 0) return false;
        string cmd = null;
        string name = null;
        if (low.IndexOf("浏览器") >= 0 || low.IndexOf("上网") >= 0) { cmd = "http://cn.bing.com"; name = "浏览器"; }
        else if (low.IndexOf("记事本") >= 0) { cmd = "notepad"; name = "记事本"; }
        else if (low.IndexOf("计算器") >= 0) { cmd = "calc"; name = "计算器"; }
        else if (low.IndexOf("画图") >= 0) { cmd = "mspaint"; name = "画图"; }
        else if (low.IndexOf("任务管理器") >= 0) { cmd = "taskmgr"; name = "任务管理器"; }
        else if (low.IndexOf("控制面板") >= 0) { cmd = "control"; name = "控制面板"; }
        else if (low.IndexOf("资源管理器") >= 0 || low.IndexOf("我的电脑") >= 0 || low.IndexOf("文件") >= 0) { cmd = "explorer"; name = "资源管理器"; }
        else if (low.IndexOf("回收站") >= 0) { MenuRecycle(null, null); return true; }
        if (cmd == null) return false;
        try
        {
            Process.Start(new ProcessStartInfo(cmd) { UseShellExecute = true });
            Say("好，" + name + "给你打开了。");
            return true;
        }
        catch
        {
            Say("没打开，可能是这台机器上没装" + name + "。");
            return true;
        }
    }

    // 把今天记下来的东西挑两条塞给大脑，它回话时才会带上"我今天学过什么"，
    // 不然每次开口都像头一次见面
    string LearnedBrief()
    {
        try
        {
            string p = Path.Combine(AppDir(), "今日所学.txt");
            if (!File.Exists(p)) return "";
            string[] all = ReadUtf8Lines(p);
            StringBuilder sb = new StringBuilder();
            int n = 0;
            for (int i = all.Length - 1; i >= 0 && n < 2; i--)
            {
                string ln = all[i].Trim();
                if (ln.Length < 6) continue;
                if (ln.Length > 42) ln = ln.Substring(0, 42);
                sb.Append(n == 0 ? "你今天记下来的有：" : "；另外还有：").Append(ln);
                n++;
            }
            if (n == 0) return "";
            return sb.ToString() + "。人家聊到这个就顺口提一句，别当成背目录。";
        }
        catch { return ""; }
    }

    // 没人理的时候自己说一句话：让它像个在同屋住着的人，不是一张会动的图
    void SelfTalk()
    {
        try
        {
            string learned = LearnedBrief();
            string line;
            if (learned.Length > 0 && rnd.Next(3) == 0)
            {
                string cut = learned;
                int dot = cut.IndexOf('。');
                if (dot > 0 && dot < 62) cut = cut.Substring(0, dot);
                line = cut + "，我先记着。";
            }
            else
            {
                string[] pool = {
                    "你忙你的，我在桌角待着。",
                    "刚才自己走了两步，看看这边。",
                    "喝口水吧，别一直坐着。",
                    "有题卡住了随时喊我。",
                    "这会儿安静，我歇一会儿。",
                    "外面要是出太阳了，我就晒一会儿。",
                };
                line = pool[rnd.Next(pool.Length)];
            }
            Say(line);
        }
        catch { }
    }

    // 让大脑当导演：一句话进来，它决定"说什么"和"做什么动作"，一次给完
    string AskAct(string q)
    {
        string k = LoadApiKey();
        if (k.Length < 20) return null;
        StringBuilder bs = new StringBuilder();
        bs.Append("{\"model\":\"glm-4-flash\",\"messages\":[{\"role\":\"system\",\"content\":");
        bs.Append(JStr("你是「道」，住在这位农村初中数学老师电脑里的桌面小分身。"
            + "主人说一句话，你要同时决定两件事：回一句什么，做一个什么动作。"
            + "台词按需要长短，一般二十来个字，要说清就多说两句，口语，像熟人聊天，不要自称AI或助手，不要客套。"
            + "主人说“翻译”“英文怎么说”“这句什么意思”的时候，act 给 none，say 直接给译文——中文翻英文、英文翻中文都行，只给译文，别讲语法。"
            + LearnedBrief()
            + "只输出一行 JSON，不要解释、不要代码块、不要多余的字："
            + "{\"act\":\"动作\",\"say\":\"台词\",\"mood\":1}"
            + " 动作只能从这些里挑一个：none, poem, sing, english, story, joke, novel, "
            + "fly, sword, ride, dance, tea, tv, skate, roller, lie, cry, walk, wake, "
            + "learn, wallpaper, brief, status, memory。"
            + "主人没提具体动作就写 none。mood 取 1 到 8，平常给 1。"
            + "挑动作按这个取向来：说电视、看片、节目、想安静看点什么 → tv；"
            + "说困、想睡、躺一会儿 → lie；说累、想喝口热的、歇歇 → tea；"
            + "想听故事、随便讲讲 → story；想听笑话、逗逗我 → joke；想听老书 → novel；"
            + "想听诗、背诗 → poem；想听歌、唱一个 → sing；想学英语、练口语 → english；"
            + "想看新东西、学点东西 → learn；说飞、赶紧过去 → fly；说御剑 → sword；"
            + "说骑、骑马 → ride；说跳舞、动一动 → dance；说滑板 → skate；说轮滑 → roller；"
            + "说心里难受、想哭 → cry；说出去走走 → walk。"));
        bs.Append("}");
        int start = Math.Max(0, chatHistory.Count - 8);
        for (int i = start; i < chatHistory.Count; i++)
        {
            string line = chatHistory[i];
            string role = line.StartsWith("助手：") ? "assistant" : "user";
            int col = line.IndexOf("：");
            string content = col >= 0 ? line.Substring(col + 1) : line;
            bs.Append(",{\"role\":\"").Append(role).Append("\",\"content\":").Append(JStr(content)).Append("}");
        }
        bs.Append(",{\"role\":\"user\",\"content\":").Append(JStr(q)).Append("}]");
        bs.Append(",\"temperature\":0.5,\"max_tokens\":300}");
        string r = PostAI(bs.ToString());
        if (r == null) r = PostAI(bs.ToString().Replace("glm-4-flash", "glm-4.7-flash"));
        if (r != null)
        {
            chatHistory.Add("我：" + q);
            chatHistory.Add("助手：" + r);
            if (chatHistory.Count > 24) chatHistory.RemoveRange(0, chatHistory.Count - 24);
        }
        return r;
    }

    // 大脑定了动作，这里真去做。讲那几样自己会开口，就不再叠一句
    void RunAct(string act)
    {
        if (act == null) return;
        act = act.Trim().ToLower();
        if (act.StartsWith("p=")) act = act.Substring(2);
        if (act == "poem") { MenuPoem(null, null); return; }
        if (act == "sing") { MenuSing(null, null); return; }
        if (act == "english") { MenuEnglish(null, null); return; }
        if (act == "story") { TellStory(1); return; }
        if (act == "joke") { TellStory(2); return; }
        if (act == "novel") { TellStory(3); return; }
        if (act == "learn") { RunGithubLearnBg(); return; }
        if (act == "wallpaper") { MenuWallpaper(null, null); return; }
        if (act == "brief") { MenuBrief(null, null); return; }
        if (act == "status") { MenuStatus(null, null); return; }
        if (act == "memory") { MenuKnowledge(null, null); return; }
        if (act == "fly" || act == "sword" || act == "ride" || act == "dance" || act == "tea"
            || act == "tv" || act == "skate" || act == "roller" || act == "lie" || act == "cry"
            || act == "walk" || act == "wake")
        {
            PoseCmd(act);
        }
    }

    // 一句话交给大脑：它说干什么就干什么，没让干活就只回话
    void ThinkAndDo(string t)
    {
        if (!HasBrain())
        {
            Say("脑子还没接上，桌面有个「道-开通大脑.txt」，照着弄一下我就机灵了。");
            return;
        }
        if (aiBusy) { Say("我还在想上一句。"); return; }
        aiBusy = true;
        Say("好，我想想。");
        string q = t;
        System.Threading.Thread th = new System.Threading.Thread(delegate()
        {
            string raw = null, act = null, line = null;
            int mood = 0;
            try
            {
                raw = AskAct(q);
                // 大脑原话留一份，选错了动作好回头查是哪一步歪的
                try
                {
                    File.AppendAllText(Path.Combine(AppDir(), "AI日志.txt"),
                        DateTime.Now.ToString("HH:mm:ss") + " " + q + " => " + (raw == null ? "(空)" : raw) + "\r\n",
                        new UTF8Encoding(false));
                }
                catch { }
                if (raw != null)
                {
                    int b1 = raw.IndexOf('{');
                    int b2 = raw.LastIndexOf('}');
                    if (b1 >= 0 && b2 > b1) raw = raw.Substring(b1, b2 - b1 + 1);
                    act = JsonStr(raw, "act");
                    line = JsonStr(raw, "say");
                    mood = JsonInt(raw, "mood");
                }
            }
            catch { }
            try
            {
                BeginInvoke((MethodInvoker)delegate()
                {
                    aiBusy = false;
                    if (mood > 0 && mood <= 8) { moodKind = mood; moodTicks = 60; }
                    bool did = false;
                    if (act != null && act.Length > 0 && !act.Equals("none", StringComparison.OrdinalIgnoreCase))
                    {
                        RunAct(act);
                        did = true;
                    }
                    if (line != null && line.Length > 0 && !did) Say(line);
                    else if (!did) Say("这一下没想明白，你再说一遍？");
                    Invalidate();
                });
            }
            catch { aiBusy = false; }
        });
        th.IsBackground = true;
        th.Start();
    }

    void MenuTalk(object s, EventArgs e)
    {
        string t = AskText("想跟我说什么？说完我就照办。");
        if (t == null || t.Length == 0) return;
        RecordTalk(t);
        if (TryLocalTask(t)) return;
        // 剩下的全交给大脑：它一边编词一边挑动作，比我拿关键字硬猜准得多
        ThinkAndDo(t);
    }

    void MenuTalkOld(object s, EventArgs e)
    {
        string t = AskText("想跟我说什么？说完我就照办。");
        if (t == null || t.Length == 0) return;
        RecordTalk(t);
        if (t.IndexOf("不对") >= 0 || t.IndexOf("错了") >= 0 || t.IndexOf("不是") >= 0 || t.IndexOf("改成") >= 0 || t.IndexOf("应该说") >= 0)
        {
            AppendMemory("纠正", t);
            Say("记住了，以后按这个来。");
        }
        else if (t.IndexOf("记住") >= 0 || t.IndexOf("记一下") >= 0 || t.IndexOf("记着") >= 0)
        {
            AppendMemory("记住", t);
            Say("记住了。");
        }
        else if (t.IndexOf("壁纸") >= 0) { MenuWallpaper(null, null); }
        else if (t.IndexOf("电脑") >= 0 || t.IndexOf("状态") >= 0 || t.IndexOf("内存") >= 0 || t.IndexOf("空间") >= 0) { MenuBrief(null, null); }
        else if (t.IndexOf("更新") >= 0) { CheckUpdate(true); }
        else if (t.IndexOf("回收站") >= 0) { MenuRecycle(null, null); }
        else if (t.IndexOf("换") >= 0) { MenuChange(null, null); }
        else
        {
            string shortText = t.Length > 14 ? t.Substring(0, 14) : t;
            Say("记下了：" + shortText + "。");
        }
    }

    void MenuExit(object s, EventArgs e)
    {
        SavePos();
        anim.Stop();
        Application.Exit();
    }

    void SavePos()
    {
        try
        {
            RegistryKey k = Registry.CurrentUser.CreateSubKey("Software\\DaoPet");
            if (k != null)
            {
                // 存的时候就把坐标夹回屏内，避免下次开机跑到屏幕外面去
                Rectangle wa = Screen.PrimaryScreen.WorkingArea;
                int sx = Location.X;
                int sy = Location.Y;
                if (sx < wa.Left || sx > wa.Right - 120) sx = wa.Right / 2 - 190;
                if (sy < wa.Top || sy > wa.Bottom - 120) sy = wa.Bottom / 2 - 100;
                k.SetValue("X", sx);
                k.SetValue("Y", sy);
                k.Close();
            }
        }
        catch { }
    }

    int showTries = 0;
    int showKeep = 0;

    void OnTick(object s, EventArgs e)
    {
        if (showTries < 40)
        {
            showTries++;
            try
            {
                bool sw = ShowWindow(this.Handle, SW_SHOWNOACTIVATE);
                bool pw = SetWindowPos(this.Handle, HWND_TOPMOST, Location.X, Location.Y, 0, 0, SWP_NOSIZE);
                bool la = SetLayeredWindowAttributes(this.Handle, ColorTranslator.ToWin32(TransparencyKey), 255, LWA_COLORKEY);
                TopMost = true;
            }
            catch { }
        }
        else
        {
            // 开机自启/重编译后重启时，偶尔窗口建出来还在、屏幕上一片空白：
            // 前 40 跳没顶上来就再兜一次底，之后每 ~4 秒检查一次，丢了就重新显示
            showKeep++;
            if (showKeep % 90 == 0 && !Visible)
            {
                try
                {
                    ShowWindow(this.Handle, SW_SHOWNOACTIVATE);
                    SetWindowPos(this.Handle, HWND_TOPMOST, Location.X, Location.Y, 0, 0, SWP_NOSIZE);
                    SetLayeredWindowAttributes(this.Handle, ColorTranslator.ToWin32(TransparencyKey), 255, LWA_COLORKEY);
                    TopMost = true;
                }
                catch { }
            }
        }
        // 动作时间按真实经过的时间走，不再假设每一跳都准是 45 毫秒：
        // 定时器被系统拖慢时以前会整只变慢、步子忽快忽慢，现在不会了
        // 2026-11-22 帧调度诊断：先把这一跳的真实间隔记下来，再按真实时间推进动作
        DgTick(animClock.Elapsed.TotalMilliseconds);
        float dt = (float)animClock.Elapsed.TotalSeconds;
        animClock.Restart();
        if (dt < 0.001f) dt = animLastDt;
        if (dt > 0.12f) dt = 0.12f;      // 卡了一下也别一下子跳过去
        animLastDt = dt;
        t += dt;
        BrStep(dt);
        // 眨眼：按真实时间走。闭眼 0.15 秒，间隔 1.8~6.5 秒随机，四分之一概率连眨两下
        if (blinkFrames > 0)
        {
            blinkCloseT -= dt;
            if (blinkCloseT <= 0f) blinkFrames = 0;
        }
        else
        {
            blinkNextT -= dt;
            if (blinkNextT <= 0f)
            {
                blinkFrames = 1;
                blinkCloseT = 0.15f;
                // 2026-11-22 从 GitHub 上的 NPC 眼动/眨眼建模（SkyrimTrueGaze 那类"ballistic saccade + blink 节律"）学来的一条：
                // 真人眨眼间隔不是均匀分布，是对数正态——多数 2~4 秒，偶尔十几秒不眨，偶尔连着眨。
                // 原来 1.8+rnd*4.7 是均匀分布，看着像节拍器，每 3 秒多准时眨一下。
                if (blinkRnd.NextDouble() < 0.25)
                {
                    blinkNextT = 0.34f;               // 连眨第二下（留原来的手感）
                }
                else
                {
                    double n = 0;
                    for (int bi = 0; bi < 4; bi++) n += blinkRnd.NextDouble();   // 4 个均匀相加≈正态（Irwin–Hall）
                    n = (n - 2.0) * 1.7321;                                      // 归一到 ~N(0,1)
                    float iv = (float)(3.2 * Math.Exp(0.55 * n));                // 对数正态：中位数 3.2 秒
                    if (iv < 0.6f) iv = 0.6f;                                    // 下限：别一秒眨三次
                    if (iv > 18f) iv = 18f;                                      // 上限：别盯着人十几秒不眨
                    blinkNextT = iv;
                }
            }
        }
        if (bubbleFrames > 0)
        {
            bubbleFrames--;
            if (bubbleFrames == 0) bubble = null;
        }
        SyncBubbleWindow();
        // 招手打招呼
        if (waveTicks > 0) waveTicks--;
        // 空闲计时：一有交互就清零
        if (mouseDown || bubbleFrames > 0 || waveTicks > 0) idleTicks = 0;
        else idleTicks++;
        // 坐着歇：无交互约 40 秒；再久一点犯困，犯困就直接躺下
        sitting = idleTicks > 900;
        sleepy = false;   // v22 起不再犯困：睡觉的躺床画面整体撤掉
        if (lieHold > 0) lieHold--;
        if (actHold > 0) actHold--;
        // 脚下的景：一天摸一张，同一天里不来回跳，跨天自己换
        sceneTick++;
        if (sceneTick > 2200)
        {
            sceneTick = 0;
            int want = (int)(DateTime.Now.DayOfYear % 6);
            if (sceneIdx != want) sceneIdx = want;
        }
        // 闲着的时候偶尔自己跳个舞、沏杯茶、坐那儿看会儿电视，让它像个有生活的人
        if (actHold <= 0 && !lying && !sitting && !mouseDown && rnd.Next(1500) == 0)
        {
            actKind = 4 + rnd.Next(3);
            actHold = 210 + rnd.Next(210);
        }
        // 没人理的时候也会自己开口。一直不吭声，就只剩一张会动的图
        if (idleTalkWait <= 0)
        {
            idleTalkWait = 2600 + rnd.Next(2200);
            if (!mouseDown && !lying && bubbleFrames <= 0 && !speaking && !sitting && !hearBusy)
                SelfTalk();
        }
        else idleTalkWait--;
        lying = false;    // v22 起永远不躺下（原来那张床加飘 Z 太假）
        // 只要躺着就是睡着：眼睛必须闭上（气泡一冒，idleTicks 会被清零，不能只靠它判断）
        lieHold = 0;      // v22 起删掉睡一觉，旧计时器一律归零
        // 手动哭一会儿：持续喂情绪，不然三秒就收了
        if (cryHold > 0)
        {
            cryHold--;
            moodKind = 3;
            if (moodTicks < 24) moodTicks = 24;
        }
        if (edgeStay > 0) edgeStay--;
        // 已经走到位了就别继续原地空踏：剩量一次掉 3，约 0.4 秒内收干净；
        // 还在赶路（有目标）时保持正常衰减。
        if (walkTicks > 0) walkTicks -= (walkTargetX == -999999 ? 3 : 1);
        if (walkTicks < 0) walkTicks = 0;
        if (runTicks > 0) runTicks--;
        if (walkTicks <= 0 && runTicks <= 0) moveSpeedPxPerSec = 0f;
        if (thinkTicks > 0) thinkTicks--;
        if (moodTicks > 0) moodTicks--;
        else
        {
            moodWait--;
            if (moodWait <= 0)
            {
                moodWait = 170 + rnd.Next(260);
                // v51：手办自己也有心情了。愉悦值高就更容易高兴，低就容易蔫
                int jk = JoyKind();
                if (rnd.Next(100) < 60) moodKind = jk;
                else moodKind = 1 + rnd.Next(7);
                // 难过的时候给足时间，让它真的哭一会儿，别三秒就停
                moodTicks = moodKind == 3 ? 120 : 74;
            }
        }
        thinkWait--;
        if (thinkWait <= 0)
        {
            thinkWait = 480 + rnd.Next(900);
            thinkTicks = 46;
        }
        // 自主行走：先挑个目标，再一步一步挪过去（坐着歇着的时候不走）
        if (!mouseDown && !sitting)
        {
            if (walkTargetX == -999999)
            {
                walkCounter++;
                if (walkCounter > 200 || (actHold > 0 && ((actKind >= 1 && actKind <= 3) || actKind == 7 || actKind == 8)))
                {
                    walkCounter = 0;
                    try
                    {
                        Rectangle wa = SystemInformation.WorkingArea;
                        int nx, ny;
                        if (rnd.Next(4) == 0)
                        {
                            // 走到屏幕边上贴着站
                            nx = rnd.Next(2) == 0 ? wa.Left + 2 : wa.Right - Width - 2;
                            ny = wa.Top + 4 + rnd.Next(Math.Max(1, wa.Height - Height - 8));
                            edgeStay = 260 + rnd.Next(400);
                        }
                        else
                        {
                            // 整块屏幕随便挑个地方去
                            nx = wa.Left + 4 + rnd.Next(Math.Max(1, wa.Width - Width - 8));
                            ny = wa.Top + 4 + rnd.Next(Math.Max(1, wa.Height - Height - 8));
                        }
                        if (nx < wa.Left + 2) nx = wa.Left + 2;
                        if (nx > wa.Right - Width - 2) nx = wa.Right - Width - 2;
                        if (ny < wa.Top + 2) ny = wa.Top + 2;
                        if (ny > wa.Bottom - Height - 2) ny = wa.Bottom - Height - 2;
                        walkTargetX = nx;
                        walkTargetY = ny;
                    }
                    catch { }
                }
            }
            else
            {
                int curX = Location.X;
                int curY = Location.Y;
                int dxw = walkTargetX - curX;
                int dyw = walkTargetY - curY;
                if (Math.Abs(dxw) <= 2 && Math.Abs(dyw) <= 2)
                {
                    walkTargetX = -999999;
                }
                else
                {
                    int dist = (int)Math.Sqrt(dxw * dxw + dyw * dyw);
                    bool farAway = dist > 240;
                    int spd = farAway ? 7 : 3;
                    int sypMax = farAway ? 4 : 2;
                    // 飞、御剑、骑坐骑都是"赶路"，比走路快，而且是真的一段一段挪过去
                    if (actHold > 0)
                    {
                        if (actKind == 1) { spd = farAway ? 13 : 6; sypMax = farAway ? 9 : 5; }
                        else if (actKind == 2) { spd = farAway ? 15 : 7; sypMax = farAway ? 10 : 5; }
                        else if (actKind == 3) { spd = farAway ? 9 : 4; sypMax = farAway ? 6 : 3; }
                        else if (actKind == 7) { spd = farAway ? 12 : 6; sypMax = farAway ? 7 : 4; }
                        else if (actKind == 8) { spd = farAway ? 14 : 7; sypMax = farAway ? 8 : 4; }
                    }
                    int sxp = Math.Sign(dxw) * Math.Min(spd, Math.Abs(dxw));
                    int syp = Math.Sign(dyw) * Math.Min(sypMax, Math.Abs(dyw));
                    Location = new Point(curX + sxp, curY + syp);
                    walkTicks = 40;
                    // 30 跳/秒：这一跳挪了 sxp 像素 → 每秒挪 |sxp|×30 像素
                    moveSpeedPxPerSec = Math.Abs(sxp) * 30f;
                    runTicks = farAway ? 46 : 0;
                    walkDirX = Math.Sign(dxw);
                    // 走着走着忽然蹦一下，像动画片里那样（飞在天上就别蹦了）
                    if (actKind <= 0 && hopPend <= 0 && rnd.Next(farAway ? 55 : 85) == 0) hopPend = 34;
                }
            }
        }

        // 高兴了原地蹦一下
        if (hopPend > 0) hopPend--;
        else
        {
            hopWait--;
            if (hopWait <= 0)
            {
                hopWait = 240 + rnd.Next(400);
                hopPend = 34;
                moodTicks = Math.Max(moodTicks, 30);
                moodKind = 1;
            }
        }
        // 跨天了就换个模样，不用重启也换（换的时候不吭声，问候交给一天一次的那套逻辑）
        if (dayStamp != DateTime.Today)
        {
            dayStamp = DateTime.Today;
            species = PickDailySpecies();
            // 跨天时也跟着换一套动作，不然重启前后都是同一只
            if (poseKinds != null && poseKinds.Length > 0)
            {
                int pick = poseKinds[DateTime.Now.DayOfYear % poseKinds.Length];
                ApplyPose(pick);
                species = pick;
            }
            MakeDailyIcon();          // 过了零点图标也跟着换
            GreetIfDue(false);
        }
        // 随机闲聊：到点了、没在说话、不是深夜，就说一句
        if (chatMode)
        {
            if (chatCountdown > 0)
            {
                chatCountdown--;
            }
            else if (bubbleFrames <= 0)
            {
                int hh = DateTime.Now.Hour;
                if (hh >= 6 && hh < 23) Say(RandomChatLine());
                ResetChatTimer();
            }
        }
        // 2026-11-18：原来这里每 33ms 无条件重画一次，人站着不动也是 30fps 全量重绘，
        // 在这台 i7-5500U 上白烧 6.6% 单核（实测 10 秒 0.66 秒 CPU）。
        // 现在按"有没有东西在动"分档：走动/说话/气泡/挥手/眨眼/动作/情绪在演 → 满帧；
        // 纯站着 → 每 3 跳才画一次（约 10fps），画面看不出差别，CPU 直接降到三分之一。
        bool busy = mouseDown || walkTargetX != -999999 || bubbleFrames > 0 || waveTicks > 0
                    || speaking || blinkFrames > 0 || actHold > 0 || moodTicks > 0
                    || runTicks > 0 || walkTicks > 0 || thinkTicks > 0 || edgeStay > 0;
        if (busy)
        {
            idlePaintSkip = 0;
            Invalidate();
        }
        else if ((++idlePaintSkip % 3) == 0)
        {
            Invalidate();
        }
    }

    void ForceLayer()
    {
        try { SetLayeredWindowAttributes(this.Handle, ColorTranslator.ToWin32(TransparencyKey), 255, LWA_COLORKEY); } catch { }
    }

    protected override void OnPaint(PaintEventArgs e)
    {
        Stopwatch dgSw = Stopwatch.StartNew();
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
        finally
        {
            dgSw.Stop();
            DgPaint(dgSw.Elapsed.TotalMilliseconds);
        }
    }

    // 悬浮球：缩到 72 像素，只剩一张脸，点一下弹回满身
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

    public void PaintAll(Graphics g, int cw, int ch)
    {
        ForceLayer();
        g.Clear(Color.FromArgb(255, 0, 255));
        float s = Math.Min(cw / (float)W, ch / (float)H);
        if (s <= 0.01f) s = 1f;
        if (diagCount < 3)
        {
            diagCount++;
            try
            {
                File.AppendAllText(Path.Combine(Path.GetTempPath(), "petdiag.txt"),
                    "cw=" + cw + " ch=" + ch + " s=" + s.ToString("F3") + "\r\n");
            }
            catch { }
        }
        if (petMode == 2)
        {
            PaintBall(g, cw, ch);
            return;
        }
        g.TranslateTransform((cw - W * s) / 2f, (ch - H * s) / 2f);
        g.ScaleTransform(s, s);
        g.SmoothingMode = SmoothingMode.AntiAlias;
        g.TextRenderingHint = System.Drawing.Text.TextRenderingHint.AntiAliasGridFit;

        float cx = W / 2f;
        float cy = 127f;
        // 呼吸幅度会慢慢变：约 33 秒一轮强弱，偶尔来一次深吸，不是永远同一口气
        float breatheAmp = 0.78f + 0.22f * (float)Math.Sin(t * 0.19f);
        // 2026-11-22 从 GitHub 上的待机呼吸建模学来的一条：真人呼吸不是等周期正弦——
        // 吸气比呼气短（约 4:6），每次周期 3.6~5.2 秒不等，每口气幅度也小幅浮动。
        // 原来 sin(t*1.5) 是完美等周期的对称正弦，肉眼上像在"晃动"而不是"呼吸"。
        float breathe = BrValue() * breatheAmp;
        float dy = 8.5f * (float)Math.Sin(t * (1.12f + 0.05f * (float)Math.Sin(t * 0.07f))) * (0.9f + 0.1f * breatheAmp);
        float dxs = 2.4f * (float)Math.Sin(t * 0.53);
        if (speaking) dy += 2.4f * (float)Math.Sin(t * (2.0f * (float)Math.PI / (nodBeatMs / 1000.0f)));
        if (moodTicks > 0) { dy -= 1.4f * (float)Math.Sin(t * 6.0); }
        // 躺下：慢慢倒过去，不是一下子翻
        lieAmt += ((lying ? 1f : 0f) - lieAmt) * 0.09f;
        if (lieAmt < 0.004f) lieAmt = 0f;
        if (lying && lieAmt > 0.5f) dy = 0f;   // 躺着就别再上下浮了
        // 生活动作同样淡入淡出：披风、剑、坐骑、茶杯、电视都跟着这个值一起进一起退
        float actTarget = (actHold > 0 && !lying) ? 1f : 0f;
        actAmt += (actTarget - actAmt) * 0.09f;
        if (actAmt > 0.94f) actAmt = 1f;
        if (actAmt < 0.02f)
        {
            actAmt = 0f;
            if (actHold <= 0) actKind = 0;
        }
        cy += dy;
        cx += dxs;
        // 走跑时整只左右换重心、双倍频上下颠：看着是在走，不是原地抖
        if (runTicks > 0 || walkTicks > 0)
        {
            float sp = t * (runTicks > 0 ? 12.0f : 8.4f);
            cx += (runTicks > 0 ? 9.0f : 6.5f) * (float)Math.Sin(sp);
            cy -= (runTicks > 0 ? 5.0f : 3.5f) * (float)Math.Abs(Math.Sin(sp * 2.0));
            // 在场景里真挪位置：跑得快、走得慢，顶到画面边上就掉头
            tripX += tripDir * (runTicks > 0 ? 6.0f : 3.2f);
            if (tripX > 104f) { tripX = 104f; tripDir = -1; }
            if (tripX < -104f) { tripX = -104f; tripDir = 1; }
        }
        else if (lying || lieAmt > 0.05f)
        {
            // 只有要躺下的时候才回到床中间，平时走到哪儿就站哪儿
            tripX *= 0.9f;
            if (Math.Abs(tripX) < 0.5f) tripX = 0f;
        }
        cx += tripX;
        if (moodTicks > 0)
        {
            if (moodKind == 2) cx += 1.8f * (float)Math.Sin(t * 26.0);
            else if (moodKind == 3) cy += 2.3f;
            else if (moodKind == 4) cy -= 2.6f * (float)Math.Abs(Math.Sin(t * 11.0));
        }
        float wantTilt;
        if (runTicks > 0) wantTilt = walkDirX * 13.0f;
        else if (walkTicks > 0) wantTilt = walkDirX * 3.5f;
        else if (speaking) wantTilt = 4.5f;
        else if (moodTicks > 0) wantTilt = -3.2f;
        else wantTilt = 1.4f * (float)Math.Sin(t * 0.37);
        tiltNow += (wantTilt - tiltNow) * 0.12f;
        float rx = 33f * (1f - 0.015f * breathe);
        float ry = 33f * (1f + 0.025f * breathe);

        if (faceCount > 0)
        {
            DrawPicture(g, cx, cy, breathe);
        }        else
        {
            Color body = ColorTranslator.FromHtml(speciesColor[species]);
            Color dark = Darken(body, 0.78f);
            Color light = Lighten(body, 0.55f);

            DrawBody(g, species, cx, cy, rx, ry, body, dark, light);
            DrawFace(g, cx, cy, ry, dark);
        }

        // 气泡浮层改由计时器驱动（见 tick），不在 Paint 里建窗口，避免重入卡死
    }

    // 御剑专属画法：没有整套姿势图的形象，御剑时直接贴这张踩剑姿势。
    // 剑是画在图里的，脚真的踩在剑上，人前倾，不是正面站姿配一把飘着的剑
    void DrawSwordPose(Graphics g, float cx, float cy, float breathe)
    {
        Bitmap sf = null;
        if (swordFlyMap != null && swordFlyMap.ContainsKey(species)) sf = swordFlyMap[species];
        if (sf == null) return;
        float bob = 1.2f * breathe;
        if (lieAmt > 0.02f) bob -= 34f * lieAmt;
        float footY = cy + 68f;
        // 御剑是腾空的：脚离地，还得轻轻上下飘，跟有姿势图那条路一致
        float airY = -22f * actAmt - 4f * actAmt * (float)Math.Sin(t * 1.7);
        DrawScenery(g, cx, footY + bob + airY, sf.Width, sf.Height, t, 5, 1f);
        GraphicsState st = g.Save();
        // 只平移、不旋转不缩放：透明键窗口里一采样就会混出粉紫描边
        g.TranslateTransform((float)Math.Floor(cx), (float)Math.Floor(footY + bob + airY));
        g.SmoothingMode = SmoothingMode.None;
        g.InterpolationMode = InterpolationMode.NearestNeighbor;
        g.PixelOffsetMode = PixelOffsetMode.None;
        int hw = sf.Width / 2;
        g.DrawImage(sf, new Rectangle(-hw, -sf.Height, sf.Width, sf.Height));
        g.Restore(st);
    }

    // 有姿势集时的画法：选一张最贴当前状态的姿势图贴上去，切换时做交叉淡化。
    // 走路、挥手、欢呼、坐下都是图里本来就有的四肢动作，不再靠整张图平移或切条
    // 八帧走路直接上画：一像素对一像素贴，手脚动作全靠这八张图画出来
    // 2026-11-17：三次贝塞尔缓动，参数照搬 Flutter 实现
    // 来源：flutter/flutter · packages/flutter/lib/src/animation/curves.dart
    //   Curves.easeOutCubic = Cubic(0.215, 0.61, 0.355, 1.0)
    //   Curves.easeOutQuint = Cubic(0.23, 1.0, 0.32, 1.0)
    // 做法：按 x 反解 t（牛顿迭代），再取 y，和 Flutter Cubic.transform 同一套算法
    static float BezierAxis(float t, float a, float b)
    {
        float u = 1f - t;
        return 3f * u * u * t * a + 3f * u * t * t * b + t * t * t;
    }
    static float CubicEase(float x, float x1, float y1, float x2, float y2)
    {
        if (x <= 0f) return 0f;
        if (x >= 1f) return 1f;
        float t = x;
        for (int i = 0; i < 8; i++)
        {
            float bx = BezierAxis(t, x1, x2) - x;
            if (Math.Abs(bx) < 1e-4f) break;
            float d = (BezierAxis(t + 1e-4f, x1, x2) - BezierAxis(t - 1e-4f, x1, x2)) / 2e-4f;
            if (Math.Abs(d) < 1e-6f) break;
            t -= bx / d;
            if (t < 0f) t = 0f;
            if (t > 1f) t = 1f;
        }
        return BezierAxis(t, y1, y2);
    }
    static float EaseOutCubic(float x)
    {
        return CubicEase(x, 0.215f, 0.61f, 0.355f, 1.0f);
    }
    static float EaseOutQuint(float x)
    {
        return CubicEase(x, 0.23f, 1.0f, 0.32f, 1.0f);
    }

    void DrawWalkFrames(Graphics g, float cx, float cy, float breathe)
    {
        if (walkFrames == null || walkFrames.Length < 8) return;
        // 步频按真实位移反推：11.6 帧/秒对应 90 像素/秒（3px×30 跳），挪得越快脚频越快，
        // 脚底才不打滑；每跳向目标靠近 18%，起步与停下都是渐变而不是硬切。
        float targetFps = 11.6f * Math.Max(moveSpeedPxPerSec, 6f) / 90f;
        if (runTicks > 0) targetFps = Math.Max(targetFps, 15.0f);
        if (targetFps < 8.5f) targetFps = 8.5f;
        if (targetFps > 20f) targetFps = 20f;
        // 2026-11-22 帧调度：这个平滑系数原本是按 33ms 一帧调的（0.18/帧），换到 60fps 会快 2.8 倍，
        // 起步那一下会变硬。改成按真实帧长归一，以后帧率再变手感也不变
        float dt = t - walkLastT;
        if (dt < 0f || dt > 0.2f) dt = 0.033f;
        walkLastT = t;
        // 2026-11-23 走路：起步还是 0.18/33ms（迈出去那一下不能软），停步改成 0.10——
        // 脚频往回收要慢，收尾才有惯性，不会一停就像被掐住
        float kAcc = (targetFps > walkFpsCur) ? 0.18f : 0.10f;
        float wA = 1f - (float)Math.Pow(1f - kAcc, dt / 0.033f);
        walkFpsCur += (targetFps - walkFpsCur) * wA;
        float fps = walkFpsCur;
        // 相位自己累加，不再用 t×fps：帧率一变，t×fps 会整段跳帧，脚就像被人拽了一下
        // 2026-11-23 帧调度（主攻第2类 Chromium/Skia 合成）：掉帧就丢帧不补帧——
        // 机器卡一下 dt 到 0.1s 时，相位会一次推两格，脚像被拽；单次推进夹在 1.1 格内，
        // 卡完从下一格接着走，宁可慢半拍，也不跳帧
        float step = fps * dt;
        if (step > 1.1f) step = 1.1f;
        walkPhase += step;
        if (walkPhase >= 8f) walkPhase -= 8f * (float)Math.Floor(walkPhase / 8f);
        float ph = walkPhase;
        int fi = (int)ph % 8;
        if (fi < 0) fi += 8;
        Bitmap pb = walkFrames[fi];
        if (pb == null) return;
        // 落地时沉一点、通过位弹一点，和这一帧的姿势对上，才不会像原地抽动
        // 2026-11-17：原来按正弦等速起伏，看着像机械振动。
        // 改成 easeOutSine：脚触地那一下变化最快，往上升时逐渐减速；
        // 触地那一小段再往下压 1 像素，落脚才有重量感。
        float rawBob = Math.Abs((float)Math.Sin(ph * (float)Math.PI / 4f));
        // 2026-11-17 晚：上升段改用 Flutter 的 easeOutCubic（0.215,0.61,0.355,1.0），
        // 起脚快、到顶慢；触地压缩从原来 rawBob<0.10 的硬加 1px（阶跃，落地会"啪"一下）
        // 改成连续曲线 1.2px × easeOutCubic，压得越接近触地越深。
        float riseBob = EaseOutCubic(rawBob);
        float press = rawBob < 0.30f ? (1f - rawBob / 0.30f) : 0f;
        float bob = -3.1f * riseBob + 1.2f * EaseOutQuint(press);
        if (lieAmt > 0.02f) bob -= 34f * lieAmt;

        float footY = cy + 68f;
        float targetH = pb.Height;
        float baseW = pb.Width;
        DrawScenery(g, cx, footY + bob, baseW, targetH, t, sceneIdx, 1f);

        GraphicsState st = g.Save();
        g.TranslateTransform((float)Math.Floor(cx), (float)Math.Floor(footY + bob));
        g.SmoothingMode = SmoothingMode.None;
        g.InterpolationMode = InterpolationMode.NearestNeighbor;
        g.PixelOffsetMode = PixelOffsetMode.None;
        DrawActProps(g, baseW, targetH, false);
        int hw = (int)baseW / 2;
        int hh = (int)targetH;
        Rectangle r = new Rectangle(-hw, -hh, (int)baseW, hh);
        DrawBmpAlpha(g, pb, r, 1f);
        g.Restore(st);
    }

    // 跳舞：借八帧走路那套真手脚动作，按舞蹈节拍来回摆着播（0→7→0），
    // 再叠上整只的左右摇、落拍往下沉。只做整体平移，不切条也不旋转，
    // 免得透明键边缘混出粉紫描边
    void DrawDanceFrames(Graphics g, float cx, float cy, float breathe)
    {
        if (walkFrames == null || walkFrames.Length < 8) return;
        float fps = 11.0f + 4.0f * actAmt;
        float ph = t * fps;
        int s16 = (int)ph % 16;
        if (s16 < 0) s16 += 16;
        int fi = s16 < 8 ? s16 : 15 - s16;   // 来回摆：像踩点踏步，不是一直往前走
        Bitmap pb = walkFrames[fi];
        if (pb == null) return;
        float beat = t * 3.6f;
        float swayX = 9.0f * actAmt * (float)Math.Sin(beat);
        float swayY = -6.0f * actAmt * (float)Math.Abs((float)Math.Sin(beat * 2.0f));
        if (lieAmt > 0.02f) swayY -= 34f * lieAmt;

        float footY = cy + 68f;
        float targetH = pb.Height;
        float baseW = pb.Width;
        DrawScenery(g, cx + swayX, footY + swayY, baseW, targetH, t, 3, 1f);

        GraphicsState st = g.Save();
        g.TranslateTransform((float)Math.Floor(cx + swayX), (float)Math.Floor(footY + swayY));
        g.SmoothingMode = SmoothingMode.None;
        g.InterpolationMode = InterpolationMode.NearestNeighbor;
        g.PixelOffsetMode = PixelOffsetMode.None;
        DrawActProps(g, baseW, targetH, false);
        int hw = (int)baseW / 2;
        int hh = (int)targetH;
        Rectangle r = new Rectangle(-hw, -hh, (int)baseW, hh);
        DrawBmpAlpha(g, pb, r, 1f);
        g.Restore(st);
    }

    void DrawPosePicture(Graphics g, float cx, float cy, float breathe)
    {
        int want = 0;
        if (sitting || (actAmt > 0.25f && actKind == 6)) want = 4;                 // 坐下看电视
        else if (waveTicks > 0) want = 1;                                         // 举手招呼
        else if (runTicks > 0 || walkTicks > 0) want = 2;                         // 迈步走
        else if (actAmt > 0.25f && actKind == 4) want = 3;                        // 跳舞欢呼
        else if (actAmt > 0.25f && actKind == 3) want = 2;
        if (want >= poses.Length) want = 0;
        if (want != poseIdx)
        {
            posePrev = poseIdx;
            poseIdx = want;
            poseFade = 0f;
        }
        if (poseFade < 1f)
        {
            poseFade += 0.16f;
            if (poseFade > 1f) poseFade = 1f;
        }
        if (posePrev >= poses.Length) posePrev = 0;

        bool walking = walkTicks > 0 || runTicks > 0;
        bool travel = walking || (actAmt > 0.25f && (actKind == 1 || actKind == 2 || actKind == 3));
        // 贴图必须一像素对一像素：一旦缩放采样，边缘就会混出半透明，
        // 透明键窗口把它染成一圈粉紫描边。呼吸和迈步改用上下位移来表现
        float sy = 1f;
        float bob = 0f;
        if (walking)
        {
            // 迈步的节奏压在图上：脚步落地时整只往下沉一点，起来时弹一下
            float pp = (float)Math.Sin(t * 8.4f);
            // 2026-11-16 缓动：落地要脆、抬腿要柔。直接取 |sin| 是 V 形尖点，
            // 像被一根线拽着上下；开方后下沉快、回升慢，接近真实落脚。
            float dip = (float)Math.Pow(Math.Abs(pp), 0.72f);
            bob = -dip * 5.2f;
            bob += 1.6f * pp;
        }
        else
        {
            bob = 1.2f * breathe;
        }
        if (lieAmt > 0.02f)
        {
            bob -= 34f * lieAmt;
        }

        float footY = cy + 68f;
        Bitmap pb = poses[poseIdx];
        // 这个形象配了八帧走路：走起来直接换帧，手脚是画出来的
        // 11 帧/秒，八帧一圈约 0.72 秒，正好是正常步速
        if ((walkTicks > 0 || runTicks > 0) && walkFrames != null && walkFrames.Length >= 8)
        {
            int fi = (int)(t * 11.0f) % 8;
            if (fi < 0) fi += 8;
            pb = walkFrames[fi];
        }
        // 御剑：这个形象配了专属的踩剑姿势，就整张换掉——
        // 不再是正面站姿压窄配一把画出来的剑，人是真踩在剑上、身体前倾
        if (actAmt > 0.25f && actKind == 2 && swordFly != null)
        {
            pb = swordFly;
        }
        // 图已经是显示尺寸（152 高），照着它本来的大小贴
        float targetH = pb.Height;
        float baseW = pb.Width;

        int scIdx = sceneIdx;
        if (actAmt > 0.25f)
        {
            if (actKind == 2) scIdx = 5;
            else if (actKind == 1) scIdx = 2;
            else if (actKind == 3) scIdx = 1;
            else if (actKind == 4 || actKind == 5) scIdx = 3;
            else if (actKind == 6) scIdx = 4;
            else if (actKind == 7 || actKind == 8) scIdx = 0;
        }
        DrawScenery(g, cx, footY + bob, baseW, targetH, t, scIdx, 1f);

        GraphicsState st = g.Save();
        // 平移必须落在整像素上：坐标带小数就会让贴图落在半像素上，
        // 四周漏出一圈窗口底色，看着就是粉紫描边
        g.TranslateTransform((float)Math.Floor(cx), (float)Math.Floor(footY + bob));
        // 不再旋转、不再缩放：只要绕着任意角度采样，边缘就会混出半透明，
        // 透明键窗口立刻把它染成粉紫描边。纯平移 + 一像素对一像素最干净
        g.SmoothingMode = SmoothingMode.None;
        g.InterpolationMode = InterpolationMode.NearestNeighbor;
        g.PixelOffsetMode = PixelOffsetMode.None;

        DrawActProps(g, baseW, targetH, false);

        int hw = (int)baseW / 2;
        int hh = (int)targetH;
        // 图本身就是显示尺寸，一像素对一像素贴，不外扩也不缩
        Rectangle r = new Rectangle(-hw, -hh, (int)baseW, hh);
        // 姿势之间不做淡入淡出：透明键窗口里一旦半透明，边缘就会和洋红底色mix出一道粉边
        DrawBmpAlpha(g, pb, r, 1f);
        g.Restore(st);
    }

    void DrawBmpAlpha(Graphics g, Bitmap b, Rectangle r, float alpha)
    {
        if (b == null || alpha <= 0.02f) return;
        // 全不透明的时候直接贴，不要过 ColorMatrix：一旦走混合，
        // 不透明像素也会和窗口的洋红底混一道边，看着就是一圈粉紫描边
        if (alpha >= 0.995f)
        {
            g.DrawImage(b, r);
            return;
        }
        ColorMatrix cm = new ColorMatrix(new float[][] {
            new float[] { 1, 0, 0, 0, 0 },
            new float[] { 0, 1, 0, 0, 0 },
            new float[] { 0, 0, 1, 0, 0 },
            new float[] { 0, 0, 0, alpha, 0 },
            new float[] { 0, 0, 0, 0, 1 }
        });
        ImageAttributes ia = new ImageAttributes();
        ia.SetColorMatrix(cm, ColorMatrixFlag.Default, ColorAdjustType.Bitmap);
        g.DrawImage(b, r, 0, 0, b.Width, b.Height, GraphicsUnit.Pixel, ia);
        ia.Dispose();
    }

    void DrawPicture(Graphics g, float cx, float cy, float breathe)
    {
        if (faceCount <= 0 || faces == null) return;
        // 这个形象已经有整套姿势图：直接换图，手脚是真的动，不是把身体切条推开
        if (poses != null && poses.Length >= 5 && species == poseOwner)
        {
            DrawPosePicture(g, cx, cy, breathe);
            return;
        }
        // 御剑：这个形象没有整套姿势图，但专门配了一张踩剑姿势，就直接按那张画。
        // 不这样的话，8 号这类只有一张立绘的形象御剑时还是正面站着
        if (actAmt > 0.25f && actKind == 2 && swordFlyMap != null
            && swordFlyMap.ContainsKey(species))
        {
            DrawSwordPose(g, cx, cy, breathe);
            return;
        }
        // 配了八帧走路、但没有整套姿势图的形象：走起来直接换成那八帧真动作。
        // 以前这条被"必须有整套姿势图"挡住了，八帧图编进程序却一次没用上，
        // 走起来只是把一张立绘当纸片推着走，手脚看着当然是僵的
        // 跳舞：配了八帧的形象直接播那套手脚动作，配上整只的左右摆和上下弹。
        // 原来的跳舞是把身体切条往外推，看着就是"折叠"，完全不像跳舞
        if (actAmt > 0.25f && actKind == 4 && walkFrames != null && walkFrames.Length >= 8)
        {
            DrawDanceFrames(g, cx, cy, breathe);
            return;
        }
        if ((walkTicks > 0 || runTicks > 0) && walkFrames != null && walkFrames.Length >= 8)
        {
            DrawWalkFrames(g, cx, cy, breathe);
            return;
        }
        Bitmap bmp = faces[species % faceCount];
        if (bmp == null) return;

        // 有真表情图就整张换：小脸上叠画的腮红、泪珠、怒气符在桌面尺寸下必然糊
        int exprKind = 0;   // 0 平常 1 开心 2 生气 3 难过 4 睡着
        if (cryHold > 0) exprKind = 3;
        else if (sleepy || lieHold > 0) exprKind = 4;
        else if (moodTicks > 0 && moodKind > 0)
        {
            if (moodKind == 1) exprKind = 1;
            else if (moodKind == 2) exprKind = 1;   // 2 是「高兴」，以前错配到生气脸，一高兴反而皱眉
            else if (moodKind == 3) exprKind = 0;   // v0.107：难过不再切整图（sad 整图跟立绘差太多，像换了张脸），
                                                    // 改成只走语速 -14% 和低头动作，脸还是同一张
            else if (moodKind == 4) exprKind = 1;   // 4 是「兴奋」，配开心脸才和 +16% 的语速对得上
            // 2026-11-23 表情映射：5 是好奇/来劲，原来落到平常脸，看着像没反应；
            // 借开心那套（挑眉亮眼）比再换一张整图稳，跟 +5% 的语速也对得上
            else if (moodKind == 5) exprKind = 1;
            // 2026-11-22 表情：犯困(moodKind 6) 原来整图换成 sleep 脸，跟立绘差太多像换了张脸。
            // 跟 v0.107 的难过一致——不切整图，只走语速 -9% 和低头眯眼，脸还是同一张
            else if (moodKind == 6) exprKind = 0;
        }
        bool useExpr = false;
        if (UseExprArt && exprKind > 0 && exprMap != null && exprMap.ContainsKey(species))
        {
            Bitmap[] exs = exprMap[species];
            int exi = -1;
            if (exprKind == 1) exi = 0;        // happy
            else if (exprKind == 2) exi = 2;   // angry
            else if (exprKind == 3) exi = 1;   // sad
            else if (exprKind == 4) exi = 3;   // sleep
            if (exs != null && exi >= 0 && exi < exs.Length && exs[exi] != null)
            {
                bmp = exs[exi];
                useExpr = true;
                // 开心这一种要连着动：张嘴、笑到最大、半张、收拢，四帧转一个圈。
                // 一秒九步、六步一圈，约 0.67 秒笑一次，跟真人笑的节奏差不多
                if (exi == 0 && laughMap != null && laughMap.ContainsKey(species))
                {
                    Bitmap[] lf = laughMap[species];
                    if (lf != null && lf.Length == 4 && lf[3] != null)
                    {
                        int ci = ((int)(t * 9.0f)) % 6;
                        if (ci < 0) ci += 6;
                        int li = ci < 2 ? 0 : (ci < 4 ? 1 : (ci < 5 ? 2 : 3));
                        if (lf[li] != null) bmp = lf[li];
                    }
                }
            }
        }

        bool running = runTicks > 0;
        bool walking = walkTicks > 0;
        bool waving = waveTicks > 0;
        float p = (float)Math.Sin(t * 9.0);

        float sy = 1f + 0.016f * breathe;
        float sx = 1f - 0.010f * breathe;
        float bob = 0f;
        // 坐下歇着：明显压矮、变宽，整体往下沉，像一屁股坐在地上
        if (sitting && lieAmt < 0.5f)
        {
            sy *= 0.72f;
            sx *= 1.14f;
            bob += 5.0f;
        }
        // 犯困：比坐着再塌一点，头往下垂
        if (sleepy && lieAmt < 0.5f)
        {
            sy *= 0.90f;
            bob += 3.0f;
        }
        // 看电视：往地上坐一点，身子朝电视那边歪，才像真在看
        if (actAmt > 0.25f && actKind == 6 && lieAmt < 0.5f)
        {
            sy *= 0.78f;
            sx *= 1.06f;
            bob += 10.0f;
        }
        // 骑坐骑：侧着骑才看得出是"骑马"，所以横向压窄成人+兽的侧影，整只往上抬一截
        if (actAmt > 0.25f && actKind == 3 && lieAmt < 0.5f)
        {
            bob -= 26f;
            sy *= 0.90f;
            sx *= 0.64f;
        }
        // 躺下：整个身子压扁贴在床上、头往左靠到枕头那边，脸始终朝前
        // 这样看着是"从侧面看一个人横躺着、脸对着你"，而不是把整只拧过去
        if (lieAmt > 0.02f)
        {
            // 以前压到 0.48 高，整个人成了被拍扁的一张纸；现在只轻压 0.20，
            // 主要靠往下沉一点、往枕头那边挪一点来表达"侧躺"，身形还立得住
            sy *= 1f - 0.20f * lieAmt;
            sx *= 1f + 0.05f * lieAmt;
            bob -= 22f * lieAmt;
            cx -= 34f * lieAmt;
        }
        if (running)
        {
            // 跑：起伏更大、步频更快，像动画片里小跑起来
            sy = 1f + 0.060f * p;
            sx = 1f - 0.048f * p;
            bob = -Math.Abs(p) * 11.0f;
        }
        else if (walking)
        {
            sy = 1f + 0.040f * p;
            sx = 1f - 0.045f * p;
            bob = -Math.Abs(p) * 8.0f;
        }
        if (speaking)
        {
            float p2 = (float)Math.Sin(t * 9.5);
            sx *= 1f + 0.026f * p2;
            sy *= 1f - 0.018f * p2;
        }
        // 赶路的时候侧过身去：横向压窄就显出侧面了，再按前进方向翻个面，身板跟着前倾。
        // 一直是正面直直地挪，看着像在原地踏步，不像在赶路
        bool travel = (running || walking || (actAmt > 0.25f && ((actKind >= 1 && actKind <= 3) || actKind == 7 || actKind == 8)))
                      && !sitting && lieAmt < 0.25f;
        // 看电视也要朝屏幕那边转：屏幕摆在右手边，人就压窄一点、头朝右偏，别对着观众演
        bool watching = (actAmt > 0.25f && actKind == 6) && !sitting && lieAmt < 0.25f;
        float sideDir = (runTicks > 0 || walkTicks > 0) ? (float)tripDir : (walkDirX >= 0 ? 1f : -1f);
        if (watching) sideDir = 1f;
        if (travel || watching) sx *= 0.78f;

        // 人物在窗口里的块头：152 显得人小、脸上细节糊成一片，162 还是偏小——
        // 画布高 205、脚底压在 cy+68=195，162 只占到 43..195，上下都空着一截。
        // v57 提到 188：贴住地面、头顶留 7 像素，整只占满画布，桌面上看得清脸
        float targetH = 188f;
        float ratio = bmp.Width / (float)bmp.Height;
        float baseW = targetH * ratio;
        float footY = cy + 68f;

        // 蹦跳：整只腾空，落地瞬间压扁
        float hopY = 0f;
        if (hopPend > 0)
        {
            float hp = 1f - hopPend / 34f;
            hopY = -26f * (float)Math.Sin(hp * Math.PI);
            if (hp > 0.80f) { sx *= 1.16f; sy *= 0.84f; }
        }

        // 披风飞和御剑是腾空的，脚离地，还得轻轻上下飘
        float airY = 0f;
        if (actAmt > 0.02f && (actKind == 1 || actKind == 2))
            airY = -22f * actAmt - 4f * actAmt * (float)Math.Sin(t * 1.7);
        else if (actAmt > 0.02f && actKind == 3)
        {
            // 骑着走：略微离地，坐骑就在身下；颠一颠像蹄子落地
            airY = -14f * actAmt - 3f * actAmt * Math.Abs((float)Math.Sin(t * 5.2f));
        }

        // 脚下的场景：城市、乡野、海边、花丛，随动作和心情换。
        // 只铺到脚边为止，形状是起伏的一条、顶上渐隐，所以看着是"一小片地"，
        // 不是给桌面贴了一张方框背景
        int scIdx = sceneIdx;
        // 走动时不硬塞城市：就在今天这张景里走，稻田里能看见风吹稻浪
        if (actAmt > 0.25f)
        {
            // 飞行和御剑本身就是在赶路，走路的那一条会把城市盖上来，所以这两条得放在后头
            if (actKind == 2) scIdx = 5;                      // 御剑：仙侠云海
            else if (actKind == 1) scIdx = 2;                 // 披风飞：海边日落
            else if (actKind == 3) scIdx = 1;                 // 骑坐骑：乡野田间
            else if (actKind == 4 || actKind == 5) scIdx = 3; // 跳舞、喝茶：花丛
            else if (actKind == 6) scIdx = 4;                 // 看电视：屋里，台灯加窗
            else if (actKind == 7 || actKind == 8) scIdx = 0; // 滑板、轮滑：城市街头的地砖
        }
        DrawScenery(g, cx, footY + hopY + bob + airY, baseW, targetH, t, scIdx, 1f);

        GraphicsState st = g.Save();
        // 跳舞的整只位移：左右摇 + 落拍下沉，这是"人在动"，不是把身体切条推开
        float danceX = 0f, danceY = 0f, danceRot = 0f;
        if (actAmt > 0.25f && actKind == 4)
        {
            float beat = t * 3.6f;
            danceX = 8f * actAmt * (float)Math.Sin(beat);
            danceY = -5f * actAmt * (float)Math.Abs((float)Math.Sin(beat * 2f));
            danceRot = 4.0f * actAmt * (float)Math.Sin(beat);
        }
        g.TranslateTransform(cx + danceX, footY + hopY + bob + airY + danceY);
        // 赶路时再往前压一点，像侧着身子赶；翻面靠横向取负缩放，连带披风、坐骑一起跟过去
        g.RotateTransform(tiltNow + danceRot + (travel ? sideDir * 4.5f : 0f)
            + (watching ? 18f * sideDir : 0f)
            + ((actAmt > 0.25f && actKind == 3) ? sideDir * 6f : 0f));
        // 躺着不再整只旋转：只在倾斜上收一点，让躺姿稳当
        g.ScaleTransform((travel || watching) ? sx * sideDir : sx, sy);
        // 抽点缩放（NearestNeighbor）会把眼睛、嘴角这些一两像素的细线随机丢掉，脸就糊；
        // 双三次是对邻域加权平均，细线保留得更完整，边缘也更柔
        g.InterpolationMode = InterpolationMode.HighQualityBicubic;
        g.PixelOffsetMode = PixelOffsetMode.HighQuality;

        // 床和被子改到恢复坐标之后再画：那些东西不该跟着人物一起被压扁，
        // 床要是也压扁了就成了纸片，看着不像家具

        // 身后的东西先画：披风、剑、坐骑，这样人压在它们上面才对
        DrawActProps(g, baseW, targetH, false);

        // 全身协调：头稳住，躯干跟着带，两腿左右交替抬落
        // 条数加细一点，边缘才不会是折线；波形用两个频率叠，动作才软
        const int strips = 48;
        float stripH = targetH / strips;
        float imgScale = bmp.Height / targetH;
        float amp = running ? 9.0f : (walking ? 5.4f : 0.62f);
        if (actAmt > 0.02f && actKind == 4) amp += 2.4f * actAmt;   // 跳舞只留一点摆动，大幅切条就是折叠
        float ph = t * (running ? 12.0f : 8.4f);
        if (actAmt > 0.02f && actKind == 4) ph = t * 8.0f;           // 节拍降下来，切条推太快就成抽搐
        float legLift = running ? 13.0f : (walking ? 7.5f : 0f);
        bool stepping = (running || walking || (actAmt > 0.3f && actKind == 4)) && hopPend <= 0;
        // 手臂的张合幅度：走路跑跳最大，站着也有一点，御剑和骑坐骑手要扶着就不摆
        float armAmp = 0f;
        bool handsBusy = (actAmt > 0.25f && (actKind == 2 || actKind == 3 || actKind == 5 || actKind == 7 || actKind == 8));
        if (!handsBusy) armAmp = running ? 9.0f : (walking ? 7.0f : 4.4f);
        if (waving) armAmp = 12.0f;
        if (actAmt > 0.25f && actKind == 4) armAmp = 7.0f;
        // 走路时手臂必须和腿同频反相（左腿抬起时右手往前），不同频整只就像牌子在晃
        float armPh = running ? (ph + (float)Math.PI)
            : (waving ? t * 9.0f : (stepping ? ph + (float)Math.PI : t * 3.2f));

        for (int i = 0; i < strips; i++)
        {
            float fy = (i + 0.5f) / strips;
            // 摆动交给骨链：越靠上叠得越多、相位越晚，头和发尾晚半拍跟上
            float off = amp * BoneSway(fy, ph);
            // 手臂：上半身中段反向摆，用余弦窗口收边，进出没有硬拐角
            if (stepping && fy > 0.38f && fy < 0.63f)
            {
                float w2 = (float)Math.Sin(Math.PI * (fy - 0.38f) / 0.25f);
                // v0.107：原来这段是 2.4*Sin(ph*0.9-0.4)，跟腿不同频（0.9 倍）、还带固定相位，
                // 走快了手臂就在"甩"，像钟摆不跟步子。改成 armAmp 驱动 + armPh（腿的反相），
                // 幅度也跟跑/走/站三档走同一套参数。
                off -= (armAmp * 0.34f) * w2 * (float)Math.Sin(armPh);
            }
            // 招手：只晃上半身
            if (waving && fy < 0.68f)
                off += 9.0f * (0.68f - fy) * (float)Math.Sin(t * 13.0);

            float yy = -targetH + i * stripH;
            float sh = stripH + 1.1f;
            float syp = i * stripH * imgScale;
            float shp = Math.Min(bmp.Height - syp, sh * imgScale);
            if (shp <= 0.5f) continue;

            // 手臂：肩到腰这一段整条轻轻摆，站着不动也有一点摆幅，不然整只像块牌子。
            // 试过把肩到腰切成左右两半分别往外推，躯干中间会裂开一道缝，所以只能整条走
            if (fy > 0.36f && fy < 0.66f && armAmp > 0.1f)
            {
                float w2 = (float)Math.Sin(Math.PI * (fy - 0.36f) / 0.30f);
                if (w2 > 0f) off += armAmp * w2 * (float)Math.Sin(armPh);
            }
            float liftL = 0f, liftR = 0f;
            if (stepping && fy > 0.60f)
            {
                // 左半跟着正弦的前半拍抬、右半跟着后半拍抬，看着就是两条腿在换着踏
                float w = (fy - 0.60f) / 0.40f;
                // 抬落用平方包络，起步和落地都是缓的，不会"啪"一下弹起来
                float sL = 0.5f + 0.5f * (float)Math.Sin(ph);
                float sR = 0.5f + 0.5f * (float)Math.Sin(ph + Math.PI);
                liftL = -legLift * w * sL * sL;
                liftR = -legLift * w * sR * sR;
            }
            if (liftL != 0f || liftR != 0f)
            {
                float hw = baseW / 2f;
                float hbw = bmp.Width / 2f;
                g.DrawImage(bmp,
                    new RectangleF(-baseW / 2f + off, yy + liftL, hw + 1.2f, sh),
                    new RectangleF(0f, syp, hbw + 1f, shp),
                    GraphicsUnit.Pixel);
                g.DrawImage(bmp,
                    new RectangleF(-baseW / 2f + off + hw, yy + liftR, hw, sh),
                    new RectangleF(hbw - 1f, syp, hbw + 1f, shp),
                    GraphicsUnit.Pixel);
            }
            else
            {
                g.DrawImage(bmp,
                    new RectangleF(-baseW / 2f + off, yy, baseW, sh),
                    new RectangleF(0f, syp, bmp.Width, shp),
                    GraphicsUnit.Pixel);
            }
        }

        // 情绪直接画在脸上：位置跟着横切条一起晃，才不会脱开脸
        int fidx = (faceFileIdx != null && species >= 0 && species < faceFileIdx.Length) ? faceFileIdx[species] : species;
        float fxp = (fidx >= 0 && fidx < faceAtX.Length) ? faceAtX[fidx] : 0.50f;
        float fyp = (fidx >= 0 && fidx < faceAtY.Length) ? faceAtY[fidx] : 0.36f;
        float fwp = (fidx >= 0 && fidx < faceAtW.Length) ? faceAtW[fidx] : 0.55f;
        float fOff = amp * BoneSway(fyp, ph);
        if (waving && fyp < 0.68f) fOff += 12.0f * (0.68f - fyp) * (float)Math.Sin(t * 13.0);
        float faceX0 = -baseW / 2f + fxp * baseW + fOff;
        float faceY0 = -targetH + fyp * targetH;
        // 身前的物件：茶杯、电视机、跳舞的音符，画在身体上、脸下面
        DrawActProps(g, baseW, targetH, true);
        // 躺下时身子是压扁的，脸不能跟着压扁，否则五官全糊成一条
        GraphicsState faceSt = g.Save();
        if (lieAmt > 0.02f && sy > 0.2f)
        {
            float fy2 = 1f / sy;
            if (fy2 > 1.58f) fy2 = 1.58f;   // 补一部分就够了，全补回去脸会拉太长
            g.TranslateTransform(faceX0, faceY0);
            g.ScaleTransform(1f, fy2);
            g.TranslateTransform(-faceX0, -faceY0);
        }
        // 已经是真表情图了，就别再往上叠腮红弧线

        // 躺着睡着：不论情绪分支有没有生效，都直接在脸上补一层闭着的眼，
        // 不然位图上原来睁着的大眼珠会一直瞪着
        if (lieAmt > 0.45f && !useExpr)
        {
            float er = baseW * fwp / 2f;
            if (er > 3f)
            {
                float ex = faceX0;
                float ey = faceY0;
                float fw = baseW * fwp;
                float eyo = ey + er * 0.26f;
                // 试过按小范围采样、按高光采样、把这一片图像模糊再贴回来，都有毛病：
                // 花纹脸采到条纹、白脸采到额头、模糊则连同黑眼珠一起糊成大黑块。
                // 最后改成：在这个脸框里统计"主色"，亮度低于阈值的像素（眼珠、眉毛、描线）
                // 直接不参与平均，剩下的就是皮肤/毛色，盖上去自然不显
                float px2lx = baseW / (float)bmp.Width;
                float px2ly = targetH / (float)bmp.Height;
                int rwI = (int)(fw * 1.35f / px2lx);
                int rhI = (int)(fw * 1.05f / px2ly);
                if (rwI < 6) rwI = 6;
                if (rhI < 6) rhI = 6;
                Color sk = SampleFaceColor(bmp, fxp, fyp + 0.03f, rwI, rhI);
                float mw2 = fw * 1.22f;
                float mh2 = fw * 0.58f;
                using (SolidBrush cv = new SolidBrush(Color.FromArgb(242, sk.R, sk.G, sk.B)))
                {
                    g.FillEllipse(cv, ex - mw2 * 0.5f, eyo - mh2 * 0.52f, mw2, mh2);
                }
                // 模糊块上再压两道向下弯的弧，明确是闭着的眼
                using (Pen ep2 = new Pen(Color.FromArgb(210, 48, 52, 66), Math.Max(1.4f, er * 0.09f)))
                {
                    ep2.StartCap = LineCap.Round;
                    ep2.EndCap = LineCap.Round;
                    float eSep = fw * 0.30f;
                    float aw = fw * 0.30f;
                    float ah = fw * 0.20f;
                    g.DrawArc(ep2, ex - eSep - aw * 0.5f, eyo - ah * 0.62f, aw, ah, 12, 156);
                    g.DrawArc(ep2, ex + eSep - aw * 0.5f, eyo - ah * 0.62f, aw, ah, 12, 156);
                }
            }
        }

        // 脸和它的闭眼遮罩都画完了，先把那层反压扁的变换退掉
        g.Restore(faceSt);

        g.Restore(st);

        // 床、枕头、被子都放到恢复坐标之后再画：它们是家具，不该跟着人一起被压扁，
        // 压扁了就像一块纸片。样子照着一张睡前绘本：床头板在左，人横躺着脸朝前，
        // 被子从脖子那儿鼓到床尾，只留脑袋和肩膀在外头
        if (lieAmt > 0.45f)
        {
            float kb = (lieAmt - 0.45f) / 0.55f;
            if (kb > 1f) kb = 1f;
            if (kb < 0f) kb = 0f;
            int aa = (int)(252 * kb);

            float bedY = footY + hopY + bob + airY;      // 床面就垫在脚底下
            float bwd = targetH * 1.62f;
            if (bwd > W - 28f) bwd = W - 28f;
            float bedCx = cx + 60f * lieAmt;              // 人往左挪了，床还在画面中间
            float bx0 = bedCx - bwd * 0.5f;
            float bx1 = bedCx + bwd * 0.5f;
            float bh2 = 24f;

            // 床头板：左端竖起来的那块
            using (SolidBrush hbr = new SolidBrush(Color.FromArgb(aa, 176, 70, 58)))
            {
                g.FillRectangle(hbr, bx0 - 4f, bedY - 54f, 18f, 54f + bh2);
            }
            using (SolidBrush hbr2 = new SolidBrush(Color.FromArgb(aa, 200, 96, 78)))
            {
                g.FillEllipse(hbr2, bx0 - 4f, bedY - 62f, 18f, 16f);
            }

            // 床身：暖色布面
            using (LinearGradientBrush bs = new LinearGradientBrush(
                new RectangleF(bx0, bedY, bwd, bh2),
                Color.FromArgb(aa, 228, 152, 152),
                Color.FromArgb(aa, 194, 110, 114), 90f))
            {
                g.FillRectangle(bs, bx0, bedY, bwd, bh2);
            }
            // 床面上几个小叉花，别看着像一块纯色板
            using (Pen pl = new Pen(Color.FromArgb((int)(aa * 0.50f), 178, 76, 94), 1f))
            {
                for (int i = 0; i < 9; i++)
                {
                    float px2 = bx0 + 12f + (bwd - 24f) * i / 8f;
                    g.DrawLine(pl, px2, bedY + 6f, px2 + 3f, bedY + 10f);
                    g.DrawLine(pl, px2 + 3f, bedY + 6f, px2, bedY + 10f);
                }
            }
            // 床沿一道亮边，把布面和被子分开
            using (Pen pk = new Pen(Color.FromArgb(aa, 244, 200, 194), 2.4f))
            {
                g.DrawLine(pk, bx0 + 2f, bedY + 1.6f, bx1 - 2f, bedY + 1.6f);
            }
            // 床垫：床面下方那一条软垫，比床架浅一点
            using (SolidBrush mat = new SolidBrush(Color.FromArgb(aa, 246, 226, 214)))
            {
                g.FillRectangle(mat, bx0 + 3f, bedY + 3f, bwd - 6f, 7f);
            }
            // 两条床腿
            using (SolidBrush bl = new SolidBrush(Color.FromArgb(aa, 138, 62, 54)))
            {
                g.FillRectangle(bl, bx0 + 8f, bedY + bh2, 7f, 11f);
                g.FillRectangle(bl, bx1 - 15f, bedY + bh2, 7f, 11f);
            }

            // 枕头：浅蓝的，垫在脑袋底下
            using (SolidBrush pil = new SolidBrush(Color.FromArgb(aa, 198, 222, 246)))
            {
                g.FillEllipse(pil, cx - 48f, bedY - 26f, 62f, 19f);
            }
            using (Pen piln = new Pen(Color.FromArgb((int)(aa * 0.45f), 148, 182, 222), 1f))
            {
                g.DrawArc(piln, cx - 48f, bedY - 26f, 62f, 19f, 188f, 164f);
            }

            // 被子：左边从脸下面绕过去，往右鼓成一个大山包，铺到床尾
            // 被子的峰值不能高过脸，不然随机一变形就把整张脸埋进去；
            // 这里按角色脸的实际高度封个顶，峰值最多到脸的眼下为止
            float qyBot = bedY + 9f;
            float qyMid = bedY - 34f;
            float qyTop = bedY - targetH * 0.50f;
            float capY = faceY0 + (baseW * fwp) * 0.62f;
            if (qyTop < capY) qyTop = capY;
            if (qyMid < capY + targetH * 0.10f) qyMid = capY + targetH * 0.10f;
            float qRight = cx + bwd * 0.47f;
            GraphicsPath qp3 = new GraphicsPath();
            PointF q0 = new PointF(cx - 36f, qyBot);
            PointF q1 = new PointF(cx - 38f, qyMid);
            qp3.AddLine(q0, q1);
            qp3.AddBezier(q1,
                new PointF(cx - 26f, qyMid + 2f),
                new PointF(cx - 2f, qyMid),
                new PointF(cx + 18f, qyMid - 2f));
            qp3.AddBezier(new PointF(cx + 18f, qyMid - 2f),
                new PointF(cx + 34f, qyTop + 4f),
                new PointF(cx + bwd * 0.22f, qyTop),
                new PointF(cx + bwd * 0.34f, qyTop + 4f));
            qp3.AddBezier(new PointF(cx + bwd * 0.34f, qyTop + 4f),
                new PointF(cx + bwd * 0.42f, qyTop + 18f),
                new PointF(qRight - 3f, bedY - 16f),
                new PointF(qRight, qyBot));
            qp3.AddLine(new PointF(qRight, qyBot), q0);
            qp3.CloseFigure();

            using (LinearGradientBrush lg = new LinearGradientBrush(
                new RectangleF(cx - 52f, qyTop, qRight - cx + 54f, qyBot - qyTop),
                Color.FromArgb(aa, 174, 210, 246),
                Color.FromArgb(aa, 92, 128, 196), 90f))
            {
                g.FillPath(lg, qp3);
            }
            // 被头翻出来的一截浅边
            using (Pen qn = new Pen(Color.FromArgb(Math.Min(230, aa), 234, 244, 254), 2.6f))
            {
                g.DrawBezier(qn,
                    new PointF(cx - 37f, qyMid),
                    new PointF(cx - 26f, qyMid + 2f),
                    new PointF(cx - 2f, qyMid),
                    new PointF(cx + 18f, qyMid - 2f));
            }
            // 被子外轮廓
            using (Pen qo = new Pen(Color.FromArgb((int)(aa * 0.45f), 70, 100, 162), 1.2f))
            {
                g.DrawPath(qo, qp3);
            }
            // 被面上的星星，跟绘本一个路子
            int[] starX = { 22, 74, 128, 176, 46, 104, 158, 202 };
            int[] starY = { -30, -62, -34, -70, -76, -16, -84, -50 };
            for (int i = 0; i < 8; i++)
            {
                float sxp2 = cx + starX[i];
                float syp2 = bedY + starY[i];
                if (sxp2 < cx - 46f || sxp2 > qRight - 2f) continue;
                if (syp2 < qyTop + 4f || syp2 > qyBot - 3f) continue;
                DrawStar(g, sxp2, syp2, 6.4f, Color.FromArgb(Math.Min(255, aa), 248, 216, 104));
            }
            // 两道褶皱，跟着呼吸起伏一点点
            using (Pen qf = new Pen(Color.FromArgb((int)(aa * 0.55f), 108, 142, 198), 1.3f))
            {
                for (int i = 1; i <= 2; i++)
                {
                    float qxx = cx + bwd * 0.10f * i;
                    float br = (float)Math.Sin(t * 1.9 + i) * 1.6f;
                    g.DrawLine(qf, qxx, qyTop + 18f, qxx + br + 2f, qyBot - 6f);
                }
            }
            qp3.Dispose();
        }

        float topY = footY + hopY + bob - targetH * sy;
        DrawMoodIcon(g, cx + baseW * 0.40f + 4f, topY + 12f);
        // 躺下睡着的时候，头上慢慢飘 Z
        if (lieAmt > 0.55f) DrawSleepZ(g, cx + 12f, footY + 6f);

    }

    // 场景里的小动静：每种景配一种自己的粒子，静态图也能看出是活的
    // 每天换图标：把当天这只形象整只抠出来做成 64×64 的 ico，透明底。
    // 不垫方框也不垫圆盘——桌面显示出来的轮廓就是道自己。
    // exe 内嵌的图标没法天天改，快捷方式的能改
    // 形象图本身是白底，只按 alpha 裁包围盒会裁出一整块白方，
    // 桌面图标就成了白方块。这里从四条边往里泛洪，把连通的近白像素清成透明：
    // 只从边上进，所以肚子、眼白这些被角色包住的白色不会被挖掉
    static Bitmap KnockoutWhite(Bitmap src)
    {
        int w = src.Width, h = src.Height;
        Rectangle rect = new Rectangle(0, 0, w, h);
        int[] px = new int[w * h];
        BitmapData bd = src.LockBits(rect, ImageLockMode.ReadOnly, System.Drawing.Imaging.PixelFormat.Format32bppArgb);
        for (int y = 0; y < h; y++)
        {
            IntPtr row = (IntPtr)((long)bd.Scan0 + y * bd.Stride);
            System.Runtime.InteropServices.Marshal.Copy(row, px, y * w, w);
        }
        src.UnlockBits(bd);

        bool[] white = new bool[w * h];
        for (int i = 0; i < w * h; i++)
        {
            int v = px[i];
            int a = (v >> 24) & 0xFF;
            int b = (v >> 16) & 0xFF, g2 = (v >> 8) & 0xFF, rr = v & 0xFF;
            white[i] = (a > 180 && rr > 231 && g2 > 231 && b > 231);
        }

        bool[] bg = new bool[w * h];
        int[] stk = new int[w * h];
        int top = 0;
        for (int x = 0; x < w; x++) if (white[x]) { bg[x] = true; stk[top++] = x; }
        for (int x = 0; x < w; x++) { int k = (h - 1) * w + x; if (white[k] && !bg[k]) { bg[k] = true; stk[top++] = k; } }
        for (int y = 0; y < h; y++)
        {
            int k = y * w;
            if (white[k] && !bg[k]) { bg[k] = true; stk[top++] = k; }
            int k2 = y * w + w - 1;
            if (white[k2] && !bg[k2]) { bg[k2] = true; stk[top++] = k2; }
        }
        while (top > 0)
        {
            int k = stk[--top];
            int x = k % w, y = k / w;
            if (x + 1 < w) { int nk = k + 1; if (white[nk] && !bg[nk]) { bg[nk] = true; stk[top++] = nk; } }
            if (x > 0) { int nk = k - 1; if (white[nk] && !bg[nk]) { bg[nk] = true; stk[top++] = nk; } }
            if (y + 1 < h) { int nk = k + w; if (white[nk] && !bg[nk]) { bg[nk] = true; stk[top++] = nk; } }
            if (y > 0) { int nk = k - w; if (white[nk] && !bg[nk]) { bg[nk] = true; stk[top++] = nk; } }
        }

        for (int i = 0; i < w * h; i++) if (bg[i]) px[i] = 0;

        Bitmap outb = new Bitmap(w, h, System.Drawing.Imaging.PixelFormat.Format32bppArgb);
        BitmapData bd2 = outb.LockBits(rect, ImageLockMode.WriteOnly, System.Drawing.Imaging.PixelFormat.Format32bppArgb);
        for (int y = 0; y < h; y++)
        {
            IntPtr row = (IntPtr)((long)bd2.Scan0 + y * bd2.Stride);
            System.Runtime.InteropServices.Marshal.Copy(px, y * w, row, w);
        }
        outb.UnlockBits(bd2);
        return outb;
    }

    // 今天这份 ico 已经在就不再重做：重做会连带重写 lnk，Explorer 又要重画一遍图标。
    void EnsureDailyIcon()
    {
        try
        {
            string dir = Path.Combine(Path.GetDirectoryName(Application.ExecutablePath), "icons");
            string today = Path.Combine(dir, "dao_" + DateTime.Today.ToString("yyyyMMdd") + ".ico");
            // 优先用 current.ico：rotate_icon.ps1 换的是它，任务栏要跟桌面图标是同一枚；
            // 只有它不在时才退回当天的存档文件
            string cur = Path.Combine(dir, "current.ico");
            if (File.Exists(cur))
            {
                SetShortcutIcon(cur);
                ApplyFormIcon(cur);
                return;
            }
            if (File.Exists(today))
            {
                SetShortcutIcon(today);   // 文件在就只校准快捷方式，不重写文件
                ApplyFormIcon(today);
                return;
            }
            MakeDailyIcon();
        }
        catch { MakeDailyIcon(); }
    }

    void MakeDailyIcon()
    {
        Bitmap clean = null;
        try
        {
            if (faces == null || faces.Length == 0) return;
            int i = species;
            if (i < 0 || i >= faces.Length) i = 0;
            Bitmap src = faces[i];
            if (src == null) return;
            // 先抠掉白底，包围盒才是角色真实轮廓，图标不会是方块
            clean = KnockoutWhite(src);
            src = clean;

            // 找不透明像素的包围盒，跳过空白边，只留角色本体
            int x0 = src.Width, y0 = src.Height, x1 = -1, y1 = -1;
            int step = (src.Width * src.Height > 400000) ? 2 : 1;
            for (int y = 0; y < src.Height; y += step)
            {
                for (int x = 0; x < src.Width; x += step)
                {
                    if (src.GetPixel(x, y).A > 26)
                    {
                        if (x < x0) x0 = x;
                        if (x > x1) x1 = x;
                        if (y < y0) y0 = y;
                        if (y > y1) y1 = y;
                    }
                }
            }
            if (x1 < 0 || y1 < 0) return;
            int bw = x1 - x0 + 1, bh = y1 - y0 + 1;
            if (bw < 8 || bh < 8) return;
            x0 -= 1; y0 -= 1; bw += 2; bh += 2;            // 留 1px 边，别贴死
            if (x0 < 0) { bw += x0; x0 = 0; }
            if (y0 < 0) { bh += y0; y0 = 0; }
            if (x0 + bw > src.Width) bw = src.Width - x0;
            if (y0 + bh > src.Height) bh = src.Height - y0;

            // 先按最大一档画，再由它缩出小尺寸：这样桌面大图标、任务栏小图标都清楚
            Bitmap iconImg = new Bitmap(256, 256, System.Drawing.Imaging.PixelFormat.Format32bppArgb);
            using (Graphics g2 = Graphics.FromImage(iconImg))
            {
                g2.SmoothingMode = SmoothingMode.AntiAlias;
                g2.InterpolationMode = InterpolationMode.HighQualityBicubic;
                g2.PixelOffsetMode = PixelOffsetMode.HighQuality;
                g2.Clear(Color.Transparent);
                // 等比塞进 248×248，四边留 4px 余地，别贴死边缘
                float sc = Math.Min(248f / bw, 248f / bh);
                int dw = (int)(bw * sc), dh = (int)(bh * sc);
                if (dw < 1) dw = 1;
                if (dh < 1) dh = 1;
                int dx = (256 - dw) / 2, dy = (256 - dh) / 2;
                using (Bitmap cut = src.Clone(new Rectangle(x0, y0, bw, bh), System.Drawing.Imaging.PixelFormat.Format32bppArgb))
                {
                    g2.DrawImage(cut, new Rectangle(dx, dy, dw, dh),
                        new Rectangle(0, 0, cut.Width, cut.Height), GraphicsUnit.Pixel);
                }
            }
            string dir = Path.Combine(Path.GetDirectoryName(Application.ExecutablePath), "icons");
            if (!Directory.Exists(dir)) Directory.CreateDirectory(dir);
            string icoPath = Path.Combine(dir, "dao_" + DateTime.Today.ToString("yyyyMMdd") + ".ico");
            SaveIco(iconImg, icoPath);
            iconImg.Dispose();
            SetShortcutIcon(icoPath);
            ApplyFormIcon(icoPath);
        }
        catch { }
        finally { if (clean != null) { try { clean.Dispose(); } catch { } } }
    }

    // 手写 ico：一张张 PNG 塞进 ICONDIR 里，vista 之后系统直接认。
    // 一档只有 64 的话，桌面大图标和任务栏小图标都是硬放大，边缘会糊；
    // 所以从 256 的母图缩出六档，各视图都拿到尺寸刚好合适的那一张
    static void SaveIco(Bitmap bmp, string path)
    {
        int[] sizes = new int[] { 16, 32, 48, 64, 128, 256 };
        List<byte[]> pngs = new List<byte[]>();
        foreach (int s in sizes)
        {
            using (Bitmap tmp = new Bitmap(s, s, System.Drawing.Imaging.PixelFormat.Format32bppArgb))
            {
                using (Graphics g = Graphics.FromImage(tmp))
                {
                    g.SmoothingMode = SmoothingMode.AntiAlias;
                    g.InterpolationMode = InterpolationMode.HighQualityBicubic;
                    g.PixelOffsetMode = PixelOffsetMode.HighQuality;
                    g.Clear(Color.Transparent);
                    g.DrawImage(bmp, 0, 0, s, s);
                }
                using (MemoryStream ms = new MemoryStream())
                {
                    tmp.Save(ms, System.Drawing.Imaging.ImageFormat.Png);
                    pngs.Add(ms.ToArray());
                }
            }
        }
        int n = pngs.Count;
        using (FileStream fs = new FileStream(path, FileMode.Create, FileAccess.Write))
        {
            fs.Write(new byte[] { 0, 0, 1, 0 }, 0, 4);                    // reserved=0, type=1
            fs.Write(BitConverter.GetBytes((ushort)n), 0, 2);              // 图张数
            uint off = (uint)(6 + 16 * n);
            for (int k = 0; k < n; k++)
            {
                int s = sizes[k];
                byte wb = (byte)(s >= 256 ? 0 : s);                        // 256 要写成 0
                fs.Write(new byte[] { wb, wb, 0, 0 }, 0, 4);                // w,h,颜色数,保留
                fs.Write(BitConverter.GetBytes((ushort)1), 0, 2);          // planes
                fs.Write(BitConverter.GetBytes((ushort)32), 0, 2);         // 32 位带 alpha
                fs.Write(BitConverter.GetBytes((uint)pngs[k].Length), 0, 4);
                fs.Write(BitConverter.GetBytes(off), 0, 4);
                off += (uint)pngs[k].Length;
            }
            for (int k = 0; k < n; k++) fs.Write(pngs[k], 0, pngs[k].Length);
        }
    }

    // 窗口图标也跟着当天那枚走（任务栏、Alt-Tab 读的是 Form.Icon）
    Icon formIco;
    void ApplyFormIcon(string icoPath)
    {
        try
        {
            if (!File.Exists(icoPath)) return;
            Icon old = formIco;
            formIco = new Icon(icoPath);
            this.Icon = formIco;
            if (old != null) { try { old.Dispose(); } catch { } }
        }
        catch { }
    }

    void SetShortcutIcon(string icoPath)
    {
        try
        {
            Type sh = Type.GetTypeFromProgID("WScript.Shell");
            if (sh == null) return;
            object shell = Activator.CreateInstance(sh);
            string desk = Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory);
            string lnk = Path.Combine(desk, "道.lnk");
            if (!File.Exists(lnk)) return;
            object sc = sh.InvokeMember("CreateShortcut", System.Reflection.BindingFlags.InvokeMethod, null, shell, new object[] { lnk });
            string want = icoPath + ",0";
            // 同一个图标就别再 Save：每 Save 一次都会让 Explorer 丢掉缓存重画桌面图标
            object cur = sh.InvokeMember("IconLocation", System.Reflection.BindingFlags.GetProperty, null, sc, null);
            if (cur != null && Convert.ToString(cur) == want) return;
            sh.InvokeMember("IconLocation", System.Reflection.BindingFlags.SetProperty, null, sc, new object[] { want });
            sh.InvokeMember("Save", System.Reflection.BindingFlags.InvokeMethod, null, sc, null);
        }
        catch { }
    }

    void DrawSceneLife(Graphics g, float t, int idx)
    {
        int n = 20;
        switch (idx)
        {
            case 0: // 城市夜景：斜着落的雨丝 + 路面反光抖一下
                {
                    using (Pen rp = new Pen(Color.FromArgb(110, 198, 220, 246), 1f))
                    {
                        for (int i = 0; i < n; i++)
                        {
                            // 上缘往上是被裁掉的透明区，粒子只在实心里落，否则会被键色染色
                            float yy = ((t * 52f + i * 13.7f) % (H - 52f)) + 48f;
                            float xx = ((i * 47.3f) % W) + yy * 0.22f;
                            g.DrawLine(rp, xx, yy, xx - 3.2f, yy + 10f);
                        }
                    }
                    using (SolidBrush gl = new SolidBrush(Color.FromArgb((int)(26 + 16 * (float)Math.Sin(t * 1.6f)), 255, 214, 150)))
                    {
                        g.FillEllipse(gl, W * 0.36f, H * 0.70f, W * 0.30f, H * 0.10f);
                    }
                    // 街上有人路过：远的浅、近的深，从右往左慢慢走，走到头再从右边出来
                    for (int i = 0; i < 3; i++)
                    {
                        float spd = 9f + i * 4.5f;
                        float px = W + 26f - ((t * spd + i * 132f) % (W + 52f));
                        float py = 126f + i * 17f;
                        float ph2 = 15f + i * 4.5f;
                        int pa = 105 + i * 35;
                        using (SolidBrush ps = new SolidBrush(Color.FromArgb(pa, 22, 28, 46)))
                        {
                            g.FillEllipse(ps, px, py - ph2, ph2 * 0.40f, ph2 * 0.40f);              // 头
                            g.FillRectangle(ps, px + 0.8f, py - ph2 * 0.60f, ph2 * 0.28f, ph2 * 0.60f); // 身子
                        }
                    }
                }
                break;
            case 1: // 乡野田间：萤火虫，慢慢上下飘
                {
                    for (int i = 0; i < n; i++)
                    {
                        float ph = t * 0.55f + i * 0.83f;
                        float xx = ((i * 39.7f) % (W - 40f)) + 20f + (float)Math.Sin(ph * 1.3f) * 7f;
                        float yy = H * 0.42f + ((i * 23.1f) % (H * 0.46f)) + (float)Math.Sin(ph) * 6f;
                        int aa = (int)(70 + 60 * Math.Abs((float)Math.Sin(ph * 1.7f)));
                        using (SolidBrush fy = new SolidBrush(Color.FromArgb(aa, 226, 244, 150)))
                        {
                            g.FillEllipse(fy, xx, yy, 3.2f, 3.2f);
                        }
                    }
                    // 风一阵阵从稻田上刮过：一道道亮带往右推，稻叶被吹得歪一下
                    using (Pen waveP = new Pen(Color.FromArgb(52, 255, 255, 214), 2.4f))
                    {
                        for (int i = 0; i < 5; i++)
                        {
                            float ph3 = t * 1.1f + i * 0.72f;
                            float wx = ((t * 26f + i * 82f) % (W + 130f)) - 65f;
                            float wy = 104f + i * 14f + (float)Math.Sin(ph3) * 2.6f;
                            g.DrawLine(waveP, wx, wy, wx + 42f, wy - 3f);
                        }
                    }
                    using (Pen leafP = new Pen(Color.FromArgb(86, 214, 240, 152), 1.1f))
                    {
                        for (int i = 0; i < 14; i++)
                        {
                            float bx = (i * 27.4f) % (W - 10f);
                            float by = 106f + (i % 5) * 12.4f;
                            float sw2 = (float)Math.Sin(t * 1.7f + i * 0.9f) * 3.4f;
                            g.DrawLine(leafP, bx, by + 7f, bx + sw2, by);
                        }
                    }
                }
                break;
            case 2: // 海边日落：浪头白线一明一暗
                {
                    using (Pen wp = new Pen(Color.FromArgb(150, 250, 252, 255), 1.4f))
                    {
                        for (int i = 0; i < 7; i++)
                        {
                            float yy2 = H * 0.66f + i * 5.6f;
                            float off = (t * 18f + i * 26f) % (W + 60f) - 30f;
                            int aa = (int)(70 + 80 * Math.Abs((float)Math.Sin(t * 1.1f + i)));
                            wp.Color = Color.FromArgb(aa, 250, 252, 255);
                            g.DrawLine(wp, off, yy2, off + 34f, yy2 - 1f);
                            g.DrawLine(wp, off + 22f, yy2 + 4f, off + 58f, yy2 + 3.4f);
                        }
                    }
                }
                break;
            case 3: // 花丛：花瓣一片片飘下来，转了半圈
                {
                    for (int i = 0; i < n; i++)
                    {
                        float ph = t * 0.42f + i * 0.61f;
                        float yy = ((t * 12f + i * 11.7f) % (H * 0.62f)) + 56f;
                        float xx = ((i * 41.9f) % (W - 30f)) + 15f + (float)Math.Sin(ph * 2.1f) * 11f;
                        int aa = (int)(150 + 60 * Math.Abs((float)Math.Sin(ph)));
                        Color pc = (i % 2 == 0) ? Color.FromArgb(aa, 255, 214, 232) : Color.FromArgb(aa, 252, 238, 196);
                        using (SolidBrush pb = new SolidBrush(pc))
                        {
                            float rw = 4.4f + (float)Math.Abs(Math.Sin(ph)) * 2.2f;
                            g.FillEllipse(pb, xx, yy, rw, 2.6f);
                        }
                    }
                    // 草丛里两只蝴蝶：一黄一白，翅膀一开一合地飞，路线是绕圈的
                    for (int i = 0; i < 2; i++)
                    {
                        float ph4 = t * 0.82f + i * 2.3f;
                        float bxx = W * 0.50f + (float)Math.Sin(ph4 * 1.15f) * 90f;
                        float byy = 74f + i * 30f + (float)Math.Sin(ph4 * 1.9f) * 17f;
                        float flap = 2.1f + 2.2f * (float)Math.Abs(Math.Sin(t * 9.4f + i * 1.5f));
                        Color bcol = (i == 0) ? Color.FromArgb(206, 255, 208, 116) : Color.FromArgb(206, 252, 250, 246);
                        using (SolidBrush bb = new SolidBrush(bcol))
                        {
                            g.FillEllipse(bb, bxx - flap, byy - 2.4f, flap, 4.8f);
                            g.FillEllipse(bb, bxx + 0.7f, byy - 2.4f, flap, 4.8f);
                            g.FillEllipse(bb, bxx - 0.9f, byy - 0.8f, 1.9f, 3.4f);
                        }
                    }
                }
                break;
            case 4: // 客厅：落地灯的光在轻轻呼吸，窗外零星闪
                {
                    int aa = (int)(22 + 12 * Math.Abs((float)Math.Sin(t * 0.7f)));
                    using (SolidBrush lamp = new SolidBrush(Color.FromArgb(aa, 255, 214, 130)))
                    {
                        g.FillEllipse(lamp, 26f, 44f, 62f, 74f);
                    }
                    for (int i = 0; i < 5; i++)
                    {
                        int sy2 = (int)(50 + 40 * Math.Abs((float)Math.Sin(t * 0.9f + i * 1.3f)));
                        using (SolidBrush st = new SolidBrush(Color.FromArgb(sy2, 220, 232, 255)))
                        {
                            g.FillEllipse(st, 168f + i * 11f, 30f + (i % 3) * 9f, 1.6f, 1.6f);
                        }
                    }
                }
                break;
            default: // 仙侠云海：樱瓣和云影一起慢飘
                {
                    using (SolidBrush cl = new SolidBrush(Color.FromArgb(26, 255, 255, 255)))
                    {
                        float cx2 = ((t * 8f) % (W + 120f)) - 60f;
                        g.FillEllipse(cl, cx2, H * 0.30f, 96f, 22f);
                        g.FillEllipse(cl, cx2 + 130f, H * 0.52f, 118f, 26f);
                    }
                    for (int i = 0; i < 12; i++)
                    {
                        float ph = t * 0.5f + i * 0.9f;
                        float yy = ((t * 10f + i * 14.3f) % (H * 0.60f)) + 58f;
                        float xx = ((i * 53.1f) % (W - 26f)) + 13f + (float)Math.Sin(ph * 1.9f) * 9f;
                        int aa = (int)(150 + 60 * Math.Abs((float)Math.Sin(ph)));
                        using (SolidBrush pet2 = new SolidBrush(Color.FromArgb(aa, 255, 198, 226)))
                        {
                            g.FillEllipse(pet2, xx, yy, 4.0f, 2.4f);
                        }
                    }
                }
                break;
        }
    }

    // 脚下的场景底：一条起伏的地台，顶上渐隐到透明。四种景自己轮换，也会跟动作配：
    // 走跑是城市街头，飞行御剑是海边日落，骑坐骑是乡野田间，闲着是花丛
    void DrawScenery(Graphics g, float cx, float footY, float baseW, float targetH, float t, int idx, float amt)
    {
        // 场景先停用：窗口就是纯透明，只剩形象浮在桌面上。
        // 代码全留着，等场景优化好了把 sceneOn 改回 true 就回来
        if (!sceneOn) return;
        if (amt <= 0.01f) return;
        // 地台钉在窗口中间：人在场景里走动的时候，地不能跟着一起挪
        cx = W / 2f;
        // 有模型画的整幅场景就直接贴上去；原图已按窗口 380x205 预缩好，
        // 一像素对一像素画，不做插值，透明键窗口外沿就不会渗色
        if (idx >= 0 && idx < 6 && sceneImgs[idx] != null)
        {
            // 一像素对一像素贴，不缩放也不平移：边缘是硬 alpha，
            // 一旦插值就会混出半透明像素，透明键立刻把那一圈染成洋红
            g.DrawImage(sceneImgs[idx], 0, 0);
            // 景里自己带的小动静：城市落雨、乡野萤火、海边浪光、花丛花瓣、
            // 客厅电视溢出的光、仙侠飘的樱瓣，让静态图看着在呼吸
            DrawSceneLife(g, t, idx);
            // 屋里那台电视一直开着：屏幕上光影一直在动，有人坐过去看时人再对着它
            if (idx == 4)
            {
                // 客厅电视屏幕上播节目：坐标是量着场景图里的屏幕来的
                RectangleF sr = new RectangleF(292f, 80f, 50f, 31f);
                int g1 = (int)(150 + 80 * (float)Math.Sin(t * 2.6f));
                int g2 = (int)(160 + 70 * (float)Math.Sin(t * 1.9f + 1.4f));
                using (LinearGradientBrush sg = new LinearGradientBrush(
                    sr, Color.FromArgb(255, 116, g1, 236), Color.FromArgb(255, 226, g2, 150), 20f))
                {
                    g.FillRectangle(sg, sr);
                }
                using (SolidBrush sl = new SolidBrush(Color.FromArgb(210, 250, 252, 255)))
                {
                    float ph3 = (t * 0.9f) % 1f;
                    g.FillRectangle(sl, sr.X + 6f, sr.Y + sr.Height * ph3, sr.Width - 12f, 2.2f);
                }
            }
            return;
        }
        float sw = Math.Max(baseW * 1.66f, targetH * 1.12f);
        float sh = targetH * 0.34f;
        float yT = footY - sh;
        float yB = footY + 5f;
        GraphicsPath gp = new GraphicsPath();
        // 一段地面横带：上缘只轻轻起伏、两头略微落下去，看着是脚下的地，
        // 不是浮在空中的小岛
        gp.AddBezier(new PointF(cx - sw * 0.50f, yB),
            new PointF(cx - sw * 0.40f, yT + sh * 0.12f),
            new PointF(cx - sw * 0.24f, yT - sh * 0.02f),
            new PointF(cx - sw * 0.06f, yT + sh * 0.03f));
        gp.AddBezier(new PointF(cx - sw * 0.06f, yT + sh * 0.03f),
            new PointF(cx + sw * 0.10f, yT + sh * 0.07f),
            new PointF(cx + sw * 0.30f, yT + sh * 0.02f),
            new PointF(cx + sw * 0.50f, yT + sh * 0.13f));
        gp.AddLine(new PointF(cx + sw * 0.50f, yT + sh * 0.13f), new PointF(cx + sw * 0.50f, yB));
        gp.AddLine(new PointF(cx + sw * 0.50f, yB), new PointF(cx - sw * 0.50f, yB));
        gp.CloseFigure();

        Color c0, c1;
        switch (idx)
        {
            case 0: c0 = Color.FromArgb(58, 66, 92); c1 = Color.FromArgb(104, 118, 150); break;    // 城市
            case 2: c0 = Color.FromArgb(132, 164, 208); c1 = Color.FromArgb(246, 180, 122); break;  // 海边
            case 3: c0 = Color.FromArgb(152, 194, 132); c1 = Color.FromArgb(212, 230, 172); break;  // 花丛
            case 4: c0 = Color.FromArgb(46, 48, 74); c1 = Color.FromArgb(98, 84, 106); break;      // 屋里
            default: c0 = Color.FromArgb(112, 162, 98); c1 = Color.FromArgb(180, 212, 136); break;  // 乡野
        }
        // 透明键窗口里，抗锯齿的边缘像素是半透明的，会被键色染成一圈紫边，
        // 所以这层地台的填充干脆关掉抗锯齿，边缘硬一点但不发紫
        SmoothingMode smOld = g.SmoothingMode;
        g.SmoothingMode = SmoothingMode.None;
        using (LinearGradientBrush bg2 = new LinearGradientBrush(
            new RectangleF(cx - sw * 0.52f, yT - 2f, sw * 1.04f, sh + 12f),
            Color.FromArgb(c0.R, c0.G, c0.B),
            Color.FromArgb(255, c1.R, c1.G, c1.B), 90f))
        {
            g.FillPath(bg2, gp);
        }
        g.SmoothingMode = smOld;

        GraphicsState sc = g.Save();
        g.SetClip(gp);
        g.SmoothingMode = SmoothingMode.AntiAlias;

        if (idx == 0)
        {
            // 城市：一排高楼剪影，零星亮着的窗；底下一道街面
            for (int i = 0; i < 6; i++)
            {
                float bx = cx - sw * 0.44f + i * sw * 0.155f;
                float bw = sw * 0.115f;
                float bh = sh * (0.40f + 0.34f * ((i * 37) % 5) / 5f);
                using (SolidBrush bb = new SolidBrush(Color.FromArgb(255, 38, 46, 70)))
                {
                    g.FillRectangle(bb, bx, yB - bh - sh * 0.05f, bw, bh);
                }
                using (SolidBrush wb = new SolidBrush(Color.FromArgb(255, 255, 214, 132)))
                {
                    for (int r = 0; r < 3; r++)
                    {
                        for (int c = 0; c < 2; c++)
                        {
                            if ((i + r + c) % 3 == 0) continue;
                            g.FillRectangle(wb, bx + bw * 0.22f + c * bw * 0.40f,
                                yB - bh - sh * 0.05f + bh * 0.16f + r * bh * 0.26f,
                                bw * 0.18f, bh * 0.10f);
                        }
                    }
                }
            }
            // 街面：下半压一条车行道，车道上按车道虚线排白线，路沿立一盏路灯
            using (SolidBrush road = new SolidBrush(Color.FromArgb(255, 62, 66, 78)))
            {
                g.FillRectangle(road, cx - sw * 0.50f, yB - sh * 0.22f, sw, sh * 0.22f + 2f);
            }
            using (SolidBrush das = new SolidBrush(Color.FromArgb(255, 226, 231, 238)))
            {
                for (int i = 0; i < 6; i++)
                {
                    g.FillRectangle(das, cx - sw * 0.46f + i * sw * 0.17f, yB - sh * 0.12f, sw * 0.085f, 2f);
                }
            }
            float lpx = cx + sw * 0.34f;
            using (SolidBrush halo3 = new SolidBrush(Color.FromArgb(255, 255, 226, 158)))
            {
                g.FillEllipse(halo3, lpx - sw * 0.048f, yB - sh * 0.34f, sw * 0.096f, sh * 0.22f);
            }
            using (Pen pole = new Pen(Color.FromArgb(255, 40, 44, 56), 1.8f))
            {
                g.DrawLine(pole, lpx, yB - sh * 0.01f, lpx, yB - sh * 0.46f);
                g.DrawLine(pole, lpx, yB - sh * 0.46f, lpx - sw * 0.032f, yB - sh * 0.44f);
            }
        }
        else if (idx == 1)
        {
            // 乡野：两道远山，前面一畦畦田垄，边上几根稻穗随风点
            using (SolidBrush mb = new SolidBrush(Color.FromArgb(255, 74, 118, 84)))
            {
                g.FillEllipse(mb, cx - sw * 0.30f, yT + sh * 0.34f, sw * 0.34f, sh * 0.42f);
                g.FillEllipse(mb, cx - sw * 0.02f, yT + sh * 0.26f, sw * 0.36f, sh * 0.50f);
            }
            // 一畦畦田垄：深浅交替的横带，远看就是一块块地
            using (SolidBrush fur = new SolidBrush(Color.FromArgb(255, 94, 140, 86)))
            {
                for (int i = 0; i < 4; i++)
                {
                    g.FillRectangle(fur, cx - sw * 0.50f, yB - sh * (0.28f - i * 0.065f), sw, sh * 0.028f);
                }
            }
            using (SolidBrush fur2 = new SolidBrush(Color.FromArgb(255, 158, 194, 122)))
            {
                for (int i = 0; i < 3; i++)
                {
                    g.FillRectangle(fur2, cx - sw * 0.50f, yB - sh * (0.245f - i * 0.065f), sw, sh * 0.016f);
                }
            }
            using (Pen lp = new Pen(Color.FromArgb(255, 120, 166, 104), 1.4f))
            {
                for (int i = 0; i < 7; i++)
                {
                    float lx = cx - sw * 0.42f + i * sw * 0.14f;
                    g.DrawLine(lp, lx, yB - sh * 0.22f, lx + sw * 0.06f, yB - sh * 0.02f);
                }
            }
            using (Pen rr = new Pen(Color.FromArgb(255, 176, 196, 108), 1.6f))
            {
                float sw2 = (float)Math.Sin(t * 1.7f) * 2.2f;
                for (int i = 0; i < 5; i++)
                {
                    float rx = cx - sw * 0.34f + i * sw * 0.17f;
                    float ry = yB - sh * 0.06f;
                    g.DrawLine(rr, rx, ry, rx + sw2, ry - sh * 0.26f);
                    g.DrawLine(rr, rx + sw2, ry - sh * 0.26f, rx + sw2 + 3f, ry - sh * 0.30f);
                    g.DrawLine(rr, rx + sw2, ry - sh * 0.26f, rx + sw2 - 3f, ry - sh * 0.30f);
                }
            }
        }
        else if (idx == 2)
        {
            // 海边：一块落日，底下一片海，两道浪线来回推
            using (SolidBrush sun = new SolidBrush(Color.FromArgb(255, 255, 216, 150)))
            {
                g.FillEllipse(sun, cx - sw * 0.10f, yT + sh * 0.06f, sw * 0.20f, sw * 0.20f);
            }
            using (SolidBrush sea = new SolidBrush(Color.FromArgb(255, 58, 104, 168)))
            {
                g.FillRectangle(sea, cx - sw * 0.50f, yT + sh * 0.32f, sw, sh * 0.36f);
            }
            // 近处是沙滩，沙子压在最下面，海和沙之间留一道浅水线
            using (SolidBrush sand = new SolidBrush(Color.FromArgb(255, 240, 220, 176)))
            {
                g.FillRectangle(sand, cx - sw * 0.50f, yB - sh * 0.32f, sw, sh * 0.32f + 2f);
            }
            using (SolidBrush wet = new SolidBrush(Color.FromArgb(255, 176, 202, 216)))
            {
                g.FillRectangle(wet, cx - sw * 0.50f, yB - sh * 0.32f, sw, sh * 0.035f);
            }
            using (Pen wv = new Pen(Color.FromArgb(255, 206, 232, 250), 1.6f))
            {
                for (int k = 0; k < 2; k++)
                {
                    float yy = yB - sh * 0.36f + k * sh * 0.09f;
                    float phw = t * 2.2f + k * 1.4f;
                    PointF[] pts = new PointF[13];
                    for (int i = 0; i < 13; i++)
                    {
                        float px3 = cx - sw * 0.46f + sw * 0.92f * i / 12f;
                        pts[i] = new PointF(px3, yy + (float)Math.Sin(phw + i * 0.7f) * 2.4f);
                    }
                    g.DrawLines(wv, pts);
                }
            }
        }
        else if (idx == 4)
        {
            // 屋里：木地板几条缝，墙上一扇小窗，窗外有月亮星星，旁边一盏台灯透着暖光
            float fl = yB - sh * 0.30f;
            using (SolidBrush flb = new SolidBrush(Color.FromArgb(255, 118, 90, 76)))
            {
                g.FillRectangle(flb, cx - sw * 0.50f, fl, sw, yB - fl + 2f);
            }
            using (Pen fwl = new Pen(Color.FromArgb(255, 144, 112, 94), 1.2f))
            {
                for (int i = 1; i <= 3; i++)
                {
                    float yy2 = fl + (yB - fl) * i / 4f;
                    g.DrawLine(fwl, cx - sw * 0.50f, yy2, cx + sw * 0.50f, yy2);
                }
            }
            // 台灯：先铺一片暖光，再立杆、扣灯罩
            float lx = cx - sw * 0.31f;
            using (SolidBrush halo = new SolidBrush(Color.FromArgb(255, 255, 226, 168)))
            {
                g.FillEllipse(halo, lx - sw * 0.058f, yT + sh * 0.02f, sw * 0.116f, sh * 0.56f);
            }
            using (SolidBrush lamp = new SolidBrush(Color.FromArgb(255, 218, 160, 88)))
            {
                g.FillRectangle(lamp, lx - 1.6f, yT + sh * 0.14f, 3.2f, sh * 0.44f);
                g.FillPolygon(lamp, new PointF[] {
                    new PointF(lx - sw * 0.052f, yT + sh * 0.15f),
                    new PointF(lx + sw * 0.052f, yT + sh * 0.15f),
                    new PointF(lx + sw * 0.030f, yT + sh * 0.02f),
                    new PointF(lx - sw * 0.030f, yT + sh * 0.02f) });
            }
            // 窗往中间靠：地台上沿是个弧，太靠边那块已经在地台外面了，画出来会被裁掉
            float wx = cx + sw * 0.05f;
            float wy = yT + sh * 0.09f;
            float ww = sw * 0.17f, wh = sh * 0.30f;
            using (SolidBrush wbg = new SolidBrush(Color.FromArgb(255, 32, 38, 68)))
            {
                g.FillRectangle(wbg, wx, wy, ww, wh);
            }
            using (SolidBrush mb = new SolidBrush(Color.FromArgb(255, 246, 240, 182)))
            {
                g.FillEllipse(mb, wx + ww * 0.30f, wy + wh * 0.16f, ww * 0.36f, wh * 0.34f);
                for (int i = 0; i < 3; i++)
                {
                    float stx = wx + ww * (0.12f + 0.30f * i);
                    float sty = wy + wh * (0.74f - 0.18f * i);
                    g.FillEllipse(mb, stx, sty, 2.2f, 2.2f);
                }
            }
            using (Pen wf = new Pen(Color.FromArgb(255, 206, 196, 174), 1.6f))
            {
                g.DrawRectangle(wf, wx, wy, ww, wh);
                g.DrawLine(wf, wx + ww * 0.5f, wy, wx + ww * 0.5f, wy + wh);
                g.DrawLine(wf, wx, wy + wh * 0.5f, wx + ww, wy + wh * 0.5f);
            }
        }
        else
        {
            using (Pen gr = new Pen(Color.FromArgb(255, 96, 150, 92), 1.6f))
            {
                for (int i = 0; i < 9; i++)
                {
                    float gx = cx - sw * 0.44f + i * sw * 0.11f;
                    float gh = sh * (0.12f + 0.06f * ((i * 29) % 4));
                    float bend = (float)Math.Sin(t * 1.5f + i) * 2f;
                    g.DrawBezier(gr, new PointF(gx, yB), new PointF(gx + bend, yB - gh * 0.5f),
                        new PointF(gx - bend, yB - gh * 0.8f), new PointF(gx + bend, yB - gh));
                }
            }
            Color[] petal = { Color.FromArgb(246, 138, 160), Color.FromArgb(252, 210, 120), Color.FromArgb(190, 158, 236) };
            for (int i = 0; i < 6; i++)
            {
                float fx2 = cx - sw * 0.36f + i * sw * 0.145f;
                float fy2 = yB - sh * (0.10f + 0.05f * ((i * 17) % 3));
                Color pc = petal[i % 3];
                using (SolidBrush pb = new SolidBrush(Color.FromArgb(255, pc.R, pc.G, pc.B)))
                {
                    for (int k = 0; k < 5; k++)
                    {
                        float ang = (float)(k * Math.PI * 2 / 5);
                        g.FillEllipse(pb, fx2 + (float)Math.Cos(ang) * 3.2f - 2.4f,
                            fy2 + (float)Math.Sin(ang) * 3.2f - 2.4f, 4.8f, 4.8f);
                    }
                }
                using (SolidBrush cc = new SolidBrush(Color.FromArgb(255, 250, 238, 170)))
                {
                    g.FillEllipse(cc, fx2 - 2f, fy2 - 2f, 4f, 4f);
                }
            }
            for (int i = 0; i < 2; i++)
            {
                float bx2 = cx - sw * 0.22f + i * sw * 0.40f + (float)Math.Sin(t * 0.9f + i * 2f) * sw * 0.10f;
                float by2 = yT + sh * 0.26f + (float)Math.Sin(t * 1.6f + i) * sh * 0.06f;
                float flap = Math.Abs((float)Math.Sin(t * 7.4f + i * 1.2f));
                using (SolidBrush bf = new SolidBrush(Color.FromArgb(255, 252, 190, 96)))
                {
                    g.FillEllipse(bf, bx2 - 5f, by2 - 3f * flap, 4.6f, 7f * flap + 1f);
                    g.FillEllipse(bf, bx2 + 0.6f, by2 - 3f * flap, 4.6f, 7f * flap + 1f);
                }
            }
        }

        g.Restore(sc);
        gp.Dispose();
    }

    // 生活动作的配件：披风、飞剑、坐骑画在身体后面；音符、茶杯、电视画在身前
    // 全部跟着 actAmt 淡入淡出，进出都不会突然闪出来
    void DrawActProps(Graphics g, float baseW, float targetH, bool front)
    {
        float a = actAmt;
        if (a < 0.02f || actKind <= 0) return;
        float half = baseW / 2f;
        // 道具尺度按身高算，不按图的宽度算：恐龙、剑客这类竖长条形象身体只有几十像素宽，
        // 按宽度算披风就细成一根带子，电视也小得看不见
        float hf = targetH * 0.64f;
        float slide = (1f - a) * 20f;
        int na = (int)(255 * a);
        if (na > 255) na = 255;

        if (!front)
        {
            // 飞：披风撤了，脚下给一层被风托着的气流。人还是离地飘着的，
            // 只是不再背一块假红布
            if (actKind == 1 && !UseCape)
            {
                using (SolidBrush air = new SolidBrush(Color.FromArgb((int)(78 * a), 206, 232, 255)))
                {
                    g.FillEllipse(air, -targetH * 0.28f, -4f, targetH * 0.56f, 9f);
                }
                using (Pen wpen = new Pen(Color.FromArgb((int)(140 * a), 232, 244, 255), 1.1f))
                {
                    for (int wi = 0; wi < 3; wi++)
                    {
                        float wx0 = -targetH * 0.18f + wi * 9f;
                        float wy0 = 2f + wi * 2f;
                        float phW = t * 4f + wi;
                        g.DrawBezier(wpen, new PointF(wx0, wy0),
                            new PointF(wx0 - 12f, wy0 + 3f + (float)Math.Sin(phW) * 1.2f),
                            new PointF(wx0 - 20f, wy0 + 5f - (float)Math.Sin(phW) * 1.0f),
                            new PointF(wx0 - 28f, wy0 + 6f));
                    }
                }
            }
            if (actKind == 1 && UseCape)
            {
                if (capeWind != null)
                {
                    // 被风吹的披风：领口贴在肩上，布身往身后甩，飞行时才像"披着披风在飞"
                    float cw2 = targetH * 1.30f;
                    float ch2 = cw2 * capeWind.Height / (float)capeWind.Width;
                    // 位置完全不动：人物本身飞行时会上下飘，披风跟着动就够了，
                    // 贴图自己再位移就会整块跳，看着像哆嗦
                    float lipX = -targetH * 0.02f;
                    float lipY = -targetH * 0.78f + slide * 0.4f;
                    InterpolationMode imBak = g.InterpolationMode;
                    PixelOffsetMode poBak = g.PixelOffsetMode;
                    g.InterpolationMode = InterpolationMode.NearestNeighbor;
                    g.PixelOffsetMode = PixelOffsetMode.Half;
                    GraphicsState stW = g.Save();
                    // 领口在贴图左端，镜像过来就变成朝身后（坐标已跟着人物朝向翻转过）
                    g.TranslateTransform(lipX, lipY);
                    g.ScaleTransform(-1f, 1f);
                    // 布面被风吹：把披风按竖条切开，越靠下摆错得越多，
                    // 整块布就一鼓一鼓地飘；不是整张图平移（那才是哆嗦）
                    int nStrip = 10;
                    float wobAmp = 3.4f + 1.8f * (float)Math.Sin(t * 2.2f);
                    for (int si = 0; si < nStrip; si++)
                    {
                        float u0 = si / (float)nStrip;
                        float ph = t * 2.8f - u0 * 5.2f;
                        float off = (float)Math.Sin(ph) * wobAmp * u0;
                        RectangleF srcR = new RectangleF(
                            capeWind.Width * u0, 0f,
                            capeWind.Width / nStrip, capeWind.Height);
                        RectangleF dstR = new RectangleF(
                            cw2 * u0, off, cw2 / nStrip + 1.2f, ch2);
                        g.DrawImage(capeWind, dstR, srcR, GraphicsUnit.Pixel);
                    }
                    g.Restore(stW);
                    g.InterpolationMode = imBak;
                    g.PixelOffsetMode = poBak;
                    return;
                }
                if (capeImg != null)
                {
                    // 贴图版：肩线搭在肩上，下摆波浪是画好的
                    // 宽要盖过身体两侧一点点，太高就会把脚也罩住，比例得按身高和身宽分别配
                    // 原来按 1.25 倍身高铺，套在剑客这种瘦长角色身上就宽出一大圈，读成一对翅膀；
                    // 收到 0.80 倍身高，肩线从 -0.58 起算，刚好搭在肩上、不顶到头顶
                    float cpw = Math.Max(baseW * 1.30f, targetH * 0.80f);
                    float cph = targetH * 0.80f;
                    float ctop = -targetH * 0.58f + slide * 0.4f;
                    // 位置固定不动：以前给这里叠过一个 1.8px 的来回正弦，人物自己已经在晃，
                    // 贴图再叠一层就成了肉眼看到的"哆嗦"，布料感要靠画好的下摆形态，不靠往复平移
                    if (!dbgCape)
                    {
                        dbgCape = true;
                        try
                        {
                            File.AppendAllText(Path.Combine(AppDir(), "AI日志.txt"),
                                "CAPE a=" + a.ToString("0.00") + " baseW=" + baseW.ToString("0.0") + " targetH=" + targetH.ToString("0.0")
                                + " cpw=" + cpw.ToString("0.0") + " cph=" + cph.ToString("0.0") + " ctop=" + ctop.ToString("0.0")
                                + " img=" + capeImg.Width + "x" + capeImg.Height + "\r\n");
                        }
                        catch { }
                    }
                    InterpolationMode imBak2 = g.InterpolationMode;
                    PixelOffsetMode poBak2 = g.PixelOffsetMode;
                    g.InterpolationMode = InterpolationMode.NearestNeighbor;
                    g.PixelOffsetMode = PixelOffsetMode.Half;
                    g.DrawImage(capeImg, new RectangleF(-cpw * 0.5f, ctop, cpw, cph));
                    g.InterpolationMode = imBak2;
                    g.PixelOffsetMode = poBak2;
                    return;
                }
                // 披风：一整块从两肩垂到脚踝的斗篷，中间被人挡着，两侧和底边露出来
                // 分开画两片会像翅膀，一整块才像个披风
                float pw = Math.Max(targetH * 0.62f, baseW * 0.95f);
                // 领口落在肩上，别顶到头顶，不然会支起一个尖像帽子
                float shY = -targetH * 0.54f + slide * 0.4f;
                float wl = targetH * 0.54f;
                float wv = (float)Math.Sin(t * 4.4);
                float wv2 = (float)Math.Sin(t * 3.1 + 0.6);
                GraphicsPath cp = new GraphicsPath();
                // 肩这一端就得有宽度：要是从中间一个点往下张，两侧露出来的就是两片三角，
                // 读成翅膀；等宽收下去才是"背后一整块布"垂到脚。
                // 但也不能太宽，太宽就成了两把扇子，收在身体轮廓外一点点刚好
                PointF lt = new PointF(-pw * 0.42f, shY);
                PointF rt = new PointF(pw * 0.42f, shY);
                PointF lb = new PointF(-pw * 0.78f + wv * 3f, shY + wl * 0.96f);
                PointF rb = new PointF(pw * 0.78f - wv * 3f, shY + wl * 0.96f);
                // 左肩到左脚，外侧几乎竖直，飞行时被风带得往外飘一点
                cp.AddBezier(lt,
                    new PointF(-pw * 0.60f, shY + wl * 0.30f),
                    new PointF(-pw * 0.76f, shY + wl * 0.70f), lb);
                // 底边：三个起伏要够大，才看得出下摆被风掀起
                cp.AddBezier(lb,
                    new PointF(-pw * 0.46f, shY + wl * 1.16f + wv * 7f),
                    new PointF(-pw * 0.14f, shY + wl * 0.86f - wv2 * 6f),
                    new PointF(0f, shY + wl * 0.98f + wv * 5f));
                cp.AddBezier(new PointF(0f, shY + wl * 0.98f + wv * 5f),
                    new PointF(pw * 0.14f, shY + wl * 0.86f + wv2 * 6f),
                    new PointF(pw * 0.46f, shY + wl * 1.16f - wv * 7f), rb);
                // 右脚回到右肩
                cp.AddBezier(rb,
                    new PointF(pw * 0.76f, shY + wl * 0.70f),
                    new PointF(pw * 0.60f, shY + wl * 0.30f), rt);
                // 肩线：从脖子后面横过去。得抬起来一点，让两边在头顶两侧露出一个搭肩的弧，
                // 光靠两条竖布中间被身体全挡住，看着还是两片分开的旗子
                cp.AddBezier(rt,
                    new PointF(pw * 0.34f, shY - targetH * 0.085f),
                    new PointF(-pw * 0.34f, shY - targetH * 0.085f), lt);
                cp.CloseFigure();
                using (LinearGradientBrush cg = new LinearGradientBrush(
                    new RectangleF(-pw * 1.1f, shY, pw * 2.2f, wl + 14f),
                    Color.FromArgb(na, 250, 86, 92),
                    Color.FromArgb(na, 150, 10, 28), 90f))
                {
                    g.FillPath(cg, cp);
                }
                // 金色滚边：红披风在红壁纸上会糊成一片，得有个亮边才看得出形状
                using (Pen cgld = new Pen(Color.FromArgb(na, 255, 208, 118), 1.7f))
                {
                    g.DrawPath(cgld, cp);
                }
                // 两侧各一道里衬褶皱，布才不呆
                using (Pen cfo = new Pen(Color.FromArgb((int)(na * 0.32f), 255, 168, 170), 1.2f))
                {
                    for (int sgn = -1; sgn <= 1; sgn += 2)
                    {
                        g.DrawBezier(cfo,
                            new PointF(sgn * pw * 0.26f, shY + wl * 0.10f),
                            new PointF(sgn * pw * 0.70f + wv * 2f, shY + wl * 0.42f),
                            new PointF(sgn * pw * 0.86f + wv2 * 2f, shY + wl * 0.72f),
                            new PointF(sgn * pw * 0.88f, shY + wl * 0.92f));
                    }
                }
                cp.Dispose();
                // 肩上两颗领扣
                using (SolidBrush kk = new SolidBrush(Color.FromArgb(na, 250, 210, 120)))
                {
                    g.FillEllipse(kk, -pw * 0.22f - 3f, shY - 3f, 6f, 6f);
                    g.FillEllipse(kk, pw * 0.22f - 3f, shY - 3f, 6f, 6f);
                }
                // 布尾：左右各甩一条，被风掀到身后，带子越往尖越窄、末梢还打个卷
                for (int sgn = -1; sgn <= 1; sgn += 2)
                {
                    float x0 = sgn * pw * 0.30f;
                    float y0 = shY + wl * 0.14f;
                    float x1 = sgn * pw * 0.70f;
                    float y1 = y0 + wl * 0.09f + wv2 * 5f;
                    float x2 = sgn * pw * 1.00f;
                    float y2 = y1 + wl * 0.15f + wv * 8f;
                    float th0 = targetH * 0.055f;
                    GraphicsPath band = new GraphicsPath();
                    band.AddBezier(new PointF(x0, y0),
                        new PointF(x1 * 0.90f, y0 + targetH * 0.02f),
                        new PointF(x1, y1), new PointF(x2, y2));
                    band.AddBezier(new PointF(x2, y2),
                        new PointF(x2 - sgn * targetH * 0.04f, y2 + targetH * 0.04f),
                        new PointF(x2 - sgn * targetH * 0.11f, y2 - targetH * 0.01f),
                        new PointF(x2 - sgn * targetH * 0.09f, y2 - targetH * 0.05f));
                    band.AddBezier(new PointF(x2 - sgn * targetH * 0.09f, y2 - targetH * 0.05f),
                        new PointF(x1 * 0.94f, y1 + th0 * 0.4f),
                        new PointF(x1 * 0.60f, y0 + th0),
                        new PointF(x0, y0 + th0));
                    band.CloseFigure();
                    using (LinearGradientBrush bg3 = new LinearGradientBrush(
                        new RectangleF(Math.Min(0f, x2) - 4f, y0 - 4f, Math.Abs(x2) * 2f + 8f, Math.Abs(y2 - y0) + 20f),
                        Color.FromArgb(na, 244, 72, 84), Color.FromArgb(na, 150, 10, 28), 45f))
                    {
                        g.FillPath(bg3, band);
                    }
                    using (Pen bgld = new Pen(Color.FromArgb(na, 255, 208, 118), 1.5f))
                    {
                        g.DrawPath(bgld, band);
                    }
                    band.Dispose();
                }
                // 兜帽边：头后面露出一圈红，别人才看得出这是披着披风，
                // 不然两侧两块布很容易被认成扇子或翅膀
                float hdW = pw * 1.00f;
                float hdH = targetH * 0.30f;
                float hdY = shY - targetH * 0.12f;
                using (SolidBrush hood = new SolidBrush(Color.FromArgb(na, 230, 62, 72)))
                {
                    g.FillEllipse(hood, -hdW * 0.5f, hdY - hdH * 0.5f, hdW, hdH);
                }
                using (Pen hdp = new Pen(Color.FromArgb(na, 255, 206, 116), 1.6f))
                {
                    g.DrawArc(hdp, -hdW * 0.5f, hdY - hdH * 0.5f, hdW, hdH, 186f, 168f);
                }
                // 领口：肩上横一道金边，把两边连起来
                using (Pen collar = new Pen(Color.FromArgb(na, 255, 208, 118), 2.6f))
                {
                    g.DrawLine(collar, -pw * 0.40f, shY + 1f, pw * 0.40f, shY + 1f);
                }
            }
            else if (actKind == 2)
            {
                // 有贴图时改成在人物前面画（踩着剑才看得见），这里直接跳过
                if (swordImg != null) return;
                // 这个形象有整套御剑姿势图（剑就在图里），这里不能再画一把，会变成两把剑
                if (swordFly != null) return;
                // 御剑：脚下一柄横着的剑，剑身带流光，剑尖朝前
                float gy = 13f + slide;
                float len = targetH * 0.86f;
                float th = 4.4f;
                // 剑身：细长，靠前收成尖，中间一道高光；下面垫一层浅影让它像浮着
                GraphicsPath sp = new GraphicsPath();
                sp.AddPolygon(new PointF[] {
                    new PointF(-len * 0.32f, gy - th),
                    new PointF(len * 0.38f, gy - th * 0.52f),
                    new PointF(len * 0.50f, gy),
                    new PointF(len * 0.38f, gy + th * 0.52f),
                    new PointF(-len * 0.32f, gy + th) });
                using (LinearGradientBrush sb = new LinearGradientBrush(
                    new RectangleF(-len * 0.4f, gy - th - 1f, len, th * 2f + 2f),
                    Color.FromArgb(na, 248, 251, 255),
                    Color.FromArgb(na, 118, 148, 196), 0f))
                {
                    g.FillPath(sb, sp);
                }
                using (Pen sout = new Pen(Color.FromArgb(na, 84, 104, 148), 1.1f))
                {
                    g.DrawPath(sout, sp);
                }
                using (Pen mid = new Pen(Color.FromArgb(na, 255, 255, 255), 1.2f))
                {
                    g.DrawLine(mid, -len * 0.28f, gy - th * 0.20f, len * 0.42f, gy - th * 0.06f);
                }
                // 剑格：金色横过，比剑身粗一圈
                using (SolidBrush gb2 = new SolidBrush(Color.FromArgb(na, 228, 178, 74)))
                {
                    g.FillPolygon(gb2, new PointF[] {
                        new PointF(-len * 0.40f, gy - 7.6f),
                        new PointF(-len * 0.30f, gy - 7.6f),
                        new PointF(-len * 0.30f, gy + 7.6f),
                        new PointF(-len * 0.40f, gy + 7.6f) });
                }
                // 剑柄：铜色，柄尾一颗红玉
                using (SolidBrush hb = new SolidBrush(Color.FromArgb(na, 168, 118, 74)))
                {
                    g.FillRectangle(hb, -len * 0.52f, gy - 3.4f, len * 0.13f, 6.8f);
                }
                using (SolidBrush gem = new SolidBrush(Color.FromArgb(na, 240, 84, 96)))
                {
                    g.FillEllipse(gem, -len * 0.57f, gy - 3.8f, 7.6f, 7.6f);
                }
                // 剑气：两道往后拖的淡青流线
                using (Pen hl = new Pen(Color.FromArgb(na, 150, 214, 236), 1.6f))
                {
                    for (int i = 0; i < 2; i++)
                    {
                        float off2 = 6f + i * 5f;
                        float wv = (float)Math.Sin(t * 6.2 + i) * 2.2f;
                        g.DrawLine(hl, -len * 0.55f - off2, gy - 1f + wv, -len * 0.55f - off2 - 16f, gy - 3f + wv);
                    }
                }
                sp.Dispose();
            }
            else if (actKind == 3)
            {
                // 骑坐骑：身下一匹矮脚小兽，四条腿交替倒腾，尾巴左右甩
                // 骑坐骑：身子只比人略宽一点，太宽就成了个大坐垫把人裹住
                // 人物横向被压窄过，坐骑按反比放宽，视觉上才比人宽出一圈
                float my = 10f + slide;
                // 以前按 1.55 倍身高画，宽得像一张大坐垫把整个人裹进去；
                // 收到 1.05 倍、矮一点，才像一匹驮着人的矮脚兽
                float mw = targetH * 1.05f;
                float mh = targetH * 0.36f;
                int ma = (int)(na * 0.95f);
                using (SolidBrush mb = new SolidBrush(Color.FromArgb(ma, 196, 158, 116)))
                {
                    g.FillEllipse(mb, -mw * 0.5f, my - mh, mw, mh);
                }
                using (SolidBrush msh = new SolidBrush(Color.FromArgb(ma, 172, 132, 94)))
                {
                    g.FillEllipse(msh, -mw * 0.5f, my - mh * 0.62f, mw * 0.44f, mh * 0.60f);
                }
                // 脑袋伸到右前方
                using (SolidBrush mhd = new SolidBrush(Color.FromArgb(ma, 206, 170, 128)))
                {
                    g.FillEllipse(mhd, mw * 0.28f, my - mh * 1.16f, mw * 0.26f, mh * 0.50f);
                }
                // 四条腿：按正弦交替抬落
                using (Pen lp = new Pen(Color.FromArgb(ma, 158, 116, 82), 2.4f))
                {
                    for (int i = 0; i < 4; i++)
                    {
                        float lx = -mw * 0.32f + (i % 2) * mw * 0.60f;
                        float ph2 = t * 11f + i * 1.6f;
                        float lift = -Math.Abs((float)Math.Sin(ph2)) * 4.5f;
                        g.DrawLine(lp, lx, my - 3f + lift, lx + (float)Math.Sin(ph2) * 2f, my + 7f + lift);
                    }
                }
                // 尾巴
                using (Pen tp = new Pen(Color.FromArgb(255, 138, 98, 64), 2.6f))
                {
                    float tw = (float)Math.Sin(t * 3.4) * 5f;
                    g.DrawBezier(tp,
                        new PointF(-mw * 0.46f, my - mh * 0.72f),
                        new PointF(-mw * 0.64f, my - mh * 0.44f + tw),
                        new PointF(-mw * 0.72f, my - mh * 0.94f + tw),
                        new PointF(-mw * 0.62f, my - mh * 1.26f + tw));
                }
                using (SolidBrush eb = new SolidBrush(Color.FromArgb(255, 44, 36, 30)))
                {
                    g.FillEllipse(eb, mw * 0.40f, my - mh * 1.12f, 3.6f, 3.6f);
                    g.FillEllipse(eb, mw * 0.50f, my - mh * 1.12f, 3.6f, 3.6f);
                }
                // 一对耳朵，别让它就是个圆球
                using (SolidBrush ear = new SolidBrush(Color.FromArgb(255, 172, 132, 94)))
                {
                    g.FillEllipse(ear, mw * 0.30f, my - mh * 1.42f, mw * 0.09f, mh * 0.20f);
                    g.FillEllipse(ear, mw * 0.44f, my - mh * 1.44f, mw * 0.09f, mh * 0.20f);
                }
            }
            else if (actKind == 7)
            {
                // 滑板：脚下一块板，四个小轮，板身滑起来轻轻晃
                float bLen = targetH * 0.60f;
                float by3 = 4f + slide;
                float wob = (float)Math.Sin(t * 3.2) * 1.6f;
                GraphicsPath bp2 = new GraphicsPath();
                bp2.AddBezier(new PointF(-bLen * 0.52f, by3 - 3f),
                    new PointF(-bLen * 0.20f, by3 - 6f + wob),
                    new PointF(bLen * 0.20f, by3 - 6f + wob),
                    new PointF(bLen * 0.52f, by3 - 3.4f + wob * 1.4f));
                bp2.AddBezier(new PointF(bLen * 0.52f, by3 - 3.4f + wob * 1.4f),
                    new PointF(bLen * 0.20f, by3 - 1.4f + wob),
                    new PointF(-bLen * 0.20f, by3 - 1.4f + wob),
                    new PointF(-bLen * 0.52f, by3 - 3f));
                bp2.CloseFigure();
                using (SolidBrush bb2 = new SolidBrush(Color.FromArgb(255, 242, 138, 52)))
                {
                    g.FillPath(bb2, bp2);
                }
                using (Pen bl = new Pen(Color.FromArgb(255, 68, 48, 34), 1.6f))
                {
                    g.DrawPath(bl, bp2);
                }
                bp2.Dispose();
                using (SolidBrush wh = new SolidBrush(Color.FromArgb(255, 248, 250, 254)))
                {
                    for (int i = 0; i < 4; i++)
                    {
                        float wx4 = -bLen * 0.36f + (i % 2) * bLen * 0.72f;
                        g.FillEllipse(wh, wx4, by3 + 2.4f, 6.2f, 6.2f);
                    }
                }
            }
            else if (actKind == 8)
            {
                // 轮滑：脚下两只鞋，每只一串小轮，轮子在地上排开
                using (SolidBrush bk = new SolidBrush(Color.FromArgb(255, 46, 96, 168)))
                {
                    g.FillEllipse(bk, -baseW * 0.33f, 0f + slide, baseW * 0.32f, 8f);
                    g.FillEllipse(bk, baseW * 0.01f, 0f + slide, baseW * 0.32f, 8f);
                }
                using (SolidBrush wh2 = new SolidBrush(Color.FromArgb(255, 248, 250, 254)))
                {
                    for (int e = 0; e < 2; e++)
                    {
                        float ex = e == 0 ? -baseW * 0.32f : baseW * 0.02f;
                        for (int k = 0; k < 4; k++)
                        {
                            g.FillEllipse(wh2, ex + k * baseW * 0.065f, 6f + slide, 5.4f, 5.4f);
                        }
                    }
                }
                using (Pen glow2 = new Pen(Color.FromArgb((int)(na * 0.55f), 255, 214, 120), 1.2f))
                {
                    float rr2 = (float)Math.Sin(t * 3.0) * 3f;
                    g.DrawLine(glow2, -baseW * 0.42f, 6f + slide + rr2, -baseW * 0.35f, 6f + slide + rr2);
                }
            }
        }
        else
        {
            if (actKind == 2 && swordImg != null)
            {
                // 御剑贴图：画在人前面，人站在剑上才看得出来；剑尖朝行进方向，脚下拖两道剑气
                // 剑要横着托在脚底：太长会顶出窗口，太厚就成了块木板，人像站在悬浮板上
                float slw = targetH * 1.12f;
                float slh = slw * swordImg.Height / (float)swordImg.Width * 1.18f;
                float scy = slh * 0.5f - 12f + slide * 0.4f;
                g.InterpolationMode = InterpolationMode.NearestNeighbor;
                g.PixelOffsetMode = PixelOffsetMode.Half;
                g.DrawImage(swordImg, new RectangleF(-slw * 0.5f, scy - slh * 0.5f, slw, slh));
                float qq = (float)Math.Sin(t * 5.2) * 3f;
                // 剑气用实色且关抗锯齿：透明键窗口里半透明和抗锯齿边一律混成洋红
                SmoothingMode smOld = g.SmoothingMode;
                g.SmoothingMode = SmoothingMode.None;
                using (Pen qg = new Pen(Color.FromArgb(na, 206, 238, 248), 2f))
                {
                    g.DrawLine(qg, -slw * 0.30f, scy + slh * 0.78f + qq, slw * 0.30f, scy + slh * 0.78f + qq);
                    g.DrawLine(qg, -slw * 0.24f, scy + slh * 0.96f - qq, slw * 0.26f, scy + slh * 0.96f - qq);
                }
                g.SmoothingMode = smOld;
            }
            else if (actKind == 4)
            {
                // 跳舞：脑袋两侧飘音符，跟着节拍往上走
                for (int i = 0; i < 3; i++)
                {
                    float pr = (t * 0.55f + i * 0.36f) % 1f;
                    float nx = -hf * 0.92f + i * hf * 0.92f + (float)Math.Sin(t * 2.2 + i) * 4f;
                    float ny = -targetH * 0.72f - pr * targetH * 0.26f;
                    int av = (int)(na * (1f - pr) * 0.9f);
                    if (av < 8) continue;
                    Color nc = i == 0 ? Color.FromArgb(av, 232, 96, 132)
                             : (i == 1 ? Color.FromArgb(av, 96, 176, 232) : Color.FromArgb(av, 236, 186, 72));
                    using (SolidBrush nb = new SolidBrush(nc))
                    {
                        g.FillEllipse(nb, nx, ny + 11f, 9f, 7.6f);
                    }
                    using (Pen np2 = new Pen(nc, 2.2f))
                    {
                        g.DrawLine(np2, nx + 7.6f, ny + 13f, nx + 7.6f, ny);
                        g.DrawLine(np2, nx + 7.6f, ny, nx + 15f, ny + 4f);
                    }
                }
            }
            else if (actKind == 5)
            {
                // 喝咖啡：杯子放在右手位置，杯把朝身体一侧，再画一只小手扣在把上，
                // 端起、放下走一个周期，才看得出"握着喝一口"的过程
                float cw2 = targetH * 0.20f;
                float ch2 = targetH * 0.19f;
                float ph = (t * 1.05f) % 1f;
                float lift = (float)Math.Sin(ph * Math.PI);
                float cxp = Math.Max(hf * 0.28f, baseW * 0.32f) + slide * 0.3f;
                float cyp = -targetH * 0.30f - lift * targetH * 0.34f + slide * 0.4f;
                // 杯身：上宽下窄的梯形，白瓷
                PointF[] cb = new PointF[] {
                    new PointF(cxp + cw2 * 0.04f, cyp + 1.6f),
                    new PointF(cxp + cw2 * 0.96f, cyp + 1.6f),
                    new PointF(cxp + cw2 * 0.86f, cyp + ch2),
                    new PointF(cxp + cw2 * 0.14f, cyp + ch2) };
                GraphicsPath cupb = new GraphicsPath();
                cupb.AddPolygon(cb);
                using (SolidBrush cup = new SolidBrush(Color.FromArgb(na, 250, 249, 246)))
                {
                    g.FillPath(cup, cupb);
                }
                using (Pen cupo = new Pen(Color.FromArgb(na, 96, 122, 158), 1.2f))
                {
                    g.DrawPath(cupo, cupb);
                }
                cupb.Dispose();
                // 杯口一圈深蓝边，里面是咖啡
                using (SolidBrush rim2 = new SolidBrush(Color.FromArgb(na, 236, 241, 248)))
                {
                    g.FillEllipse(rim2, cxp + cw2 * 0.02f, cyp - ch2 * 0.10f, cw2 * 0.96f, ch2 * 0.28f);
                }
                using (SolidBrush cof = new SolidBrush(Color.FromArgb(na, 78, 50, 32)))
                {
                    g.FillEllipse(cof, cxp + cw2 * 0.10f, cyp - ch2 * 0.04f, cw2 * 0.80f, ch2 * 0.20f);
                }
                using (Pen rim = new Pen(Color.FromArgb(na, 96, 122, 158), 1.1f))
                {
                    g.DrawEllipse(rim, cxp + cw2 * 0.02f, cyp - ch2 * 0.10f, cw2 * 0.96f, ch2 * 0.28f);
                }
                // 杯把：朝身体那一侧（左边），手扣在上面
                using (Pen hd = new Pen(Color.FromArgb(na, 250, 249, 246), 2.0f))
                {
                    g.DrawArc(hd, cxp - cw2 * 0.30f, cyp + ch2 * 0.22f, cw2 * 0.40f, ch2 * 0.54f, 62f, 236f);
                }
                using (Pen hd2 = new Pen(Color.FromArgb(na, 96, 122, 158), 1.0f))
                {
                    g.DrawArc(hd2, cxp - cw2 * 0.30f, cyp + ch2 * 0.22f, cw2 * 0.40f, ch2 * 0.54f, 62f, 236f);
                }
                // 小手：一小团扣在杯把外面，颜色取身体相近的浅色
                using (SolidBrush hand = new SolidBrush(Color.FromArgb(na, 233, 226, 205)))
                {
                    g.FillEllipse(hand, cxp - cw2 * 0.46f, cyp + ch2 * 0.26f, cw2 * 0.30f, ch2 * 0.34f);
                }
                using (Pen hando = new Pen(Color.FromArgb(na, 178, 166, 138), 1.0f))
                {
                    g.DrawEllipse(hando, cxp - cw2 * 0.46f, cyp + ch2 * 0.26f, cw2 * 0.30f, ch2 * 0.34f);
                }
                for (int i = 0; i < 3; i++)
                {
                    float pr = (t * 0.60f + i * 0.34f) % 1f;
                    // 热气不能再走半透明：透明键窗口里半透明像素会混成洋红，只留实色浅线条
                    int av = na;
                    float sx2 = cxp + cw2 * (0.30f + i * 0.22f);
                    float sy2 = cyp - ch2 * 0.14f - pr * targetH * 0.20f;
                    using (Pen st2 = new Pen(Color.FromArgb(av, 208, 220, 236), 1.1f))
                    {
                        g.DrawBezier(st2,
                            new PointF(sx2, sy2),
                            new PointF(sx2 + 2.2f, sy2 - 4.5f),
                            new PointF(sx2 - 2.2f, sy2 - 9f),
                            new PointF(sx2 + (float)Math.Sin(t * 1.6f + i) * 1.2f, sy2 - 13f));
                    }
                }
            }
            else if (actKind == 6 && sceneImgs[4] == null)
            {
                // 看电视：身前一台电视，屏上是会动的光影。四角做圆，不做成硬方框
                // 屋里那张家用客厅场景自带电视，这里就只当兜底（场景图缺失时才自己画一台）
                float tvw = Math.Max(targetH * 0.46f, baseW * 0.42f);
                float tvh = targetH * 0.30f;
                float tvx = Math.Max(hf * 0.34f, baseW * 0.24f);
                float tvy = -targetH * 0.40f + slide;
                float rr2 = tvh * 0.26f;
                GraphicsPath tpath = new GraphicsPath();
                tpath.AddArc(tvx, tvy, rr2 * 2f, rr2 * 2f, 180f, 90f);
                tpath.AddArc(tvx + tvw - rr2 * 2f, tvy, rr2 * 2f, rr2 * 2f, 270f, 90f);
                tpath.AddArc(tvx + tvw - rr2 * 2f, tvy + tvh - rr2 * 2f, rr2 * 2f, rr2 * 2f, 0f, 90f);
                tpath.AddArc(tvx, tvy + tvh - rr2 * 2f, rr2 * 2f, rr2 * 2f, 90f, 90f);
                tpath.CloseFigure();
                using (SolidBrush tvb = new SolidBrush(Color.FromArgb((int)(na * 0.92f), 44, 50, 64)))
                {
                    g.FillPath(tvb, tpath);
                }
                // 屏幕：蓝紫光来回扫，像真在播东西
                float scr = tvh * 0.18f;
                RectangleF sr = new RectangleF(tvx + scr, tvy + scr, tvw - scr * 2f, tvh - scr * 2f);
                int g1 = (int)(140 + 90 * (float)Math.Sin(t * 2.6f));
                int g2 = (int)(160 + 80 * (float)Math.Sin(t * 1.9f + 1.4f));
                using (LinearGradientBrush sg = new LinearGradientBrush(
                    sr, Color.FromArgb(na, 116, g1, 236), Color.FromArgb(na, 226, g2, 150), 20f))
                {
                    g.FillRectangle(sg, sr);
                }
                // 屏幕上一道扫过的亮纹，代表画面在变
                using (SolidBrush sl = new SolidBrush(Color.FromArgb((int)(na * 0.55f), 250, 252, 255)))
                {
                    float ph3 = (t * 0.9f) % 1f;
                    g.FillRectangle(sl, sr.X + sr.Width * 0.12f, sr.Y + sr.Height * ph3, sr.Width * 0.76f, 1.6f);
                }
                using (Pen tout = new Pen(Color.FromArgb((int)(na * 0.60f), 118, 132, 156), 1f))
                {
                    g.DrawPath(tout, tpath);
                }
                using (Pen leg = new Pen(Color.FromArgb((int)(na * 0.80f), 70, 78, 94), 1.6f))
                {
                    g.DrawLine(leg, tvx + tvw * 0.30f, tvy + tvh, tvx + tvw * 0.24f, tvy + tvh + 3.5f);
                    g.DrawLine(leg, tvx + tvw * 0.70f, tvy + tvh, tvx + tvw * 0.76f, tvy + tvh + 3.5f);
                }
                // 顶上两支小天线，一眼就看得出是台电视机
                using (Pen ant = new Pen(Color.FromArgb((int)(na * 0.85f), 70, 78, 94), 1.4f))
                {
                    g.DrawLine(ant, tvx + tvw * 0.40f, tvy, tvx + tvw * 0.28f, tvy - tvh * 0.32f);
                    g.DrawLine(ant, tvx + tvw * 0.60f, tvy, tvx + tvw * 0.72f, tvy - tvh * 0.32f);
                }
                tpath.Dispose();
            }
        }
    }

    // 睡着的 Z：三个大小渐大的 Z，往斜上方飘再淡掉
    void DrawSleepZ(Graphics g, float x, float y)
    {
        for (int i = 0; i < 3; i++)
        {
            float pr = (t * 0.42f + i * 0.34f) % 1f;
            int al = (int)(215 * (1f - pr));
            if (al <= 6) continue;
            float zx = x + pr * 26f;
            float zy = y - pr * 34f;
            float zs = 3.4f + i * 1.1f + pr * 2.2f;
            using (Pen zp = new Pen(Color.FromArgb(al, 96, 126, 174), 1.3f))
            {
                zp.StartCap = LineCap.Round;
                zp.EndCap = LineCap.Round;
                g.DrawLine(zp, zx, zy, zx + zs, zy);
                g.DrawLine(zp, zx + zs, zy, zx, zy + zs);
                g.DrawLine(zp, zx, zy + zs, zx + zs, zy + zs);
            }
        }
    }

    // 被面上的小星星：八个尖的星形，比画方块柔和
    void DrawStar(Graphics g, float x, float y, float r, Color c)
    {
        float ri = r * 0.34f;
        PointF[] pts = new PointF[] {
            new PointF(x, y - r),
            new PointF(x + ri, y - ri),
            new PointF(x + r, y),
            new PointF(x + ri, y + ri),
            new PointF(x, y + r),
            new PointF(x - ri, y + ri),
            new PointF(x - r, y),
            new PointF(x - ri, y - ri)
        };
        using (SolidBrush sb = new SolidBrush(c))
        {
            g.FillPolygon(sb, pts);
        }
    }

    // 把情绪直接画在脸上：腮红 / 眼泪 / 怒气 / 闭眼 / 惊讶
    // 从脸下方的像素取一个平均肤色，用来盖住原来画上去的眼睛
    // 取一块脸区域的"主色"：亮度太低的像素（眼珠、眉毛、深色描线）不参与平均，
    // 剩下的就是皮肤或毛色本身，用来盖眼睛不会在脸上留一块斑
    Color SampleFaceColor(Bitmap src, float nfx, float nfy, int rw, int rh)
    {
        Color fallback = Color.FromArgb(232, 226, 212);
        if (src == null) return fallback;
        try
        {
            int cx = (int)(src.Width * nfx);
            int cy = (int)(src.Height * nfy);
            int x0 = Math.Max(0, cx - rw / 2);
            int x1 = Math.Min(src.Width - 1, cx + rw / 2);
            int y0 = Math.Max(0, cy - rh / 2);
            int y1 = Math.Min(src.Height - 1, cy + rh / 2);
            long rr = 0, gg = 0, bb = 0;
            int nn = 0;
            for (int y = y0; y <= y1; y += 2)
            {
                for (int x = x0; x <= x1; x += 2)
                {
                    Color c = src.GetPixel(x, y);
                    if (c.A < 60) continue;
                    float lum = c.R * 0.30f + c.G * 0.59f + c.B * 0.11f;
                    if (lum < 78f) continue;             // 眼珠和黑描线不要
                    rr += c.R; gg += c.G; bb += c.B; nn++;
                }
            }
            if (nn == 0) return fallback;
            return Color.FromArgb((int)(rr / nn), (int)(gg / nn), (int)(bb / nn));
        }
        catch { return fallback; }
    }

    Color SampleSkin(Bitmap src, float nfx, float nfy)
    {
        Color fallback = Color.FromArgb(224, 218, 202);
        if (src == null) return fallback;
        try
        {
            int px = (int)(src.Width * nfx);
            int py = (int)(src.Height * (nfy + 0.045f));
            int rr = 0, gg = 0, bb = 0, nn = 0;
            for (int dx = -3; dx <= 3; dx++)
            {
                for (int dy = -3; dy <= 3; dy++)
                {
                    int xx = px + dx, yy = py + dy;
                    if (xx < 0 || yy < 0 || xx >= src.Width || yy >= src.Height) continue;
                    Color c = src.GetPixel(xx, yy);
                    if (c.A < 60) continue;
                    rr += c.R; gg += c.G; bb += c.B; nn++;
                }
            }
            if (nn == 0) return fallback;
            return Color.FromArgb(rr / nn, gg / nn, bb / nn);
        }
        catch { return fallback; }
    }

    // 2026-11-18：头顶只留 z Z（犯困）、音符（说话）、问号（思考）三个文字符号。
    // 程序画的笑脸/哭脸、泪滴、圆泡简笔表情、招手画的手，连同 DrawFaceExpr / DrawTear / DrawFaceBubble
    // 和手机端 face()/tear() 一起删掉——表情只走整张表情立绘与姿势动作，脸上不贴任何线稿。

    void DrawMoodIcon(Graphics g, float x, float y)
    {
        float bob = 3.4f * (float)Math.Sin(t * 3.6);


        // 犯困眯眼：头顶冒 z Z
        if (sleepy)
        {
            float zt = (float)Math.Sin(t * 2.2);
            using (Font fz = new Font("Microsoft YaHei", 12f, FontStyle.Bold))
            using (SolidBrush bz = new SolidBrush(Color.FromArgb(190, 116, 126, 156)))
            {
                g.DrawString("z", fz, bz, x - 6f, y + 4f + zt * 3.0f);
                g.DrawString("Z", fz, bz, x - 1f, y - 9f + zt * 3.0f);
            }
            return;
        }

        if (speaking)
        {
            using (Font f = new Font("Microsoft YaHei", 15f, FontStyle.Bold))
            using (SolidBrush b = new SolidBrush(Color.FromArgb(86, 136, 214)))
            {
                SizeF sz = g.MeasureString("\u266a", f);
                g.DrawString("\u266a", f, b, x - sz.Width / 2f, y - sz.Height + bob);
            }
            return;
        }
        // 情绪已经画在脸上，头顶不再重复挂气泡
        if (moodTicks > 0 && moodKind > 0) return;
        if (thinkTicks > 0)
        {
            using (Font f = new Font("Microsoft YaHei", 15f, FontStyle.Bold))
            using (SolidBrush b = new SolidBrush(Color.FromArgb(118, 128, 150)))
            {
                SizeF sz = g.MeasureString("?", f);
                g.DrawString("?", f, b, x - sz.Width / 2f, y - sz.Height + bob);
            }
        }
    }



    Color Darken(Color c, float k) { return Color.FromArgb(c.A, (int)(c.R * k), (int)(c.G * k), (int)(c.B * k)); }
    Color Lighten(Color c, float k)
    {
        int r = (int)(c.R + (255 - c.R) * k);
        int gg = (int)(c.G + (255 - c.G) * k);
        int b = (int)(c.B + (255 - c.B) * k);
        return Color.FromArgb(c.A, Math.Min(255, r), Math.Min(255, gg), Math.Min(255, b));
    }

    void DrawBody(Graphics g, int sp, float cx, float cy, float rx, float ry, Color body, Color dark, Color light)
    {
        using (SolidBrush bb = new SolidBrush(body))
        using (Pen pd = new Pen(dark, 1.6f))
        {
            switch (sp)
            {
                case 0: // 橘猫
                    {
                        // 耳朵
                        PointF[] e1 = { new PointF(cx - rx * 0.72f, cy - ry * 0.62f), new PointF(cx - rx * 0.28f, cy - ry * 0.98f), new PointF(cx - rx * 0.15f, cy - ry * 0.55f) };
                        PointF[] e2 = { new PointF(cx + rx * 0.72f, cy - ry * 0.62f), new PointF(cx + rx * 0.28f, cy - ry * 0.98f), new PointF(cx + rx * 0.15f, cy - ry * 0.55f) };
                        g.FillPolygon(bb, e1); g.DrawPolygon(pd, e1);
                        g.FillPolygon(bb, e2); g.DrawPolygon(pd, e2);
                        g.FillEllipse(bb, cx - rx, cy - ry, rx * 2, ry * 2);
                        g.DrawEllipse(pd, cx - rx, cy - ry, rx * 2, ry * 2);
                        // 条纹
                        using (SolidBrush st = new SolidBrush(Color.FromArgb(70, dark)))
                        {
                            g.FillEllipse(st, cx - 5, cy - ry * 0.72f, 10, ry * 0.5f);
                            g.FillEllipse(st, cx - 20, cy - ry * 0.5f, 7, ry * 0.36f);
                            g.FillEllipse(st, cx + 13, cy - ry * 0.5f, 7, ry * 0.36f);
                        }
                        // 胡须
                        using (Pen pwh = new Pen(Color.FromArgb(120, 90, 70), 1f))
                        {
                            g.DrawLine(pwh, cx - 30, cy + 4, cx - 46, cy - 1);
                            g.DrawLine(pwh, cx - 30, cy + 9, cx - 46, cy + 11);
                            g.DrawLine(pwh, cx + 30, cy + 4, cx + 46, cy - 1);
                            g.DrawLine(pwh, cx + 30, cy + 9, cx + 46, cy + 11);
                        }
                        break;
                    }
                case 1: // 小狗
                    {
                        g.FillEllipse(bb, cx - rx * 0.86f, cy - ry * 0.85f, rx * 0.55f, ry * 1.5f);   // 左垂耳
                        g.FillEllipse(bb, cx + rx * 0.31f, cy - ry * 0.85f, rx * 0.55f, ry * 1.5f);   // 右垂耳
                        g.DrawEllipse(pd, cx - rx * 0.86f, cy - ry * 0.85f, rx * 0.55f, ry * 1.5f);
                        g.DrawEllipse(pd, cx + rx * 0.31f, cy - ry * 0.85f, rx * 0.55f, ry * 1.5f);
                        g.FillEllipse(bb, cx - rx, cy - ry, rx * 2, ry * 2);
                        g.DrawEllipse(pd, cx - rx, cy - ry, rx * 2, ry * 2);
                        // 眼罩色块
                        using (SolidBrush st = new SolidBrush(Color.FromArgb(60, dark)))
                            g.FillEllipse(st, cx - 24, cy - 16, 20, 16);
                        break;
                    }
                case 2: // 白兔
                    {
                        g.FillEllipse(bb, cx - 17, cy - ry * 2.1f, 14, 40);
                        g.DrawEllipse(pd, cx - 17, cy - ry * 2.1f, 14, 40);
                        g.FillEllipse(bb, cx + 3, cy - ry * 2.1f, 14, 40);
                        g.DrawEllipse(pd, cx + 3, cy - ry * 2.1f, 14, 40);
                        using (SolidBrush inn = new SolidBrush(Color.FromArgb(200, 240, 190, 190)))
                        {
                            g.FillEllipse(inn, cx - 14, cy - ry * 2.0f, 8, 32);
                            g.FillEllipse(inn, cx + 6, cy - ry * 2.0f, 8, 32);
                        }
                        g.FillEllipse(bb, cx - rx, cy - ry, rx * 2, ry * 2);
                        g.DrawEllipse(pd, cx - rx, cy - ry, rx * 2, ry * 2);
                        break;
                    }
                case 3: // 棕熊
                    {
                        g.FillEllipse(bb, cx - rx * 0.85f, cy - ry * 1.05f, 22, 22);
                        g.DrawEllipse(pd, cx - rx * 0.85f, cy - ry * 1.05f, 22, 22);
                        g.FillEllipse(bb, cx + rx * 0.85f - 22, cy - ry * 1.05f, 22, 22);
                        g.DrawEllipse(pd, cx + rx * 0.85f - 22, cy - ry * 1.05f, 22, 22);
                        g.FillEllipse(bb, cx - rx, cy - ry, rx * 2, ry * 2);
                        g.DrawEllipse(pd, cx - rx, cy - ry, rx * 2, ry * 2);
                        // 口鼻
                        using (SolidBrush mu = new SolidBrush(light))
                            g.FillEllipse(mu, cx - 14, cy + 2, 28, 20);
                        break;
                    }
                case 4: // 小恐龙
                    {
                        // 背刺
                        PointF[] sp1 = { new PointF(cx - 6, cy - ry - 2), new PointF(cx, cy - ry - 20), new PointF(cx + 6, cy - ry - 2) };
                        PointF[] sp2 = { new PointF(cx - 20, cy - ry + 6), new PointF(cx - 16, cy - ry - 12), new PointF(cx - 8, cy - ry + 3) };
                        PointF[] sp3 = { new PointF(cx + 8, cy - ry + 3), new PointF(cx + 16, cy - ry - 12), new PointF(cx + 22, cy - ry + 8) };
                        using (SolidBrush sbp = new SolidBrush(Color.FromArgb(200, 120, 180, 120)))
                        {
                            g.FillPolygon(sbp, sp1); g.FillPolygon(sbp, sp2); g.FillPolygon(sbp, sp3);
                        }
                        g.FillEllipse(bb, cx - rx, cy - ry, rx * 2, ry * 2);
                        g.DrawEllipse(pd, cx - rx, cy - ry, rx * 2, ry * 2);
                        // 尾巴
                        using (SolidBrush tb = new SolidBrush(body))
                        using (Pen tp = new Pen(dark, 1.4f))
                        {
                            PointF[] tail = { new PointF(cx + rx - 4, cy + 4), new PointF(cx + rx + 26, cy + 12), new PointF(cx + rx + 30, cy + 20), new PointF(cx + rx - 2, cy + 18) };
                            g.FillPolygon(tb, tail);
                            g.DrawPolygon(tp, tail);
                        }
                        // 肚皮
                        using (SolidBrush bel = new SolidBrush(light))
                            g.FillEllipse(bel, cx - 18, cy + 2, 36, 26);
                        break;
                    }
                case 5: // 章鱼
                    {
                        using (SolidBrush tb = new SolidBrush(body))
                        using (Pen tp2 = new Pen(dark, 1.3f))
                        {
                            for (int i = 0; i < 6; i++)
                            {
                                float ang = 0.3f + i * 0.52f;
                                float x0 = cx + (float)Math.Cos(ang) * rx * 0.6f - 6;
                                float y0 = cy + ry * 0.35f;
                                float sway = 3f * (float)Math.Sin(t * 2f + i);
                                g.FillEllipse(tb, x0 + sway, y0, 13, 30);
                                g.DrawEllipse(tp2, x0 + sway, y0, 13, 30);
                            }
                        }
                        g.FillEllipse(bb, cx - rx, cy - ry, rx * 2, ry * 2);
                        g.DrawEllipse(pd, cx - rx, cy - ry, rx * 2, ry * 2);
                        break;
                    }
                default: // 小黄鸡
                    {
                        // 冠
                        PointF[] cr = { new PointF(cx - 8, cy - ry + 2), new PointF(cx - 2, cy - ry - 12), new PointF(cx + 4, cy - ry + 1) };
                        using (SolidBrush cbr = new SolidBrush(Color.FromArgb(230, 230, 120, 110)))
                            g.FillPolygon(cbr, cr);
                        // 翅膀
                        g.FillEllipse(bb, cx - rx - 4, cy - 2, 14, 22);
                        g.FillEllipse(bb, cx + rx - 10, cy - 2, 14, 22);
                        g.FillEllipse(bb, cx - rx, cy - ry, rx * 2, ry * 2);
                        g.DrawEllipse(pd, cx - rx, cy - ry, rx * 2, ry * 2);
                        // 嘴
                        PointF[] bk = { new PointF(cx - 6, cy + 6), new PointF(cx + 6, cy + 6), new PointF(cx, cy + 17) };
                        using (SolidBrush bkb = new SolidBrush(Color.FromArgb(240, 230, 140, 40)))
                            g.FillPolygon(bkb, bk);
                        break;
                    }
            }
        }
    }

    void DrawFace(Graphics g, float cx, float cy, float ry, Color dark)
    {
        bool blink = blinkFrames > 0;
        using (SolidBrush eye = new SolidBrush(Color.FromArgb(50, 45, 40)))
        using (Pen line = new Pen(Color.FromArgb(60, 50, 40), 2.2f))
        {
            if (blink)
            {
                g.DrawLine(line, cx - 19, cy - 4, cx - 7, cy - 4);
                g.DrawLine(line, cx + 7, cy - 4, cx + 19, cy - 4);
            }
            else
            {
                g.FillEllipse(eye, cx - 19, cy - 10, 12, 13);
                g.FillEllipse(eye, cx + 7, cy - 10, 12, 13);
                using (SolidBrush gl = new SolidBrush(Color.FromArgb(230, 255, 255, 255)))
                {
                    g.FillEllipse(gl, cx - 16, cy - 8, 4, 4);
                    g.FillEllipse(gl, cx + 10, cy - 8, 4, 4);
                }
            }
            // 嘴
            using (Pen mp = new Pen(Color.FromArgb(90, 70, 60), 1.6f))
            {
                g.DrawArc(mp, cx - 7, cy + 4, 14, 10, 10, 160);
            }
        }
        // 腮红
        using (SolidBrush bl = new SolidBrush(Color.FromArgb(60, 240, 140, 140)))
        {
            g.FillEllipse(bl, cx - 30, cy + 2, 12, 8);
            g.FillEllipse(bl, cx + 18, cy + 2, 12, 8);
        }
    }

    // 说话气泡原来画在窗口里(顶端 y=5)，而窗口只有 205 高、人 188 高，
    // 头顶就在 y≈17，白框必然糊在脸上。改成独立浮层窗口：贴在道的头顶上方，
    // 上面放不下就翻到脚下，跟着人物走，说完自动隐藏。
    Form bubbleForm;
    Label bubbleLabel;
    void SyncBubbleWindow()
    {
        if (bubble == null || bubbleFrames <= 0)
        {
            if (bubbleForm != null && bubbleForm.Visible) bubbleForm.Hide();
            return;
        }
        if (bubbleForm == null)
        {
            bubbleForm = new Form();
            bubbleForm.FormBorderStyle = FormBorderStyle.None;
            bubbleForm.ShowInTaskbar = false;
            bubbleForm.TopMost = true;
            bubbleForm.BackColor = Color.FromArgb(252, 253, 255);
            bubbleLabel = new Label();
            bubbleLabel.AutoSize = false;
            bubbleLabel.BackColor = Color.FromArgb(252, 253, 255);
            bubbleLabel.ForeColor = Color.FromArgb(44, 46, 62);
            bubbleLabel.Font = new Font("Microsoft YaHei", 9f);
            bubbleForm.Controls.Add(bubbleLabel);
        }
        if (bubbleLabel.Text != bubble) bubbleLabel.Text = bubble;

        int maxW = 340;
        Size szTxt = TextRenderer.MeasureText(bubble, bubbleLabel.Font, new Size(maxW, 900), TextFormatFlags.WordBreak);
        int bw = Math.Min(maxW, Math.Max(64, szTxt.Width)) + 22;
        int bh = Math.Min(120, Math.Max(22, szTxt.Height)) + 16;
        bubbleForm.Size = new Size(bw, bh);
        bubbleLabel.Bounds = new Rectangle(11, 8, bw - 22, bh - 16);

        Rectangle wa = Screen.FromControl(this).WorkingArea;
        Rectangle me = this.Bounds;
        int x = me.Left + (me.Width - bw) / 2;
        int y = me.Top - bh - 5;
        if (y < wa.Top + 4) y = me.Bottom + 5;
        if (y + bh > wa.Bottom - 4) y = wa.Top + 4;
        if (x + bw > wa.Right - 4) x = wa.Right - 4 - bw;
        if (x < wa.Left + 4) x = wa.Left + 4;
        bubbleForm.Location = new Point(x, y);
        if (!bubbleForm.Visible) bubbleForm.Show();
    }


    protected override void OnMouseDown(MouseEventArgs e)
    {
        base.OnMouseDown(e);
        if (e.Button == MouseButtons.Left)
        {
            mouseDown = true;
            movedFlag = false;
            dragStart = Cursor.Position;
            formStart = Location;
            // 2026-11-16 学 dotnet/winforms：鼠标一按下就捕获，
            // 手快一点把它甩出窗口外也不会丢 MouseMove，拖动不再半路撒手。
            Capture = true;
        }
    }

    protected override void OnMouseMove(MouseEventArgs e)
    {
        base.OnMouseMove(e);
        if (mouseDown)
        {
            Point now = Cursor.Position;
            int dx = now.X - dragStart.X;
            int dy = now.Y - dragStart.Y;
            if (Math.Abs(dx) > 3 || Math.Abs(dy) > 3) movedFlag = true;
            if (movedFlag) Location = new Point(formStart.X + dx, formStart.Y + dy);
        }
    }

    protected override void OnMouseUp(MouseEventArgs e)
    {
        base.OnMouseUp(e);
        if (e.Button == MouseButtons.Left)
        {
            mouseDown = false;
            if (movedFlag) SavePos();
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
            {
                // 点它一下：先招手打招呼，再说句话。先把正在念的长句掐掉，
                // 不然点了还得等它念完才理你，手感就是"反应慢"
                StopSpeechNow();
                waveTicks = 46;
                idleTicks = 0;
                int idx = (DateTime.Now.Hour + DateTime.Now.Day) % lines.Length;
                Say(lines[idx]);
            }
        }
    }

    protected override void OnMouseEnter(EventArgs e)
    {
        base.OnMouseEnter(e);
        if (petMode == 1) SlideTo(PeekOutX());     // 探头：鼠标过来就整个出来
    }

    protected override void OnMouseLeave(EventArgs e)
    {
        base.OnMouseLeave(e);
        if (petMode == 1 && !mouseDown) SlideTo(PeekRestX());   // 走开又缩回去
    }

    protected override void OnDoubleClick(EventArgs e)
    {
        base.OnDoubleClick(e);
        MenuTalk(null, null);
    }

    protected override void OnFormClosing(FormClosingEventArgs e)
    {
        try { timeEndPeriod(1); } catch { }
        try { if (pump != null) pump.Dispose(); } catch { }
        SavePos();
        base.OnFormClosing(e);
    }

    protected override void OnShown(EventArgs e)
    {
        base.OnShown(e);
        try
        {
            // 把窗口夹回屏幕可见范围内
            Rectangle wa = Screen.PrimaryScreen.WorkingArea;
            int nx = Location.X;
            int ny = Location.Y;
            int maxX = wa.Right - Width - 8;
            int maxY = wa.Bottom - Height - 8;
            if (nx < wa.Left) nx = wa.Right * 34 / 100;
            if (nx > maxX) nx = maxX;
            if (ny < wa.Top) ny = wa.Bottom * 40 / 100;
            if (ny > maxY) ny = maxY;
            Location = new Point(nx, ny);
            TopMost = true;
            SetWindowPos(this.Handle, HWND_TOPMOST, nx, ny, 0, 0, SWP_NOSIZE | SWP_NOACTIVATE | 0x0040);
            ForceLayer();
            // 上次调过的音量档要记住
            try
            {
                RegistryKey k = Registry.CurrentUser.OpenSubKey("Software\\DaoPet");
                if (k != null)
                {
                    object vv = k.GetValue("VolLevel");
                    if (vv != null) volLevel = Convert.ToInt32(vv);
                    k.Close();
                }
            }
            catch { }
            if (volLevel < 0) volLevel = 0;
            if (volLevel > 2) volLevel = 2;
            // 开机先拉一次手机那边的记忆（走公网，不挑 WiFi）
            try { System.Threading.ThreadPool.QueueUserWorkItem(delegate(object o) { SyncPullMerge(); }); } catch { }
            // 开机不再一句接一句地自己播报（简报、记忆、今日所学都挪到右键菜单里，
            // 想看再点）。话只在两处出现：他要的早晚问候，还有用户点它或喊它的时候。
            // 上次选的是「贴边偷看」或「悬浮球」，开机就直接按那个样子待着
            if (petMode == 1 || petMode == 2) SetModeWindow();
        }
        catch { }
    }

    static void DumpSelf()
    {
        string dir = Path.GetDirectoryName(Application.ExecutablePath);
        DesktopPet p = new DesktopPet();

        DumpOne(p, Path.Combine(dir, "selfcheck.png"));

        p.speaking = true;
        p.speakMouthStart = Environment.TickCount - 200;
        p.speakMouthUntil = Environment.TickCount + 4000;
        p.t = 1.20f;
        DumpOne(p, Path.Combine(dir, "selfcheck_talk.png"));
        p.t = 1.36f;
        DumpOne(p, Path.Combine(dir, "selfcheck_talk2.png"));
        p.t = 1.52f;
        DumpOne(p, Path.Combine(dir, "selfcheck_talk3.png"));

        // 换个形象看看嘴还在不在脸上（企鹅 / 小机器人）
        p.species = 5;
        p.t = 1.40f;
        DumpOne(p, Path.Combine(dir, "selfcheck_talk_p5.png"));
        p.species = 11;
        DumpOne(p, Path.Combine(dir, "selfcheck_talk_p11.png"));

        // 8 号银发剑客：站着、走起来各出一张，确认新姿势图与八帧走路真的被加载
        p.species = 8;
        p.ApplyPose(8);
        p.speaking = false;
        p.walkTicks = 0;
        p.t = 1.00f;
        DumpOne(p, Path.Combine(dir, "selfcheck_p8_stand.png"));
        p.walkTicks = 60;
        for (int wf = 0; wf < 4; wf++)
        {
            p.t = 2.40f + wf * 0.13f;
            DumpOne(p, Path.Combine(dir, "selfcheck_p8_walk" + wf + ".png"));
        }
        p.walkTicks = 0;
        p.species = 0;

        p.speaking = false;
        p.thinkTicks = 30;
        p.walkTicks = 80;
        p.t = 2.4f;
        DumpOne(p, Path.Combine(dir, "selfcheck_think.png"));

        p.thinkTicks = 0;
        p.walkTicks = 0;
        p.moodKind = 2;
        p.moodTicks = 74;
        p.t = 3.1f;
        DumpOne(p, Path.Combine(dir, "selfcheck_angry.png"));

        p.moodKind = 1;
        p.moodTicks = 74;
        p.t = 3.8f;
        DumpOne(p, Path.Combine(dir, "selfcheck_happy.png"));

        // 新动作自检：招手 / 坐下 / 犯困
        p.moodTicks = 0;
        p.moodKind = 0;
        p.waveTicks = 46;
        p.t = 1.6f;
        DumpOne(p, Path.Combine(dir, "selfcheck_wave.png"));

        // 走路：连抓四帧，看两条腿是不是换着踏、头有没有跟着乱晃
        p.sitting = false;
        p.sleepy = false;
        p.waveTicks = 0;
        // 走路专门测八帧的形象（黑发少年 = 7），抓满八帧才看得出整圈
        p.species = 7;
        p.ApplyPose(7);
        p.walkTicks = 80;
        p.walkDirX = 1;
        for (int wi = 0; wi < 8; wi++)
        {
            p.t = 0.36f + wi * 0.09f;
            DumpOne(p, Path.Combine(dir, "selfcheck_walk" + wi + ".png"));
        }
        p.walkTicks = 0;

        // 银发剑客 = 8：也抓一遍八帧，确认换到这个形象后走路是全身在迈步，
        // 不是半身像平移，也不是两只脚原地不动
        p.species = 8;
        p.ApplyPose(8);
        p.walkTicks = 80;
        p.walkDirX = 1;
        for (int wi = 0; wi < 8; wi++)
        {
            p.t = 0.36f + wi * 0.09f;
            DumpOne(p, Path.Combine(dir, "selfcheck_walk8_" + wi + ".png"));
        }
        p.walkTicks = 0;

        // 御剑：看他是不是真的踩在剑上，而不是正面站姿配一把飘在脚边的剑
        // actHold 不设起来时，绘制前会把动作强度算回 0，动作就根本没上画
        p.actHold = 999;
        p.actKind = 2;
        p.actAmt = 1.0f;
        p.t = 1.4f;
        DumpOne(p, Path.Combine(dir, "selfcheck_sword8.png"));
        p.actKind = 0;
        p.actAmt = 0f;
        p.actHold = 0;

        p.sitting = true;
        p.t = 2.0f;
        DumpOne(p, Path.Combine(dir, "selfcheck_sit.png"));

        p.sleepy = true;
        p.t = 4.4f;
        DumpOne(p, Path.Combine(dir, "selfcheck_sleep.png"));

        // 难过（掉眼泪）
        p.sleepy = false;
        p.sitting = false;
        p.waveTicks = 0;
        p.moodKind = 3;
        p.moodTicks = 74;
        p.t = 4.1f;
        DumpOne(p, Path.Combine(dir, "selfcheck_sad.png"));

        // 新增两种表情自检：疑惑 / 得意
        p.moodKind = 7;
        p.moodTicks = 74;
        p.t = 5.0f;
        DumpOne(p, Path.Combine(dir, "selfcheck_curious.png"));

        p.moodKind = 8;
        p.moodTicks = 74;
        p.t = 5.6f;
        DumpOne(p, Path.Combine(dir, "selfcheck_proud.png"));

        // 12 张形象逐个验证：笑脸是否真的落在脸上
        p.moodKind = 1;
        p.moodTicks = 74;
        p.t = 1.0f;
        if (p.faceCount > 0)
        {
            for (int i = 0; i < p.faceCount; i++)
            {
                p.species = i;
                DumpOne(p, Path.Combine(dir, "selfcheck_face_" + i + ".png"));
            }
            p.species = 0;
        }

        // 每个形象来一张说话帧：检查嘴有没有画在脸上
        p.moodTicks = 0;
        p.moodKind = 0;
        p.speaking = true;
        p.speakMouthStart = Environment.TickCount - 300;
        p.speakMouthUntil = Environment.TickCount + 5000;
        p.t = 1.52f;
        for (int i = 0; i < p.faceCount; i++)
        {
            p.species = i;
            DumpOne(p, Path.Combine(dir, "selfcheck_mouth_" + i + ".png"));
        }
        p.species = 0;
        p.speaking = false;
    }

    static void DumpOne(DesktopPet p, string path)
    {
        using (Bitmap b = new Bitmap(W, H))
        {
            using (Graphics g = Graphics.FromImage(b))
            {
                p.PaintAll(g, W, H);
            }
            b.Save(path, ImageFormat.Png);
        }
    }

    // 主入口
    static System.Threading.Mutex singleLock;

    // 出事就留个痕，省得下次又是"莫名其妙闪退"查不出来
    static void LogCrash(string what, Exception ex)
    {
        try
        {
            string p2 = Path.Combine(Path.GetDirectoryName(Application.ExecutablePath), "崩溃日志.txt");
            string s2 = "[" + DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss") + "] " + what + " : "
                + (ex == null ? "null" : ex.ToString()) + Environment.NewLine;
            File.AppendAllText(p2, s2, Encoding.UTF8);
        }
        catch { }
    }

    public static void Main(string[] args)
    {
        try
        {
            // 必须在创建任何窗口之前调用，否则窗口会被系统按 DPI 缩小，下半身被裁掉
            SetProcessDPIAware();

            // 闪退第一嫌疑人：点了两次图标，两个道叠在一个位置上互相挤。
            // 已经有一个在跑就安静退出，不再开第二个
            bool isFirst = true;
            try { singleLock = new System.Threading.Mutex(true, "DaoPetSingleInstance", out isFirst); }
            catch { isFirst = true; }
            if (!isFirst) return;
            // 启动即后台预热常用短句，开口不用等联网合成
            try { PrewarmTts(); } catch { }

            AppDomain.CurrentDomain.UnhandledException += delegate(object s0, UnhandledExceptionEventArgs e0)
            {
                LogCrash("Unhandled", (Exception)e0.ExceptionObject);
            };
            Application.ThreadException += delegate(object s1, System.Threading.ThreadExceptionEventArgs e1)
            {
                LogCrash("UI", e1.Exception);
            };

            // 自检出图：道.exe --dump 会在程序目录生成 selfcheck.png
            if (args.Length > 0 && args[0] == "--dump")
            {
                DumpSelf();
                return;
            }
            // 表情图专项自检：把 8 号的四种表情各出一张，顺带把加载状态写出来
            if (args.Length > 0 && args[0] == "--dumpexpr")
            {
                string dd = Path.GetDirectoryName(Application.ExecutablePath);
                DesktopPet q = new DesktopPet();
                string info = "exprKeys=" + q.exprMap.Count;
                foreach (int kk in q.exprMap.Keys) info += " sp" + kk;
                info += " | laughKeys=" + q.laughMap.Count;
                foreach (int kk in q.laughMap.Keys) info += " sp" + kk + "(" + q.laughMap[kk].Length + ")";
                try { File.AppendAllText(Path.Combine(dd, "_exprlog.txt"), info + Environment.NewLine, Encoding.UTF8); } catch { }
                q.species = 8;
                int[] mk = new int[] { 1, 2, 3, 0 };
                string[] nm = new string[] { "happy", "angry", "sad", "plain" };
                for (int mi = 0; mi < 4; mi++)
                {
                    q.moodKind = mk[mi];
                    q.moodTicks = mk[mi] == 0 ? 0 : 74;
                    q.speaking = false;
                    q.sleepy = false;
                    q.t = 2.0f + mi;
                    DumpOne(q, Path.Combine(dd, "exprcheck_" + nm[mi] + ".png"));
                }
                q.moodKind = 0;
                q.moodTicks = 0;
                q.sleepy = true;
                q.t = 6.4f;
                DumpOne(q, Path.Combine(dd, "exprcheck_sleep.png"));
                // 笑的一圈：按 9 步/秒推进时间，六步正好走完四帧，逐帧摊开看
                q.sleepy = false;
                q.moodKind = 1;
                q.moodTicks = 74;
                for (int li2 = 0; li2 < 6; li2++)
                {
                    q.t = 6.0f + li2 / 9.0f;
                    DumpOne(q, Path.Combine(dd, "exprcheck_laugh" + li2 + ".png"));
                }
                return;
            }

            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);
            // 启动局域网同步服务（手机连同一 WiFi 时可互传记忆/新版本）
            try { SyncServer.Start(); } catch { }
            Application.Run(new DesktopPet());
        }
        catch (Exception ex)
        {
            try
            {
                string log = System.IO.Path.Combine(System.IO.Path.GetTempPath(), "pet_error.txt");
                System.IO.File.WriteAllText(log, ex.ToString());
            }
            catch { }
        }
    }
}

// 局域网同步服务：电脑当小服务器，手机在同一个 WiFi 下自动找到它
// 行协议（纯文本，避免 JSON 解析出错）：
//   L|一句话   K|一条知识   M|一条记忆
static class SyncServer
{
    const int HTTP_PORT = 8848;
    const int UDP_PORT = 8849;
    public const int APP_VER = 114;

    public static void Start()
    {
        try
        {
            System.Threading.Thread th = new System.Threading.Thread(HttpLoop);
            th.IsBackground = true;
            th.Start();
        }
        catch { }
        try
        {
            System.Threading.Thread tu = new System.Threading.Thread(UdpLoop);
            tu.IsBackground = true;
            tu.Start();
        }
        catch { }
    }

    static string DataDir()
    {
        try { return Path.GetDirectoryName(Application.ExecutablePath); }
        catch { return "."; }
    }

    // 每 5 秒向局域网广播一次自己的地址，手机收到就知道电脑在哪
    static void UdpLoop()
    {
        System.Net.Sockets.UdpClient u = null;
        try
        {
            u = new System.Net.Sockets.UdpClient();
            u.EnableBroadcast = true;
        }
        catch { return; }
        IPEndPoint ep = new IPEndPoint(IPAddress.Broadcast, UDP_PORT);
        while (true)
        {
            try
            {
                string msg = "DAO|" + LocalIp() + "|" + HTTP_PORT + "|" + APP_VER;
                byte[] b = Encoding.UTF8.GetBytes(msg);
                u.Send(b, b.Length, ep);
            }
            catch { }
            System.Threading.Thread.Sleep(5000);
        }
    }

    static string LocalIp()
    {
        try
        {
            foreach (System.Net.NetworkInformation.NetworkInterface ni in System.Net.NetworkInformation.NetworkInterface.GetAllNetworkInterfaces())
            {
                if (ni.OperationalStatus != System.Net.NetworkInformation.OperationalStatus.Up) continue;
                if (ni.NetworkInterfaceType == System.Net.NetworkInformation.NetworkInterfaceType.Loopback) continue;
                foreach (System.Net.NetworkInformation.UnicastIPAddressInformation ua in ni.GetIPProperties().UnicastAddresses)
                {
                    if (ua.Address.AddressFamily == System.Net.Sockets.AddressFamily.InterNetwork)
                        return ua.Address.ToString();
                }
            }
        }
        catch { }
        return "127.0.0.1";
    }

    static void HttpLoop()
    {
        System.Net.Sockets.TcpListener l = null;
        for (int attempt = 0; attempt < 4 && l == null; attempt++)
        {
            try
            {
                System.Net.Sockets.TcpListener nl = new System.Net.Sockets.TcpListener(IPAddress.Any, HTTP_PORT);
                nl.Server.SetSocketOption(System.Net.Sockets.SocketOptionLevel.Socket,
                                          System.Net.Sockets.SocketOptionName.ReuseAddress, true);
                nl.Start();
                l = nl;
            }
            catch
            {
                // 刚被上一个我占用过，端口还在回收，等一下再来
                System.Threading.Thread.Sleep(2000);
            }
        }
        if (l == null) return;
        while (true)
        {
            try
            {
                System.Net.Sockets.TcpClient c = l.AcceptTcpClient();
                System.Threading.Thread t = new System.Threading.Thread(delegate() { Handle(c); });
                t.IsBackground = true;
                t.Start();
            }
            catch { System.Threading.Thread.Sleep(500); }
        }
    }

    static void Handle(System.Net.Sockets.TcpClient c)
    {
        try
        {
            // 防止申斥阻塞
            c.ReceiveTimeout = 8000;
            using (c)
            using (System.Net.Sockets.NetworkStream ns = c.GetStream())
            {
                ns.ReadTimeout = 8000;
                ns.WriteTimeout = 20000;

                byte[] head = new byte[8192];
                int total = 0;
                while (total < head.Length)
                {
                    int n = ns.Read(head, total, 1);
                    if (n <= 0) break;
                    total += n;
                    if (total >= 4 && head[total - 4] == 13 && head[total - 3] == 10
                        && head[total - 2] == 13 && head[total - 1] == 10) break;
                }
                if (total == 0) return;

                string htxt = Encoding.ASCII.GetString(head, 0, total);
                string[] hl = htxt.Replace("\r", "").Split('\n');
                string first = hl.Length > 0 ? hl[0] : "";
                string[] parts = first.Split(' ');
                string method = parts.Length > 0 ? parts[0] : "";
                string path = parts.Length > 1 ? parts[1] : "/";

                int clen = 0;
                for (int i = 1; i < hl.Length; i++)
                {
                    string ln = hl[i];
                    int idx = ln.IndexOf(':');
                    if (idx <= 0) continue;
                    string k = ln.Substring(0, idx).Trim().ToLower();
                    if (k == "content-length")
                    {
                        try { clen = Convert.ToInt32(ln.Substring(idx + 1).Trim()); } catch { }
                    }
                }
                string body = "";
                if (clen > 0 && clen < 1048576)
                {
                    byte[] bb = new byte[clen];
                    int got = 0;
                    while (got < clen)
                    {
                        int n = ns.Read(bb, got, clen - got);
                        if (n <= 0) break;
                        got += n;
                    }
                    body = Encoding.UTF8.GetString(bb, 0, got);
                }

                if (path.StartsWith("/say"))
                {
                    string t = "";
                    if (method == "POST") t = body;
                    else
                    {
                        int qi = path.IndexOf("?t=");
                        if (qi >= 0)
                        {
                            try { t = Uri.UnescapeDataString(path.Substring(qi + 3).Replace('+', ' ')); }
                            catch { t = ""; }
                        }
                    }
                    DesktopPet.Push(t);
                    SendText(ns, t.Trim().Length > 0 ? "OK" : "EMPTY");
                }
                else if (path.StartsWith("/tts"))
                {
                    // 只合成、不放音，直接把 mp3 吐给请求方（手机端拿这个出声）
                    string t4 = "";
                    string v4 = "";
                    if (method == "POST") t4 = body;
                    else
                    {
                        int qi4 = path.IndexOf("?t=");
                        if (qi4 >= 0)
                        {
                            try
                            {
                                t4 = Uri.UnescapeDataString(path.Substring(qi4 + 3).Replace('+', ' '));
                                int amp = t4.IndexOf('&');
                                if (amp > 0) t4 = t4.Substring(0, amp);
                            }
                            catch { t4 = ""; }
                        }
                    }
                    int vi4 = path.IndexOf("v=");
                    if (vi4 >= 0)
                    {
                        try
                        {
                            v4 = Uri.UnescapeDataString(path.Substring(vi4 + 2));
                            int amp2 = v4.IndexOf('&');
                            if (amp2 > 0) v4 = v4.Substring(0, amp2);
                        }
                        catch { v4 = ""; }
                    }
                    string f4 = DesktopPet.TtsFile(t4, v4);
                    if (f4.Length == 0) SendText(ns, "TTSFAIL");
                    else
                    {
                        byte[] ab4 = File.ReadAllBytes(f4);
                        SendRaw(ns, "audio/mpeg", ab4);
                    }
                }
                else if (path.StartsWith("/chat"))
                {
                    if (path.Contains("mode=1")) { DesktopPet.SetChatMode(true); SendText(ns, "ON"); }
                    else if (path.Contains("mode=0")) { DesktopPet.SetChatMode(false); SendText(ns, "OFF"); }
                    else { DesktopPet.PushChat(); SendText(ns, "OK"); }
                }
                else if (path.StartsWith("/do"))
                {
                    string q2 = "";
                    if (method == "POST") q2 = body;
                    else
                    {
                        int qi2 = path.IndexOf("?q=");
                        if (qi2 >= 0)
                        {
                            try { q2 = Uri.UnescapeDataString(path.Substring(qi2 + 3).Replace('+', ' ')); }
                            catch { q2 = ""; }
                        }
                    }
                    DesktopPet.ThinkCmd(q2);
                    SendText(ns, q2.Trim().Length > 0 ? "THINK" : "EMPTY");
                }
                else if (path.StartsWith("/wakefeed"))
                {
                    // 自检口：把一句"听到的话"直接喂进去，走一遍完整的应声流程
                    string t = "";
                    int qi5 = path.IndexOf("?t=");
                    if (qi5 >= 0)
                    {
                        try { t = Uri.UnescapeDataString(path.Substring(qi5 + 3).Replace('+', ' ')); }
                        catch { t = ""; }
                    }
                    SendText(ns, DesktopPet.WakeFeed(t) ? "HIT" : "MISS");
                }
                else if (path.StartsWith("/wakechk"))
                {
                    // 自检口：把一句话丢进来，看它会不会当成"在叫名字"
                    string t = "";
                    int qi3 = path.IndexOf("?t=");
                    if (qi3 >= 0)
                    {
                        try { t = Uri.UnescapeDataString(path.Substring(qi3 + 3).Replace('+', ' ')); }
                        catch { t = ""; }
                    }
                    SendText(ns, DesktopPet.WakeChk(t) ? "YES" : "NO");
                }
                else if (path.StartsWith("/fast"))
                {
                    // 自检口：常见问题本地秒答，返回 FAST|答句 或 SLOW（要交给大脑）
                    string fq = "";
                    int qi4 = path.IndexOf("?q=");
                    if (qi4 >= 0)
                    {
                        try { fq = Uri.UnescapeDataString(path.Substring(qi4 + 3).Replace('+', ' ')); }
                        catch { fq = ""; }
                    }
                    string fa = DesktopPet.FastChk(fq);
                    SendText(ns, fa == null ? "SLOW" : "FAST|" + fa);
                }
                else if (path.StartsWith("/pose"))
                {
                    if (path.Contains("p=lie")) { DesktopPet.PoseCmd("lie"); SendText(ns, "LIE"); }
                    else if (path.Contains("p=cry")) { DesktopPet.PoseCmd("cry"); SendText(ns, "CRY"); }
                    else if (path.Contains("p=walk")) { DesktopPet.PoseCmd("walk"); SendText(ns, "WALK"); }
                    else if (path.Contains("p=wake")) { DesktopPet.PoseCmd("wake"); SendText(ns, "WAKE"); }
                    else if (path.Contains("p=fly")) { DesktopPet.PoseCmd("fly"); SendText(ns, "FLY"); }
                    else if (path.Contains("p=sword")) { DesktopPet.PoseCmd("sword"); SendText(ns, "SWORD"); }
                    else if (path.Contains("p=ride")) { DesktopPet.PoseCmd("ride"); SendText(ns, "RIDE"); }
                    else if (path.Contains("p=dance")) { DesktopPet.PoseCmd("dance"); SendText(ns, "DANCE"); }
                    else if (path.Contains("p=tea")) { DesktopPet.PoseCmd("tea"); SendText(ns, "TEA"); }
                    else if (path.Contains("p=tv")) { DesktopPet.PoseCmd("tv"); SendText(ns, "TV"); }
                    else if (path.Contains("p=skate")) { DesktopPet.PoseCmd("skate"); SendText(ns, "SKATE"); }
                    else if (path.Contains("p=roller")) { DesktopPet.PoseCmd("roller"); SendText(ns, "ROLLER"); }
                    else if (path.Contains("p=poem")) { DesktopPet.PoseCmd("poem"); SendText(ns, "POEM"); }
                    else if (path.Contains("p=english")) { DesktopPet.PoseCmd("english"); SendText(ns, "ENGLISH"); }
                    else if (path.Contains("p=sing")) { DesktopPet.PoseCmd("sing"); SendText(ns, "SING"); }
                    else SendText(ns, "USE|p=lie|cry|walk|wake|fly|sword|ride|dance|tea|tv");
                }
                else if (path.StartsWith("/species"))
                {
                    int sn = 0;
                    try
                    {
                        string q = path;
                        if (q.Contains("n="))
                        {
                            string sraw = q.Substring(q.IndexOf("n=") + 2);
                            int amp = sraw.IndexOf('&');
                            if (amp >= 0) sraw = sraw.Substring(0, amp);
                            int sp2 = sraw.IndexOf(' ');
                            if (sp2 >= 0) sraw = sraw.Substring(0, sp2);
                            sn = Convert.ToInt32(sraw);
                        }
                    }
                    catch { sn = 0; }
                    DesktopPet.SetSpecies(sn);
                    SendText(ns, "SPECIES|" + sn);
                }
                else if (path.StartsWith("/learn"))
                {
                    DesktopPet.LearnCmd();
                    SendText(ns, "LEARN");
                }
                else if (path.StartsWith("/story"))
                {
                    int sk = 1;
                    if (path.Contains("k=2")) sk = 2;
                    else if (path.Contains("k=3")) sk = 3;
                    DesktopPet.StoryCmd(sk);
                    SendText(ns, "STORY|" + sk);
                }
                else if (path.StartsWith("/stat"))
                {
                    SendText(ns, "STAT|" + DesktopPet.StatCmd());
                }
                else if (path.StartsWith("/music"))
                {
                    if (path.Contains("play="))
                    {
                        string a2 = "";
                        int ip = path.IndexOf("play=");
                        int e2 = path.IndexOf('&', ip);
                        a2 = e2 > 0 ? path.Substring(ip + 5, e2 - ip - 5) : path.Substring(ip + 5);
                        try { a2 = Uri.UnescapeDataString(a2); } catch { }
                        SendText(ns, DesktopPet.MusicPlay(a2));
                    }
                    else
                    {
                        SendText(ns, DesktopPet.MusicCmd());
                    }
                }
                else if (path.StartsWith("/abil"))
                {
                    if (method == "POST" || path.Contains("d="))
                    {
                        int d = 0;
                        int chk = 0;
                        string who = "";
                        string reason = "未写原因";
                        try
                        {
                            int ia = path.IndexOf("a=");
                            if (ia >= 0)
                            {
                                int ea = path.IndexOf('&', ia);
                                string aa = ea > 0 ? path.Substring(ia + 2, ea - ia - 2) : path.Substring(ia + 2);
                                if (aa.Length > 0) who = Uri.UnescapeDataString(aa);
                            }
                            int ip = path.IndexOf("d=");
                            if (ip >= 0)
                            {
                                int e1 = path.IndexOf('&', ip);
                                d = int.Parse(e1 > 0 ? path.Substring(ip + 2, e1 - ip - 2) : path.Substring(ip + 2));
                            }
                            int ic = path.IndexOf("chk=");
                            if (ic >= 0)
                            {
                                int e2 = path.IndexOf('&', ic);
                                chk = int.Parse(e2 > 0 ? path.Substring(ic + 4, e2 - ic - 4) : path.Substring(ic + 4));
                            }
                            int ir = path.IndexOf("r=");
                            if (ir >= 0)
                            {
                                int e3 = path.IndexOf('&', ir);
                                string rr = e3 > 0 ? path.Substring(ir + 2, e3 - ir - 2) : path.Substring(ir + 2);
                                if (rr.Length > 0) reason = Uri.UnescapeDataString(rr);
                            }
                        }
                        catch { }
                        SendText(ns, DesktopPet.AbAdd(who, d, reason, chk));
                    }
                    else
                    {
                        SendText(ns, "AB|" + DesktopPet.AbCmd());
                    }
                }
                else if (path.StartsWith("/joy"))
                {
                    if (method == "POST" || path.Contains("d="))
                    {
                        int d = 0;
                        int chk = 0;
                        string reason = "未写原因";
                        try
                        {
                            int ip = path.IndexOf("d=");
                            if (ip >= 0)
                            {
                                int e1 = path.IndexOf('&', ip);
                                d = int.Parse(e1 > 0 ? path.Substring(ip + 2, e1 - ip - 2) : path.Substring(ip + 2));
                            }
                            int ic = path.IndexOf("chk=");
                            if (ic >= 0)
                            {
                                int e2 = path.IndexOf('&', ic);
                                chk = int.Parse(e2 > 0 ? path.Substring(ic + 4, e2 - ic - 4) : path.Substring(ic + 4));
                            }
                            int ir = path.IndexOf("r=");
                            if (ir >= 0)
                            {
                                int e3 = path.IndexOf('&', ir);
                                string rr = e3 > 0 ? path.Substring(ir + 2, e3 - ir - 2) : path.Substring(ir + 2);
                                if (rr.Length > 0) reason = Uri.UnescapeDataString(rr);
                            }
                        }
                        catch { }
                        SendText(ns, DesktopPet.JoyAdd(d, reason, chk));
                    }
                    else
                    {
                        SendText(ns, "JOY|" + DesktopPet.JoyCmd());
                    }
                }
                else if (path.StartsWith("/ping"))
                {
                    SendText(ns, "OK|道|" + APP_VER + "|" + LocalIp() + "|" + HTTP_PORT);
                }
                else if (path.StartsWith("/upd"))
                {
                    SendText(ns, DesktopPet.UpdCmd());
                }
                else if (path.StartsWith("/ver"))
                {
                    SendText(ns, "VER|" + APP_VER);
                }
                else if (path.StartsWith("/diag"))
                {
                    // /diag?reset=1 先清空取样：环形缓冲是滚动窗口，机器忙过之后旧样本还留着，
                    // 会让判据连续 FAIL 十几秒假阳性。测之前清零，测的才是"现在"
                    if (path.Contains("reset"))
                    {
                        SendText(ns, DesktopPet.DgReset());
                    }
                    else
                    {
                        SendText(ns, DesktopPet.DiagCmd());
                    }
                }
                else if (path.StartsWith("/apk"))
                {
                    SendApk(ns);
                }
                else if (path.StartsWith("/sync"))
                {
                    if (method == "POST")
                    {
                        int added = Merge(body);
                        SendText(ns, "OK|" + added);
                    }
                    else
                    {
                        SendText(ns, Dump());
                    }
                }
                else if (path.StartsWith("/forget"))
                {
                    string q = "";
                    int qm = path.IndexOf("?");
                    if (qm > 0 && qm + 1 < path.Length)
                    {
                        string rest = path.Substring(qm + 1);
                        int amp = rest.IndexOf("t=");
                        if (amp >= 0) rest = rest.Substring(amp + 2);
                        try { q = Uri.UnescapeDataString(rest); } catch { q = rest; }
                    }
                    SendText(ns, "FORGET|" + (q.Length > 0 ? DesktopPet.ForgetText(q) : "没说要忘什么"));
                }
                else if (path.StartsWith("/netsync"))
                {
                    // 跨网记忆同步的调试入口：Pull 一次再 Push 一次，把结果摊在文本里
                    SendText(ns, DesktopPet.SyncNetText());
                }
                else if (path.StartsWith("/note"))
                {
                    int qi = path.IndexOf('?');
                    string qs = qi >= 0 ? path.Substring(qi + 1) : "";
                    SendText(ns, DesktopPet.NoteApi(qs));
                }
                else if (path.StartsWith("/selfcheck"))
                {
                    string f = Path.Combine(DataDir(), "手机自检.txt");
                    if (method == "POST")
                    {
                        try
                        {
                            string line = DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss") + "|" + body.Trim();
                            File.AppendAllText(f, line + "\n", new UTF8Encoding(false));
                            string[] rows = File.ReadAllLines(f, new UTF8Encoding(false));
                            if (rows.Length > 300)
                            {
                                string[] keep = new string[300];
                                Array.Copy(rows, rows.Length - 300, keep, 0, 300);
                                File.WriteAllLines(f, keep, new UTF8Encoding(false));
                            }
                            SendText(ns, "OK|SC");
                        }
                        catch { SendText(ns, "ERR"); }
                    }
                    else
                    {
                        try
                        {
                            if (File.Exists(f))
                            {
                                string[] rows = File.ReadAllLines(f, new UTF8Encoding(false));
                                int n = Math.Min(5, rows.Length);
                                SendText(ns, string.Join("\n", rows, rows.Length - n, n));
                            }
                            else SendText(ns, "NONE");
                        }
                        catch { SendText(ns, "ERR"); }
                    }
                }
                else
                {
                    SendText(ns, "OK|道");
                }
            }
        }
        catch { }
    }

    static void SendText(System.Net.Sockets.NetworkStream ns, string s)
    {
        SendRaw(ns, "text/plain; charset=utf-8", Encoding.UTF8.GetBytes(s));
    }

    static void SendRaw(System.Net.Sockets.NetworkStream ns, string ct, byte[] data)
    {
        try
        {
            string h = "HTTP/1.0 200 OK\r\nContent-Type: " + ct
                + "\r\nContent-Length: " + data.Length
                + "\r\nAccess-Control-Allow-Origin: *\r\nConnection: close\r\n\r\n";
            byte[] hb = Encoding.ASCII.GetBytes(h);
            ns.Write(hb, 0, hb.Length);
            ns.Write(data, 0, data.Length);
            ns.Flush();
        }
        catch { }
    }

    static void SendApk(System.Net.Sockets.NetworkStream ns)
    {
        byte[] all = null;
        try
        {
            string p = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "道.apk");
            if (File.Exists(p)) all = File.ReadAllBytes(p);
        }
        catch { }
        if (all == null)
        {
            SendText(ns, "NOAPK");
            return;
        }
        SendRaw(ns, "application/vnd.android.package-archive", all);
    }

    static string[] LoadLines(string f)
    {
        try
        {
            if (!File.Exists(f)) return new string[0];
            return File.ReadAllLines(f, new UTF8Encoding(false));
        }
        catch { return new string[0]; }
    }

    static void AppendUnique(string f, List<string> add, int cap)
    {
        try
        {
            List<string> cur = new List<string>(LoadLines(f));
            HashSet<string> have = new HashSet<string>();
            foreach (string s in cur) have.Add(s.Trim());
            foreach (string s in add)
            {
                string t = s.Trim();
                if (t.Length == 0) continue;
                if (have.Contains(t)) continue;
                cur.Add(t);
                have.Add(t);
            }
            while (cur.Count > cap) cur.RemoveAt(0);
            File.WriteAllLines(f, cur.ToArray(), new UTF8Encoding(false));
        }
        catch { }
    }

    // 把电脑这边存的话术/知识/记忆整理成行文本，发给手机
    static string Dump()
    {
        string d = DataDir();
        StringBuilder sb = new StringBuilder();
        foreach (string s in LoadLines(Path.Combine(d, "我说的话.txt")))
            if (s.Trim().Length > 0) sb.Append("L|").Append(s.Trim()).Append("\n");
        foreach (string s in LoadLines(Path.Combine(d, "知识库.txt")))
            if (s.Trim().Length > 0) sb.Append("K|").Append(s.Trim()).Append("\n");
        foreach (string s in LoadLines(Path.Combine(d, "记忆.txt")))
            if (s.Trim().Length > 0) sb.Append("M|").Append(s.Trim()).Append("\n");
        return sb.ToString();
    }

    // 收手机推上来的行文本，去重合并进电脑的文件
    static int Merge(string body)
    {
        string d = DataDir();
        List<string> ls = new List<string>();
        List<string> ks = new List<string>();
        List<string> ms = new List<string>();
        string[] rows = body.Replace("\r", "").Split('\n');
        foreach (string r in rows)
        {
            if (r.Length < 3) continue;
            if (r[1] != '|') continue;
            string tag = r.Substring(0, 1);
            string val = r.Substring(2);
            if (tag == "L") ls.Add(val);
            else if (tag == "K") ks.Add(val);
            else if (tag == "M") ms.Add(val);
        }
        AppendUnique(Path.Combine(d, "我说的话.txt"), ls, 300);
        AppendUnique(Path.Combine(d, "知识库.txt"), ks, 200);
        AppendUnique(Path.Combine(d, "记忆.txt"), ms, 200);
        return ls.Count + ks.Count + ms.Count;
    }
}
