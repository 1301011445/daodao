# 量「点一下道」窗口本身有没有抖：点击前后各 3 秒按 60Hz 读窗口矩形
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class W {
  [StructLayout(LayoutKind.Sequential)] public struct R { public int L, T, Rt, B; }
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out R r);
  [DllImport("user32.dll")] public static extern void mouse_event(uint f, uint dx, uint dy, uint d, UIntPtr e);
  [DllImport("user32.dll")] public static extern bool SetCursorPos(int x, int y);
}
"@
$proc = Get-Process -Name '道' -ErrorAction Stop | Where-Object { $_.MainWindowHandle -ne 0 }
$h = $proc.MainWindowHandle
$r = New-Object W+R
[W]::GetWindowRect($h, [ref]$r) | Out-Null
$w = $r.Rt - $r.L; $hh = $r.B - $r.T
Write-Output ("窗口 hwnd={0} 位置=({1},{2}) 尺寸={3}x{4}" -f $h, $r.L, $r.T, $w, $hh)

function Sample-Seq([string]$tag) {
  $res = @()
  $sw = [System.Diagnostics.Stopwatch]::StartNew()
  while ($sw.Elapsed.TotalSeconds -lt 3.2) {
    [W]::GetWindowRect($h, [ref]$r) | Out-Null
    $res += [pscustomobject]@{ t = [math]::Round($sw.Elapsed.TotalSeconds, 2); x = $r.L; y = $r.T; w = $r.Rt - $r.L; h = $r.B - $r.T }
    Start-Sleep -Milliseconds 16
  }
  $res | Export-Csv -NoTypeInformation -Encoding UTF8 ("F:\Daodao\自我状态\窗口采样_" + $tag + ".csv")
  $ys = $res | ForEach-Object { $_.y }
  $dys = @(); for ($i = 1; $i -lt $ys.Count; $i++) { $dys += ($ys[$i] - $ys[$i - 1]) }
  $flips = 0; for ($i = 1; $i -lt $dys.Count; $i++) { if ($dys[$i] * $dys[$i - 1] -lt 0) { $flips++ } }
  $xs = $res | ForEach-Object { $_.x }
  $ws = $res | ForEach-Object { $_.w }
  Write-Output ("{0}：{1} 次采样 y∈[{2},{3}] 行程={4}px 逐次最大Δy={5}px 换向={6}  x∈[{7},{8}]  w∈[{9},{10}]" -f `
    $tag, $res.Count, ($ys | Measure-Object -Minimum).Minimum, ($ys | Measure-Object -Maximum).Maximum, `
    (($ys | Measure-Object -Maximum).Maximum - ($ys | Measure-Object -Minimum).Minimum), `
    ($dys | ForEach-Object { [math]::Abs($_) } | Measure-Object -Maximum).Maximum, $flips, `
    ($xs | Measure-Object -Minimum).Minimum, ($xs | Measure-Object -Maximum).Maximum, `
    ($ws | Measure-Object -Minimum).Minimum, ($ws | Measure-Object -Maximum).Maximum)
  return $res
}

Sample-Seq '点击前' | Out-Null
[int]$cx = $r.L + [int]($w / 2); [int]$cy = $r.T + [int]($hh / 2)
Write-Output ("点击坐标 ({0},{1})" -f $cx, $cy)
[W]::SetCursorPos($cx, $cy) | Out-Null
Start-Sleep -Milliseconds 60
[W]::mouse_event(0x0002, 0, 0, 0, [UIntPtr]::Zero)   # LEFTDOWN
Start-Sleep -Milliseconds 50
[W]::mouse_event(0x0004, 0, 0, 0, [UIntPtr]::Zero)   # LEFTUP
Sample-Seq '点击后' | Out-Null
