# daily_bing.ps1 — 每天取一张必应壁纸设成桌面，标题记进 today.json 给「道」念
# 由计划任务 DaoWallpaper 每天 07:35 调用，也可以右键「换张新壁纸」随时跑
$ErrorActionPreference = 'Stop'
$logPath = 'F:\Daodao\壁纸日志.txt'

function Log($m) {
    try { Add-Content -LiteralPath $logPath -Value ((Get-Date -Format 'yyyy-MM-dd HH:mm:ss') + '  ' + $m) -Encoding UTF8 } catch {}
}

try {
    $pics = [Environment]::GetFolderPath('MyPictures')
    if (-not $pics) { $pics = Join-Path $env:USERPROFILE 'Pictures' }
    $dir = Join-Path $pics '每日壁纸'
    if (-not (Test-Path -LiteralPath $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }

    $today = Get-Date -Format 'yyyyMMdd'
    $jsonPath = Join-Path $dir 'today.json'
    $jpg = Join-Path $dir ('bing_' + $today + '.jpg')

    $title = ''
    if (-not (Test-Path -LiteralPath $jpg)) {
        $api = 'https://www.bing.com/HPImageArchive.aspx?format=js&idx=0&n=1&mkt=zh-CN'
        $resp = Invoke-WebRequest -Uri $api -UseBasicParsing -TimeoutSec 20
        $obj = $resp.Content | ConvertFrom-Json
        $img = $obj.images[0]
        $title = $img.title
        $url = 'https://www.bing.com' + $img.urlbase + '_UHD.jpg'
        Invoke-WebRequest -Uri $url -OutFile $jpg -UseBasicParsing -TimeoutSec 90
        $meta = [ordered]@{ date = $today; title = $title; copyright = $img.copyright; url = $url; path = $jpg }
        ($meta | ConvertTo-Json -Depth 3) | Out-File -LiteralPath $jsonPath -Encoding utf8
        Log ('新壁纸已下载：' + $title + ' → ' + $jpg)
    } else {
        if (Test-Path -LiteralPath $jsonPath) {
            $old = Get-Content -LiteralPath $jsonPath -Raw -Encoding UTF8 | ConvertFrom-Json
            $title = $old.title
        }
        Log ('今天的壁纸已经有了：' + $title)
    }

    # 换成桌面壁纸（只换图，不动你原本的填充方式）
    if (-not ('DaoWallApi' -as [type])) {
        Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
public class DaoWallApi {
    [DllImport("user32.dll", SetLastError = true, CharSet = CharSet.Auto)]
    public static extern int SystemParametersInfo(int uAction, int uParam, string lpvParam, int fuWinIni);
}
"@
    }
    $ok = [DaoWallApi]::SystemParametersInfo(20, 0, $jpg, 3)
    if ($ok -ne 1) {
        $err = [ComponentModel.Win32Exception][Runtime.InteropServices.Marshal]::GetLastWin32Error()
        Log ('设置壁纸失败：' + $err.Message)
        exit 1
    }
    Log ('桌面已换成：' + $title)
    Write-Output ('OK|' + $title + '|' + $jpg)
}
catch {
    Log ('出错：' + $_.Exception.Message)
    Write-Output ('ERR|' + $_.Exception.Message)
    exit 1
}