# check_and_feed.ps1 — 定期检查「道」的状态，并把一行结论写进 F:\Daodao\反馈.txt
# 2026-11-16 新增（用户要求：要有定期检查更新的程序，要及时反馈）
# 用法：powershell -ExecutionPolicy Bypass -File check_and_feed.ps1
# 退出码：0 正常；1 有问题（问题写在结论里）

param([switch]$Quiet)

$ErrorActionPreference = 'SilentlyContinue'
$root = 'F:\Daodao'
$feed = Join-Path $root '反馈.txt'
$now = Get-Date

# 轮次：中午 12 点前算体检轮，之后算更新轮
$round = '更新轮'
if ($now.Hour -lt 12) { $round = '体检轮' }

$issues = New-Object System.Collections.ArrayList

# 一、进程
$procs = @(Get-Process -Name '道')
$procInfo = "进程 $($procs.Count)"
if ($procs.Count -eq 0) { [void]$issues.Add('道没在跑') }
elseif ($procs.Count -gt 1) { [void]$issues.Add("进程开了 $($procs.Count) 个") }

# 二、同步服务 ping 取版本
$ver = '?'
try {
    $c = New-Object System.Net.Sockets.TcpClient
    $c.Connect('127.0.0.1', 8848)
    $st = $c.GetStream()
    $sw = New-Object System.IO.StreamWriter $st
    $sw.WriteLine('GET /ping HTTP/1.0')
    $sw.WriteLine('')
    $sw.Flush()
    $sr = New-Object System.IO.StreamReader $st
    $resp = $sr.ReadToEnd()
    $c.Close()
    $line = ($resp -split "`r?`n" | Where-Object { $_ -match 'OK\|' } | Select-Object -First 1)
    if ($line) { $ver = $line.Split('|')[2] } else { [void]$issues.Add('ping 没回 OK') }
} catch {
    [void]$issues.Add('ping 连不上')
}

# 三、数据文件行数
function Lines($path) {
    if (Test-Path -LiteralPath $path) { return @(Get-Content -LiteralPath $path).Count }
    return 0
}
$say  = Lines (Join-Path $root '我说的话.txt')
$know = Lines (Join-Path $root '知识库.txt')
$mem  = Lines (Join-Path $root '记忆.txt')

# 四、27 项功能体检
$feat = '未跑'
$cf = Join-Path $root 'tools\check_features.ps1'
if (Test-Path -LiteralPath $cf) {
    $ps51 = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
    $feat = (& $ps51 -NoProfile -ExecutionPolicy Bypass -File $cf -Quiet 2>&1 | Out-String).Trim()
    $feat = ($feat -split "`r?`n" | Where-Object { $_ -match '项' } | Select-Object -First 1)
    if ($feat -notmatch '缺 0 项') { [void]$issues.Add('功能体检有缺项') }
} else {
    [void]$issues.Add('体检脚本不见了')
}

# 五、崩溃日志
$cl = Join-Path $root '崩溃日志.txt'
$crash = '无'
if (Test-Path -LiteralPath $cl) {
    $crash = "有 $((Get-Content -LiteralPath $cl).Count) 行"
    [void]$issues.Add('崩溃日志里有新内容')
}

# 六、待装更新
$upd = Join-Path $root 'updates\道.exe'
$updInfo = '无'
if (Test-Path -LiteralPath $upd) { $updInfo = '有待装'; }

# 七、当天图标有没有换
$icoDay = Join-Path $root ('icons\dao_' + $now.ToString('yyyyMMdd') + '.ico')
$icoInfo = '今天还没换'
if (Test-Path -LiteralPath $icoDay) { $icoInfo = '今天已换' }

# 八、两端版本是否一致（读 apk 的 versionName）
$apk = Join-Path $root '道.apk'
$apkVer = '未读'
$bt = 'E:\AndroidTools\sdk\build-tools\34.0.0\aapt2.exe'
if ((Test-Path -LiteralPath $apk) -and (Test-Path -LiteralPath $bt)) {
    try {
        $dump = (& $bt dump badging $apk 2>&1 | Out-String)
        if ($dump -match "versionName='([^']+)'") { $apkVer = $Matches[1] }
    } catch { }
}
if ($apkVer -ne '未读' -and $ver -ne '?') {
    $num = ($apkVer -split '\.')[0]
    if ($num -ne $ver) { [void]$issues.Add("两端版本不一致：exe v$ver / apk v$apkVer") }
}

# 结论
$conclusion = '正常'
if ($issues.Count -gt 0) { $conclusion = '⚠ ' + ($issues -join '；') }

# 九、把这一轮发到邮箱（没配授权码就静默跳过，不算故障）
$mailInfo = '未配'
$mailScript = Join-Path $root 'tools\send_mail.ps1'
if (Test-Path -LiteralPath $mailScript) {
    $html = "<h3>道 · $($now.ToString('yyyy-MM-dd HH:mm')) $round</h3><p><b>结论：</b>$conclusion</p><p>$procInfo，v$ver；体检：$feat；话术 $say 行 / 知识 $know 行 / 记忆 $mem 行；崩溃 $crash；待装 $updInfo；图标 $icoInfo；apk v$apkVer</p><p style='color:#999'>这条是程序自动发的，不用回。</p>"
    $subj = "道 · $($now.ToString('yyyy-MM-dd')) $round · $conclusion"
    $ps51m = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
    & $ps51m -NoProfile -ExecutionPolicy Bypass -File $mailScript -Subject $subj -Body $html -Quiet 2>&1 | Out-Null
    switch ($LASTEXITCODE) {
        0 { $mailInfo = '已发' }
        1 { $mailInfo = '失败'; [void]$issues.Add('邮件发送失败') }
        default { $mailInfo = '未配' }
    }
}

$lineOut = "[$($now.ToString('yyyy-MM-dd HH:mm'))] $round | $procInfo v$ver | 体检：$feat | 话术 $say 知识 $know 记忆 $mem | 崩溃 $crash | 待装 $updInfo | 图标 $icoInfo | apk v$apkVer | 邮件 $mailInfo | 结论：$conclusion"

# 写反馈文件（UTF-8 BOM，CRLF），超过 800 行只留最近 800 行
$enc = New-Object Text.UTF8Encoding($true)
$old = ''
if (Test-Path -LiteralPath $feed) { $old = [IO.File]::ReadAllText($feed, $enc) }
$all = [IO.File]::ReadAllText($feed, $enc) -split "`r`n"
if ($all.Count -gt 800) {
    $keep = $all[($all.Count - 800)..($all.Count - 1)]
    [IO.File]::WriteAllText($feed, ($keep -join "`r`n") + "`r`n" + $lineOut + "`r`n", $enc)
} else {
    [IO.File]::AppendAllText($feed, $lineOut + "`r`n", $enc)
}

if (-not $Quiet) { Write-Output $lineOut }

if ($issues.Count -gt 0) { exit 1 }
exit 0
