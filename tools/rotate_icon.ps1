# 程序版本：v0.1 | 2026-11-22 | 基线建档（此前无版本头）
# 每日图标轮换：按一年中的第几天挑当天的 ico，覆盖 current.ico，改桌面/开始菜单快捷方式图标
$ErrorActionPreference = 'Continue'
$root = 'F:\Daodao'
$icoDir = Join-Path $root 'icons\ico'
$cur = Join-Path $root 'icons\current.ico'
$log = Join-Path $root 'github_sync.log'

if (-not (Test-Path -LiteralPath $icoDir)) { exit 0 }

$list = @(Get-ChildItem -LiteralPath $icoDir -Filter '*.ico' -File | Sort-Object Name)
if ($list.Count -eq 0) { exit 0 }

$curHash = ''
if (Test-Path -LiteralPath $cur) { $curHash = (Get-FileHash -LiteralPath $cur -Algorithm SHA256).Hash }

# 从当天序号往后找，跳过与 current.ico 内容相同的，保证每天都真换
$idx = ((Get-Date).DayOfYear) % $list.Count
$pick = $null
for ($i = 0; $i -lt $list.Count; $i++) {
    $cand = $list[($idx + $i) % $list.Count]
    if ((Get-FileHash -LiteralPath $cand.FullName -Algorithm SHA256).Hash -ne $curHash) { $pick = $cand; break }
}
if (-not $pick) { $pick = $list[$idx] }

Copy-Item -LiteralPath $pick.FullName -Destination $cur -Force
# 复制会保留源文件时间，这里显式写成本轮时间，便于判断"今天是否真换"
(Get-Item -LiteralPath $cur).LastWriteTime = Get-Date

# 当天存档一份，方便回溯
$arch = Join-Path $root ('icons\dao_' + (Get-Date -f 'yyyyMMdd') + '.ico')
Copy-Item -LiteralPath $pick.FullName -Destination $arch -Force

# 改所有指向 道.exe 的快捷方式（桌面 + 开始菜单）
$changed = 0
$targets = @()
$targets += [Environment]::GetFolderPath('Desktop')
$targets += [Environment]::GetFolderPath('CommonDesktopDirectory')
$targets += (Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs')
$targets += (Join-Path $env:ProgramData 'Microsoft\Windows\Start Menu\Programs')

$shell = New-Object -ComObject WScript.Shell
foreach ($d in $targets) {
    if (-not (Test-Path -LiteralPath $d)) { continue }
    $lnks = @(Get-ChildItem -LiteralPath $d -Filter '*.lnk' -File -Recurse -ErrorAction SilentlyContinue)
    foreach ($l in $lnks) {
        try { $sc = $shell.CreateShortcut($l.FullName) } catch { continue }
        $tp = [string]$sc.TargetPath
        $ar = [string]$sc.Arguments
        if ($tp -match '道\.exe' -or $ar -match 'game_mode') {
            if ($sc.IconLocation -ne ($cur + ',0')) {
                $sc.IconLocation = $cur + ',0'
                $sc.Save()
                $changed++
            }
        }
    }
}

$ie4 = Join-Path $env:SystemRoot 'System32\ie4uinit.exe'; if (Test-Path -LiteralPath $ie4) { & $ie4 -show 2>&1 | Out-Null }

$line = "[{0}] 图标轮换 -> {1}（{2}，每年第 {3} 天），{4} 字节，sha={5}，快捷方式改了 {6} 处" -f (Get-Date -f 'yyyy-MM-dd HH:mm:ss'), $pick.BaseName, $pick.Name, (Get-Date).DayOfYear, $pick.Length, ((Get-FileHash -LiteralPath $cur -Algorithm SHA256).Hash.Substring(0,12)), $changed
Write-Output $line
Add-Content -LiteralPath $log -Value $line -Encoding UTF8
