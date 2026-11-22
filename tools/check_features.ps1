# 程序版本：v0.1 | 2026-11-22 | 基线建档（此前无版本头）
# check_features.ps1 — 「道」功能体检：一条命令看出哪块功能缺件
# 用法: powershell -NoProfile -ExecutionPolicy Bypass -File check_features.ps1
param([switch]$Quiet)

$root = 'F:\Daodao'
$script:okCount = 0
$script:badList = @()

function Row($label, $state, $note) {
    $tag = '[缺]  '
    if ($state) { $tag = '[OK]  ' }
    $tail = ''
    if ($note) { $tail = '  ' + $note }
    if (-not $Quiet) { Write-Output ($tag + $label + $tail) }
}

function NeedFile($label, $path) {
    if (Test-Path -LiteralPath $path) {
        $script:okCount = $script:okCount + 1
        Row $label $true ''
        return
    }
    $script:badList = $script:badList + @($label + ' -> ' + $path)
    Row $label $false $path
}

function NeedDir($label, $path, $minCount) {
    if (-not (Test-Path -LiteralPath $path)) {
        $script:badList = $script:badList + @($label + ' -> ' + $path)
        Row $label $false '目录不存在'
        return
    }
    $n = @(Get-ChildItem -LiteralPath $path -File -ErrorAction SilentlyContinue).Count
    if ($n -ge $minCount) {
        $script:okCount = $script:okCount + 1
        Row $label $true ($n.ToString() + ' 个')
        return
    }
    $script:badList = $script:badList + @($label + ' 数量不足 ' + $n)
    Row $label $false ($n.ToString() + '/' + $minCount.ToString())
}

if (-not $Quiet) { Write-Output '=== 1. 程序本体 ===' }
NeedFile '道.exe（桌面端）' (Join-Path $root '道.exe')
NeedFile 'pet.cs（源码）'   (Join-Path $root 'src\桌面分身\pet.cs')
NeedDir  'icons\ico 图标'   (Join-Path $root 'icons\ico') 10
NeedFile 'icons\current.ico' (Join-Path $root 'icons\current.ico')
NeedFile '记忆.txt'         (Join-Path $root '记忆.txt')

if (-not $Quiet) { Write-Output ''; Write-Output '=== 2. 功能脚本 ===' }
NeedFile 'daily_bing.ps1（换壁纸）' (Join-Path $root 'daily_bing.ps1')
NeedFile 'hear.py（听写/语音识别）'  (Join-Path $root 'hear.py')
NeedFile 'backup.ps1（备份）'       (Join-Path $root 'backup.ps1')
NeedFile 'tools\daily_sync.ps1（每日同步）' (Join-Path $root 'tools\daily_sync.ps1')
NeedFile 'tools\rotate_icon.ps1（图标轮换）' (Join-Path $root 'tools\rotate_icon.ps1')
NeedFile 'tools\pack_resources.ps1（打资源）' (Join-Path $root 'tools\pack_resources.ps1')
NeedFile 'tools\build_exe.ps1（编译）' (Join-Path $root 'tools\build_exe.ps1')

if (-not $Quiet) { Write-Output ''; Write-Output '=== 3. 语音链路 ===' }
$voice = Join-Path $env:TEMP 'daovoice'
NeedFile '语音辅助 say.py'      (Join-Path $voice 'say.py')
NeedFile '语音播放 play.ps1'    (Join-Path $voice 'play.ps1')
NeedFile '语音播放 play_mp3.py' (Join-Path $voice 'play_mp3.py')
$mp3n = 0
if (Test-Path -LiteralPath $voice) { $mp3n = @(Get-ChildItem -LiteralPath $voice -Filter '*.mp3' -ErrorAction SilentlyContinue).Count }
Row '语音缓存' ($mp3n -gt 0) ($mp3n.ToString() + ' 条')

if (-not $Quiet) { Write-Output ''; Write-Output '=== 4. 手机端 ===' }
NeedFile 'dao.html（手机页面）' (Join-Path $root 'src\_apk\assets\dao.html')
NeedFile '道.apk（安装包）'      (Join-Path $root '道.apk')
$mf = Join-Path $root 'src\_apk\AndroidManifest.xml'
NeedFile 'AndroidManifest.xml'  $mf
if (Test-Path -LiteralPath $mf) {
    $mx = [IO.File]::ReadAllText($mf, [Text.Encoding]::UTF8)
    $vc = '?'
    if ($mx -match 'versionCode="(\d+)"') { $vc = $Matches[1] }
    Row '手机端版本号' $true ('versionCode=' + $vc)
}

if (-not $Quiet) { Write-Output ''; Write-Output '=== 5. 壁纸 ===' }
$pics = [Environment]::GetFolderPath('MyPictures')
NeedFile '壁纸记录 today.json' (Join-Path $pics '每日壁纸\today.json')
$wall = ''
try { $wall = (Get-ItemProperty -Path 'HKCU:\Control Panel\Desktop' -Name Wallpaper).Wallpaper } catch { $wall = '' }
if ($wall.Length -gt 0 -and (Test-Path -LiteralPath $wall)) {
    $script:okCount = $script:okCount + 1
    Row '桌面壁纸已设' $true (Split-Path -Leaf $wall)
} else {
    $script:badList = $script:badList + '桌面壁纸未设'
    Row '桌面壁纸已设' $false $wall
}

if (-not $Quiet) { Write-Output ''; Write-Output '=== 6. 运行状态 ===' }
$proc = Get-Process -Name '道' -ErrorAction SilentlyContinue
if ($proc) {
    $script:okCount = $script:okCount + 1
    Row '道 进程在跑' $true ('PID ' + $proc.Id)
} else {
    $script:badList = $script:badList + '道 进程没起'
    Row '道 进程在跑' $false ''
}
$ping = ''
try { $ping = (Invoke-WebRequest -Uri 'http://127.0.0.1:8848/ping' -TimeoutSec 4 -UseBasicParsing).Content } catch { $ping = '' }
if ($ping -match 'OK') {
    $script:okCount = $script:okCount + 1
    Row '互通端口 8848' $true $ping
} else {
    $script:badList = $script:badList + '端口不通'
    Row '互通端口 8848' $false ''
}

if (-not $Quiet) { Write-Output ''; Write-Output '=== 7. 定时任务 ===' }
$sch = Join-Path $env:SystemRoot 'System32\schtasks.exe'
foreach ($task in @('DaoWallpaper','DaoIconRotate','DaoDailyAuto','DaoPageUpdate','DaoGithubPush')) {
    $null = & $sch /query /tn $task /fo LIST 2>&1
    if ($LASTEXITCODE -eq 0) {
        $script:okCount = $script:okCount + 1
        Row ('计划任务 ' + $task) $true ''
    } else {
        $script:badList = $script:badList + @('计划任务缺 ' + $task)
        Row ('计划任务 ' + $task) $false ''
    }
}

if (-not $Quiet) { Write-Output ''; Write-Output '=== 汇总 ===' }
Write-Output ('正常 ' + $script:okCount + ' 项，缺 ' + $script:badList.Count + ' 项')
if ($script:badList.Count -gt 0) {
    Write-Output '需要补的：'
    foreach ($b in $script:badList) { Write-Output ('  - ' + $b) }
    exit 1
}
Write-Output '全部齐全'
exit 0