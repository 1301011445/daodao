# 开机瘦身（需管理员权限，双击右键"以管理员身份运行"或用 PowerShell 管理员窗口执行）
# 只做三件事，全部可逆；改前会把原值打印出来并存进 F:\Daodao\开机优化备份\还原说明.txt
# 1) 遥测服务 DiagTrack：Auto -> Manual 并停止
# 2) 关掉 Conexant 音频面板三件套的开机自启（只关面板，音频驱动与服务不动，出声不受影响）
# 3) 打印当前状态核对
$ErrorActionPreference = 'Continue'
if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
  Write-Host '这不是管理员窗口，什么都没改。请用管理员身份重开再跑。' -ForegroundColor Yellow
  exit 1
}
$bk = 'F:\Daodao\开机优化备份'
if (-not (Test-Path $bk)) { New-Item -ItemType Directory -Force -Path $bk | Out-Null }
$note = @()

# 1) DiagTrack
$svc = Get-CimInstance Win32_Service -Filter "Name='DiagTrack'"
$note += "DiagTrack 原启动类型: $($svc.StartMode) / 状态: $($svc.State)"
Stop-Service DiagTrack -Force -ErrorAction SilentlyContinue
Set-Service DiagTrack -StartupType Manual -ErrorAction SilentlyContinue
$svc2 = Get-CimInstance Win32_Service -Filter "Name='DiagTrack'"
$note += "DiagTrack 改后: $($svc2.StartMode) / $($svc2.State)  还原: Set-Service DiagTrack -StartupType Automatic; Start-Service DiagTrack"

# 2) Conexant 三件套（HKLM Run 项，Task Manager 靠 HKLM\...\StartupApproved\Run 判定禁用）
$saHK = 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run'
if (-not (Test-Path $saHK)) { New-Item -Path $saHK -Force | Out-Null }
foreach ($n in @('ForteConfig','SmartAudio','cAudioFilterAgent')) {
  $old = (Get-ItemProperty $saHK -ErrorAction SilentlyContinue).$n
  $note += "HKLM StartupApproved  $n  原值: " + (($old -join ",") -replace "^,$","") + "（空=原来没这一项，默认启用）"
  New-ItemProperty -Path $saHK -Name $n -Value ([byte[]](3,0,0,0,0,0,0,0,0,0,0,0)) -PropertyType Binary -Force | Out-Null
  $note += "  -> 已禁用。还原: Remove-ItemProperty '$saHK' -Name '$n'"
}

# 3) 核对
Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run' -ErrorAction SilentlyContinue |
  Select-Object -Property * -ExcludeProperty PS* | Format-Table -AutoSize

$note | Set-Content -LiteralPath (Join-Path $bk '还原说明.txt') -Encoding UTF8 -Force
$note | ForEach-Object { Write-Host $_ }
Write-Host ''
Write-Host '完成。还原说明已写入 F:\Daodao\开机优化备份\还原说明.txt' -ForegroundColor Green
