# 程序版本：v0.3 | 2026-11-28 | 加 System.Speech.dll WPF 目录引用，支持本机 SAPI 短句合成
# Build the desktop pet exe from source, then swap and restart it.
# Output: one line "BUILD_OK size=... proc=..." on success, "BUILD_FAIL ..." otherwise.
$ErrorActionPreference = 'Stop'
$root = 'F:\Daodao'
$src  = Join-Path $root 'src\桌面分身\pet.cs'
$manifest = Join-Path $root 'src\桌面分身\pet.manifest'
$icon = Join-Path $root 'icons\current.ico'
$outNew = Join-Path $root 'src\桌面分身\_build_tmp.exe'
$exe  = Join-Path $root '道.exe'
$csc  = Join-Path $env:SystemRoot 'Microsoft.NET\Framework64\v4.0.30319\csc.exe'
if (-not (Test-Path -LiteralPath $csc)) { $csc = Join-Path $env:SystemRoot 'Microsoft.NET\Framework\v4.0.30319\csc.exe' }
if (-not (Test-Path -LiteralPath $csc)) { Write-Output 'BUILD_FAIL no csc'; exit 1 }
if (-not (Test-Path -LiteralPath $src)) { Write-Output 'BUILD_FAIL no pet.cs'; exit 1 }

$args = @('/nologo', '/target:winexe', '/optimize+', ('/out:' + $outNew))
if (Test-Path -LiteralPath $manifest) { $args += ('/win32manifest:' + $manifest) }
if (Test-Path -LiteralPath $icon) { $args += ('/win32icon:' + $icon) }

# 嵌入形象/姿势/走路帧/话术等资源：这些是程序运行时用 ResStream 直接读的，
# 不嵌的话 exe 只有代码，桌面上就画不出形象（v31/v32 出的就是这个毛病）
$bundle = Join-Path $root 'src\桌面分身\_bundle'
$packer = Join-Path $root 'tools\pack_resources.ps1'
$needPack = $true
if (Test-Path -LiteralPath $bundle) {
    if (@(Get-ChildItem -LiteralPath $bundle -File).Count -ge 63) { $needPack = $false }
}
if ($needPack) {
    if (-not (Test-Path -LiteralPath $packer)) { Write-Output 'BUILD_FAIL no pack_resources.ps1'; exit 1 }
    $psExe = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
    $packLog = & $psExe -NoProfile -ExecutionPolicy Bypass -File $packer 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Output ('BUILD_FAIL resource pack code=' + $LASTEXITCODE)
        foreach ($l in $packLog) { Write-Output ('  ' + $l) }
        exit 1
    }
}
$resCount = 0
foreach ($f in (Get-ChildItem -LiteralPath $bundle -File)) {
    $args += ('/resource:' + $f.FullName)
    $resCount++
}

$args += '/r:System.dll'
$args += '/r:System.Windows.Forms.dll'
$args += '/r:System.Drawing.dll'
$args += '/r:' + (Join-Path $env:SystemRoot 'Microsoft.NET\Framework64\v4.0.30319\WPF\System.Speech.dll')
$args += $src

if (Test-Path -LiteralPath $outNew) { Remove-Item -LiteralPath $outNew -Force -ErrorAction SilentlyContinue }
$logOut = & $csc @args 2>&1
$code = $LASTEXITCODE
if ($code -ne 0 -or -not (Test-Path -LiteralPath $outNew)) {
    Write-Output ('BUILD_FAIL code=' + $code)
    foreach ($l in $logOut) { Write-Output ('  ' + $l) }
    exit 1
}

# stop running pet so the exe can be replaced
Get-Process -Name '道' -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2
# 2026-11-22 修：原来用 Move-Item -Force 换包，目标已存在时不覆盖，报
# 「当文件已存在时，无法创建该文件」——编译成功了但 exe 换不上去。改成 Copy-Item -Force 覆盖 + 删临时件。
Copy-Item -LiteralPath $outNew -Destination $exe -Force
Remove-Item -LiteralPath $outNew -Force -ErrorAction SilentlyContinue
# 顺手清掉自愈冷却，免得「10 分钟内不重启」把新构建没起来遮住
$stamp = Join-Path $root '自我状态\.last_selfheal'
if (Test-Path -LiteralPath $stamp) { Remove-Item -LiteralPath $stamp -Force -ErrorAction SilentlyContinue }
Start-Process -FilePath $exe
Start-Sleep -Seconds 10
$n = @(Get-Process -Name '道' -ErrorAction SilentlyContinue).Count
Write-Output ('BUILD_OK size=' + (Get-Item -LiteralPath $exe).Length + ' proc=' + $n + ' res=' + $resCount)