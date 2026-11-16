# notify.ps1 — 在桌面右下角弹一条托盘提示（不弹窗、不抢焦点，几秒后自己消失）
# 2026-11-16 新增：邮件通道没通时的即时反馈手段
# 用法：powershell -ExecutionPolicy Bypass -File notify.ps1 -Title "道 体检" -Text "结论：正常"

param(
    [string]$Title = '道',
    [string]$Text = '',
    [string]$FromFile = '',
    [int]$Seconds = 8
)

$ErrorActionPreference = 'Stop'
if (-not [string]::IsNullOrWhiteSpace($FromFile) -and (Test-Path -LiteralPath $FromFile)) {
    $fl = @([IO.File]::ReadAllText($FromFile, (New-Object Text.UTF8Encoding($false))) -split "`r?`n")
    if ($fl.Count -gt 0 -and $fl[0].Trim()) { $Title = $fl[0].Trim() }
    if ($fl.Count -gt 1) { $Text = ($fl[1..($fl.Count - 1)] -join "`r`n") }
}
if ([string]::IsNullOrWhiteSpace($Text)) { $Text = '这一轮跑完了，没有内容。' }

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$ni = New-Object System.Windows.Forms.NotifyIcon
$ni.Icon = [System.Drawing.SystemIcons]::Information
$ni.Text = '道'
$ni.Visible = $true
$ni.BalloonTipTitle = $Title
$ni.BalloonTipText = $Text
$ni.BalloonTipIcon = [System.Windows.Forms.ToolTipIcon]::Info
$ni.ShowBalloonTip($Seconds * 1000)

Start-Sleep -Seconds $Seconds
$ni.Visible = $false
$ni.Dispose()
Write-Output "已提示：$Title"
