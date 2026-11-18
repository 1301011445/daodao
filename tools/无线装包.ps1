# 无线装包（红米 12 Turbo / Android 13+）
# 一次配对，之后可复用；端口重启后会变。
# 用法：
#   powershell -File F:\Daodao\tools\无线装包.ps1 -PairAddr 192.168.2.x:41234 -PairCode 123456 -ConnectAddr 192.168.2.x:5555
#   已配对过只需： -ConnectAddr 192.168.2.x:port
param(
    [string]$PairAddr = '',
    [string]$PairCode = '',
    [string]$ConnectAddr = '',
    [string]$Apk = 'F:\Daodao\道.apk'
)

$adb = 'E:\AndroidTools\sdk\platform-tools\adb.exe'
if (-not (Test-Path -LiteralPath $adb)) { Write-Output 'NO_ADB'; exit 1 }

if ($PairAddr) {
    Write-Output "配对 $PairAddr ..."
    "`n$PairCode" | & $adb pair $PairAddr 2>&1 | ForEach-Object { Write-Output ("pair: " + $_) }
}

if (-not $ConnectAddr) {
    $svc = & $adb mdns services 2>&1 | Select-String -Pattern '_adb-tls-connect'
    if ($svc) {
        $ConnectAddr = ($svc.Line -split '\s+')[-1]
        Write-Output ("mDNS 发现: " + $ConnectAddr)
    }
}
if (-not $ConnectAddr) { Write-Output 'NO_ADDR（手机「无线调试」页上的 IP:端口 没给，也没扫到）'; exit 2 }

Write-Output "连接 $ConnectAddr ..."
& $adb connect $ConnectAddr 2>&1 | ForEach-Object { Write-Output ("connect: " + $_) }
Start-Sleep -Seconds 2
& $adb devices -l 2>&1 | ForEach-Object { Write-Output $_ }

$serial = (& $adb devices | Select-Object -Skip 1 | Where-Object { $_ -match 'device$' } | Select-Object -First 1)
if (-not $serial) { Write-Output '未连上，停下'; exit 3 }

if (Test-Path -LiteralPath $Apk) {
    & $adb install -r $Apk 2>&1 | ForEach-Object { Write-Output ("install: " + $_) }
    & $adb shell am start -n com.daodao.pet/.Launcher0 2>&1 | Out-Null
    Start-Sleep -Seconds 8
    & $adb pull /sdcard/手机自检.txt 'F:\Daodao\手机自检.txt' 2>&1 | ForEach-Object { Write-Output ("pull: " + $_) }
    if (Test-Path -LiteralPath 'F:\Daodao\手机自检.txt') {
        Write-Output '--- 手机自检 ---'
        Get-Content -LiteralPath 'F:\Daodao\手机自检.txt' -Encoding UTF8 -TotalCount 6
    }
}
Write-Output 'DONE'
