# 手机装包：等设备接上 -> 校验版本 -> 安装 -> 启动 -> 回读自检
# 用法：powershell -File F:\Daodao\tools\手机装包.ps1
# 前提：手机打开「开发者选项 → USB 调试」，用数据线连上电脑，手机上点「允许调试」。
param([int]$WaitSec = 120, [string]$Apk = 'F:\Daodao\道.apk')

$adb = 'E:\AndroidTools\sdk\platform-tools\adb.exe'
if (-not (Test-Path -LiteralPath $adb)) { Write-Output 'NO_ADB'; exit 1 }
if (-not (Test-Path -LiteralPath $Apk)) { Write-Output 'NO_APK'; exit 1 }

$apkVer = (& 'E:\AndroidTools\sdk\build-tools\34.0.0\aapt2.exe' dump badging $Apk |
           Select-String -Pattern 'versionCode=').Line
Write-Output ("APK: " + $Apk + " " + $apkVer)

# 等设备
$deadline = (Get-Date).AddSeconds($WaitSec)
$serial = $null
while ((Get-Date) -lt $deadline) {
    $lines = & $adb devices | Select-Object -Skip 1 | Where-Object { $_ -match "`tdevice" }
    if ($lines) { $serial = ($lines[0] -split "`t")[0]; break }
    Start-Sleep -Seconds 3
}
if (-not $serial) { Write-Output 'NO_DEVICE（数据线没连上，或手机没允许调试）'; exit 2 }
Write-Output ("设备: " + $serial)

# 装上
& $adb -s $serial install -r $Apk 2>&1 | ForEach-Object { Write-Output ("install: " + $_) }

# 启动
& $adb -s $serial shell am start -n com.daodao.pet/.Launcher0 2>&1 | ForEach-Object { Write-Output ("start: " + $_) }
Start-Sleep -Seconds 8

# 回读装上的版本 + 程序自己写的自检
$pv = (& $adb -s $serial shell dumpsys package com.daodao.pet | Select-String -Pattern 'versionCode').Line
Write-Output ("设备上的版本: " + $pv)

& $adb -s $serial pull /sdcard/手机自检.txt 'F:\Daodao\手机自检.txt' 2>&1 |
    ForEach-Object { Write-Output ("pull: " + $_) }
if (Test-Path -LiteralPath 'F:\Daodao\手机自检.txt') {
    Write-Output '--- 手机自检 ---'
    Get-Content -LiteralPath 'F:\Daodao\手机自检.txt' -Encoding UTF8 -TotalCount 6
}
Write-Output 'DONE'
