param(
  [string]$Png = 'F:\Daodao\selfcheck.png',
  [int]$X = 300,
  [int]$Y = 300,
  [int]$ProcId = 0
)
Add-Type -AssemblyName System.Drawing

Add-Type -ReferencedAssemblies 'System.Drawing' -TypeDefinition @'
using System;
using System.Drawing;
using System.Runtime.InteropServices;
using System.Text;

public class DaoLayer {
    [StructLayout(LayoutKind.Sequential)]
    public struct POINT { public int x, y; public POINT(int a, int b) { x = a; y = b; } }
    [StructLayout(LayoutKind.Sequential)]
    public struct SIZE { public int cx, cy; public SIZE(int a, int b) { cx = a; cy = b; } }
    [StructLayout(LayoutKind.Sequential, Pack = 1)]
    public struct BLENDFUNCTION { public byte Op; public byte Flags; public byte Alpha; public byte Format; }

    [DllImport("user32.dll", SetLastError = true)]
    public static extern bool UpdateLayeredWindow(IntPtr hwnd, IntPtr hdcDst, ref POINT ptDst, ref SIZE size,
        IntPtr hdcSrc, ref POINT ptSrc, int crKey, ref BLENDFUNCTION blend, int flags);
    [DllImport("user32.dll")] public static extern IntPtr GetDC(IntPtr h);
    [DllImport("user32.dll")] public static extern int ReleaseDC(IntPtr h, IntPtr dc);
    [DllImport("gdi32.dll")] public static extern IntPtr CreateCompatibleDC(IntPtr dc);
    [DllImport("gdi32.dll")] public static extern bool DeleteDC(IntPtr dc);
    [DllImport("gdi32.dll")] public static extern IntPtr SelectObject(IntPtr dc, IntPtr obj);
    [DllImport("gdi32.dll")] public static extern bool DeleteObject(IntPtr obj);
    [DllImport("user32.dll")] public static extern int GetWindowLong(IntPtr h, int i);
    [DllImport("user32.dll")] public static extern int SetWindowLong(IntPtr h, int i, int v);
    [DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc cb, IntPtr p);
    [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
    [DllImport("user32.dll")] public static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
    public delegate bool EnumProc(IntPtr h, IntPtr p);

    public static IntPtr ByPid(uint pid) {
        IntPtr found = IntPtr.Zero;
        EnumWindows((h, p) => {
            uint id; GetWindowThreadProcessId(h, out id);
            if (id == pid) {
                StringBuilder tt = new StringBuilder(256);
                GetWindowText(h, tt, 256);
                if (tt.ToString() == "DaoPetWindow") { found = h; return false; }
            }
            return true;
        }, IntPtr.Zero);
        return found;
    }

    public static bool Blit(IntPtr hwnd, string pngPath, int x, int y) {
        int ex = GetWindowLong(hwnd, -20);
        if ((ex & 0x00080000) == 0) SetWindowLong(hwnd, -20, ex | 0x00080000);
        Bitmap bmp = new Bitmap(pngPath);
        Bitmap argb = new Bitmap(bmp.Width, bmp.Height, System.Drawing.Imaging.PixelFormat.Format32bppArgb);
        Graphics g = Graphics.FromImage(argb);
        g.DrawImage(bmp, 0, 0);
        g.Dispose();
        for (int yy = 0; yy < argb.Height; yy++) {
            for (int xx = 0; xx < argb.Width; xx++) {
                Color c = argb.GetPixel(xx, yy);
                if (c.R > 240 && c.G < 20 && c.B > 240) argb.SetPixel(xx, yy, Color.FromArgb(0, 0, 0, 0));
            }
        }
        IntPtr screenDc = GetDC(IntPtr.Zero);
        IntPtr memDc = CreateCompatibleDC(screenDc);
        IntPtr hBitmap = argb.GetHbitmap(Color.FromArgb(0));
        IntPtr old = SelectObject(memDc, hBitmap);
        POINT dst = new POINT(x, y);
        POINT src = new POINT(0, 0);
        SIZE size = new SIZE(argb.Width, argb.Height);
        BLENDFUNCTION bf = new BLENDFUNCTION();
        bf.Op = 0; bf.Flags = 0; bf.Alpha = 255; bf.Format = 1;
        bool ok = UpdateLayeredWindow(hwnd, screenDc, ref dst, ref size, memDc, ref src, 0, ref bf, 2);
        int err = Marshal.GetLastWin32Error();
        SelectObject(memDc, old);
        DeleteObject(hBitmap);
        DeleteDC(memDc);
        ReleaseDC(IntPtr.Zero, screenDc);
        argb.Dispose();
        bmp.Dispose();
        Console.WriteLine("UpdateLayeredWindow=" + ok + " err=" + err + " size=" + size.cx + "x" + size.cy);
        return ok;
    }
}
'@

if ($ProcId -le 0) {
    $proc = Get-Process | Where-Object { $_.ProcessName -eq [char]0x9059 + [char]0xFEFF } | Select-Object -First 1
}
if ($ProcId -gt 0) { $proc = Get-Process -Id $ProcId -ErrorAction Stop }
if ($null -eq $proc) {
    $proc = Get-Process | Where-Object { $_.MainModule.FileName -like '*\Daodao\*.exe' } | Select-Object -First 1
}
Write-Output "PID=$($proc.Id) NAME=$($proc.ProcessName)"
$h = [DaoLayer]::ByPid([uint32]$proc.Id)
Write-Output "HWND=$h"
if ($h -eq [IntPtr]::Zero) { Write-Output 'FIND_FAIL'; exit 1 }
[DaoLayer]::Blit($h, $Png, $X, $Y) | Out-Null
Write-Output 'BLIT_DONE'
