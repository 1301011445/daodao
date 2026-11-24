# 乐谱学习 · 第1类：微软 dotnet / WinForms 的渲染与 DPI（2026-11-24）

## 一、今天读了什么（来源 ≥2，可复核）

1. Microsoft Learn《High DPI Desktop Application Development on Windows》
   https://learn.microsoft.com/zh-cn/windows/win32/hidpi/high-dpi-desktop-application-development-on-windows
   关键点：WinForms / WPF / GDI+ 都不做自动每屏 DPI 缩放；进程注册 Per-Monitor V2 后，Windows 在 DPI 变化时**不再位图拉伸**，而是发 `WM_DPICHANGED`，由程序按消息里的**建议矩形**自己改尺寸；不用建议矩形会进入"递归 DPI 变化"循环，鼠标相对位置也会漂。
2. Microsoft Learn《ControlStyles 枚举》
   https://learn.microsoft.com/en-us/dotnet/api/system.windows.forms.controlstyles?view=windowsdesktop-8.0
   关键点：`DoubleBuffer` 必须与 `UserPaint`、`AllPaintingInWmPaint` 同时为 true；`AllPaintingInWmPaint` 让控件忽略 `WM_ERASEBKGND`，背景与前景都在 `WM_PAINT` 里画完再一次输出，这才是真正不闪。
3. MSDN Magazine《Practical Tips For Boosting The Performance Of Windows Forms Apps》
   https://learn.microsoft.com/en-us/archive/msdn-magazine/2006/march/practical-tips-for-boosting-the-performance-of-windows-forms-apps
   关键点：双缓冲的代价是每次重绘多分配一块位图内存，所以要**缩小无效区域**（Invalidate 局部），别整窗 Refresh；`Refresh()` = Invalidate + Update，会同步阻塞消息泵。

## 二、判据表（已写成脚本，可独立跑）

脚本：`F:\Daodao\tools\形象\winforms_判据.py`（输入 pet.cs，输出 PASS/FAIL，退出码 0 才算全过）

| 编号 | 判据 | 阈值 | 现状 |
|------|------|------|------|
| W1 | 双缓冲组合 | `OptimizedDoubleBuffer` 与 `AllPaintingInWmPaint` 同时出现，或 `DoubleBuffered=true` | PASS（2/1/1） |
| W2 | 进程级 DPI 感知 | 出现 `SetProcessDpiAwarenessContext` 或 `SetProcessDPIAware` | PASS（4 处） |
| W3 | 每屏 DPI 切换 | `WndProc` 处理 `0x02E0`（WM_DPICHANGED），并按 `LParam` 建议矩形 `SetWindowPos` | 今天上午 FAIL（0 处）→ 改后 PASS（3 处） |
| W4 | GDI+ 对象释放 | `new Brush/Pen/Font/Bitmap` 的 using 覆盖率 ≥90% | PASS（115.7%） |
| W5 | 重绘节奏 | `Invalidate` 次数 ≥ `Refresh` 次数（Refresh 同步阻塞） | PASS（2 : 0） |
| W6 | 跨线程改 UI | 存在 `Invoke/BeginInvoke`（后台线程数 6） | PASS（34 处） |

## 三、落到自己身上（不是笔记）

上午实测：进程已 `SetProcessDPIAware`（系统级），但 `WndProc` 里完全没接 `WM_DPICHANGED`——把窗口拖到另一块不同缩放的显示器上，系统不会替我们缩放，窗口尺寸和鼠标相对位置就会错。

改动：`F:\Daodao\src\桌面分身\pet.cs`，`OnPaint` 之前新增 `protected override void WndProc(ref Message m)`：
- 收到 `0x02E0` 时读高 16 位取新 DPI，按 `新DPI/旧DPI` 重算 `uiScale` 与窗口尺寸；
- 用 `Marshal.ReadInt32(m.LParam, 0..12)` 取系统建议矩形，`SetWindowPos(..., SWP_NOZORDER|SWP_NOACTIVATE|SWP_NOCOPYBITS)` 落位；
- `ForceLayer()` 重新贴 layered 属性，`Invalidate()` 重画，`m.Result=0` 表示已处理。

验证：判据复跑 W3 由 FAIL 变 PASS（`WM_DPICHANGED=3`），重编 exe 后进程数 1，`/ping` 回 `OK|道|116|192.168.2.115|8848`。

## 四、还没做的（如实记）

- 只验了"代码里接了消息 + 进程能起 + ping 正常"，**没真把窗口拖到第二块不同 DPI 的显示器上肉眼验**（本机只有一块内置屏 + 一块外接，缩放同为 100%，条件不具备）。这条留给有双 DPI 环境时补。
- `WM_GETDPISCALEDSIZE` 没接：现在完全按系统建议矩形走，够用；如果以后要固定设计尺寸，再接这个。
- 子控件（右键菜单、ToolStrip）在 DPI 变化后没有单独重排，仍由 WinForms 自己按字体缩放，可能有 1–2px 偏差，未量化。
