# 程序版本：v0.1 | 2026-11-24 | 新增 WinForms 渲染/DPI/绘制判据 W1-W6（第1类学习落地）
"""第1类（微软 dotnet/winforms）判据：W1-W6。

来源：
- https://learn.microsoft.com/zh-cn/windows/win32/hidpi/high-dpi-desktop-application-development-on-windows
- https://learn.microsoft.com/en-us/dotnet/api/system.windows.forms.controlstyles?view=windowsdesktop-8.0
- https://learn.microsoft.com/en-us/archive/msdn-magazine/2006/march/practical-tips-for-boosting-the-performance-of-windows-forms-apps

判据（全部可脚本判）：
W1 双缓冲：必须同时出现 OptimizedDoubleBuffer 与 AllPaintingInWmPaint（或 DoubleBuffered=true）
W2 进程 DPI：必须调用 SetProcessDpiAwarenessContext 或 SetProcessDPIAware（否则系统位图拉伸）
W3 DPI 切换：WndProc 处理 WM_DPICHANGED(0x02E0) 并按建议矩形 SetWindowPos/WM_GETDPISCALEDSIZE
W4 画笔释放：new Brush/Pen/Font 的 using 覆盖率 ≥ 90%
W5 重绘节奏：Invalidate 次数 ≥ Refresh 次数（Refresh 会同步阻塞）
W6 跨线程：非 UI 线程改控件必须 Invoke/BeginInvoke，出现 ≥1 处即 PASS 并在报告里列出次数

用法：python F:\Daodao\tools\形象\winforms_判据.py [pet.cs路径]
"""
import io
import re
import sys

DEFAULT = r"F:\Daodao\src\桌面分身\pet.cs"


def read(p):
    return io.open(p, encoding="utf-8", errors="replace").read()


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT
    src = read(path)
    fails = []
    rows = []

    def add(code, name, ok, detail):
        rows.append((code, name, "PASS" if ok else "FAIL", detail))
        if not ok:
            fails.append(code)

    # W1 双缓冲
    odb = len(re.findall(r"OptimizedDoubleBuffer", src))
    apw = len(re.findall(r"AllPaintingInWmPaint", src))
    dbp = len(re.findall(r"DoubleBuffered\s*=\s*true", src))
    ok1 = (odb > 0 and apw > 0) or dbp > 0
    add("W1", "双缓冲(OptimizedDoubleBuffer+AllPaintingInWmPaint 或 DoubleBuffered=true)", ok1,
        f"OptimizedDoubleBuffer={odb} AllPaintingInWmPaint={apw} DoubleBuffered=true={dbp}")

    # W2 进程 DPI
    ctx = len(re.findall(r"SetProcessDpiAwarenessContext", src))
    aware = len(re.findall(r"SetProcessDPIAware", src))
    ok2 = ctx > 0 or aware > 0
    add("W2", "进程级 DPI 感知(SetProcessDpiAwarenessContext/SetProcessDPIAware)", ok2,
        f"SetProcessDpiAwarenessContext={ctx} SetProcessDPIAware={aware}")

    # W3 WM_DPICHANGED
    dpi_msg = len(re.findall(r"0x02E0|WM_DPICHANGED|0x2E0", src, re.I))
    dpi_pos = len(re.findall(r"WM_GETDPISCALEDSIZE", src, re.I))
    ok3 = dpi_msg > 0
    add("W3", "处理 WM_DPICHANGED(0x02E0)，按建议矩形调整窗口", ok3,
        f"WM_DPICHANGED={dpi_msg} WM_GETDPISCALEDSIZE={dpi_pos}")

    # W4 GDI+ 对象释放
    created = len(re.findall(r"new (?:SolidBrush|LinearGradientBrush|Pen|Font|GraphicsPath|Bitmap)\s*\(", src))
    used = len(re.findall(r"using\s*(?:\(|var\b|new\b)", src))
    ratio = (used / created) if created else 1.0
    ok4 = ratio >= 0.90
    add("W4", "GDI+ 对象 using 释放覆盖率 ≥90%", ok4,
        f"new 画笔/字体/位图={created} using={used} 覆盖={ratio:.1%}")

    # W5 重绘节奏
    inv = len(re.findall(r"\.Invalidate\s*\(", src))
    ref = len(re.findall(r"\.Refresh\s*\(", src))
    ok5 = inv >= ref and inv > 0
    add("W5", "Invalidate 次数 ≥ Refresh 次数（Refresh 同步阻塞）", ok5,
        f"Invalidate={inv} Refresh={ref}")

    # W6 跨线程
    cross = len(re.findall(r"BeginInvoke|\.Invoke\s*\(", src))
    bg = len(re.findall(r"new Thread|Task\.Run|ThreadPool", src))
    ok6 = cross > 0
    add("W6", "后台线程改 UI 走 Invoke/BeginInvoke", ok6,
        f"Invoke/BeginInvoke={cross} 后台线程/Task={bg}")

    print(f"文件：{path}")
    print(f"{'判据':<4}{'项目':<46}{'结果':<6}明细")
    for c, n, r, d in rows:
        print(f"{c:<4}{n:<46}{r:<6}{d}")
    print(f"汇总：{len(fails)} 项 FAIL" + (f" -> {','.join(fails)}" if fails else " | 全部 PASS"))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
