# 程序版本：v0.4 | 2026-11-22 | 自愈冷却分支去掉重复的「道没在跑」，只留一句冷却说明
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

# 一·二、自愈：进程为 0 就拉起来一次（10 分钟内不重复，防重启风暴）
# 2026-11-22 新增（待优化第 13 条：道退出后靠人工拉回）
$healLog = Join-Path $root '自愈日志.txt'
$healStamp = Join-Path $root '自我状态\.last_selfheal'
$healInfo = '未触发'
$exePath = Join-Path $root '道.exe'
if ($procs.Count -eq 0 -and (Test-Path -LiteralPath $exePath)) {
    $last = $null
    if (Test-Path -LiteralPath $healStamp) {
        try { $last = [datetime]::Parse((Get-Content -LiteralPath $healStamp -Raw).Trim()) } catch { $last = $null }
    }
    if ($last -and ((Get-Date) - $last).TotalMinutes -lt 10) {
        $healInfo = '冷却中（上次 ' + $last.ToString('HH:mm') + '）'
        [void]$issues.Add('自愈冷却中（10 分钟内已试过），本轮不重启')
    }
    else {
        try { Start-Process -FilePath $exePath -WorkingDirectory $root } catch { }
        Set-Content -LiteralPath $healStamp -Value (Get-Date).ToString('s') -Encoding UTF8
        $ok = $false
        for ($i = 0; $i -lt 16; $i++) {
            Start-Sleep -Milliseconds 500
            if (@(Get-Process -Name '道').Count -gt 0) { $ok = $true; break }
        }
        if ($ok) { $healInfo = '重启成功'; [void]$issues.Add('巡检自愈：道没在跑，已自动重启') }
        else { $healInfo = '重启失败'; [void]$issues.Add('巡检自愈：道没在跑，自动重启失败') }
        $healLine = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') 自愈 $healInfo"
        Add-Content -LiteralPath $healLog -Value $healLine -Encoding UTF8
        Add-Content -LiteralPath (Join-Path $root '同步日志.txt') -Value $healLine -Encoding UTF8
    }
    $procs = @(Get-Process -Name '道')
    $procInfo = "进程 $($procs.Count)"
}

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
    # 2026-11-21 修：apk 的 versionName 是 "0.86" 这种带前导 0. 的写法，
     # 原来用 ($apkVer -split '\.')[0] 取到的是 "0"，跟 exe 的 "86" 一比就误报"版本不一致"。
     # 这里把前导 "0." 去掉，只留主版本号再比。
     $num = ($apkVer -replace '^\s*0\.', '').Trim()
    if ($num -ne $ver) { [void]$issues.Add("两端版本不一致：exe v$ver / apk v$apkVer") }
}

# 八·二、常驻程序版本档案（缺版本头 / 改了没升版 = 故障）
# 2026-11-22 新增：用户要求「各项程序都要定期优化更新，最好有版本记录」
$progVer = '未跑'
$chkProg = Join-Path $root 'tools\程序版本检查.py'
$pyExe = 'E:\Python313\python.exe'
if ((Test-Path -LiteralPath $chkProg) -and (Test-Path -LiteralPath $pyExe)) {
    try {
        $outProg = (& $pyExe $chkProg 2>&1 | Out-String)
        if ($outProg -match 'PROGVER\|([^\r\n]*)') {
            $progVer = $Matches[1].Trim()
            if ($progVer -notmatch 'PASS$') { [void]$issues.Add("程序版本：$progVer") }
        } else { $progVer = '输出异常' }
    } catch { $progVer = '失败' }
}

# 结论
$conclusion = '正常'
if ($issues.Count -gt 0) { $conclusion = '⚠ ' + ($issues -join '；') }

# 九、把这一轮发到邮箱（没配授权码就静默跳过，不算故障）
$mailInfo = '未配'
$mailScript = Join-Path $root 'tools\send_mail.ps1'
if (Test-Path -LiteralPath $mailScript) {
    $html = "<h3>道 · $($now.ToString('yyyy-MM-dd HH:mm')) $round</h3><p><b>结论：</b>$conclusion</p><p>$procInfo，v$ver；体检：$feat；话术 $say 行 / 知识 $know 行 / 记忆 $mem 行；崩溃 $crash；待装 $updInfo；图标 $icoInfo；apk v$apkVer；程序版本 $progVer</p><p style='color:#999'>这条是程序自动发的，不用回。</p>"
    $subj = "道 · $($now.ToString('yyyy-MM-dd')) $round · $conclusion"
    $ps51m = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
    & $ps51m -NoProfile -ExecutionPolicy Bypass -File $mailScript -Subject $subj -Body $html -Quiet 2>&1 | Out-Null
    switch ($LASTEXITCODE) {
        0 { $mailInfo = '已发' }
        1 { $mailInfo = '失败' }
        default { $mailInfo = '未配' }
    }
}

$lineOut = "[$($now.ToString('yyyy-MM-dd HH:mm'))] $round | $procInfo v$ver | 体检：$feat | 话术 $say 知识 $know 记忆 $mem | 崩溃 $crash | 待装 $updInfo | 图标 $icoInfo | apk v$apkVer | 程序版本 $progVer | 自愈 $healInfo | 邮件 $mailInfo | 结论：$conclusion"

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

# 十、桌面托盘提示（后台弹几秒，不阻塞）
$notifyScript = Join-Path $root 'tools\notify.ps1'
if (Test-Path -LiteralPath $notifyScript) {
    $tipDir = Join-Path $root '反馈'
    if (-not (Test-Path -LiteralPath $tipDir)) { New-Item -ItemType Directory -Path $tipDir -Force | Out-Null }
    $tipFile = Join-Path $tipDir ('提示_' + $now.ToString('yyyyMMdd_HHmmss') + '.txt')
    $tipBody = "$($now.ToString('HH:mm')) $round，结论：$conclusion`r`n进程 $($procs.Count) 个，版本 v$ver`r`n体检：$feat`r`n话术 $say / 知识 $know / 记忆 $mem"
    [IO.File]::WriteAllText($tipFile, ("道 · $round" + "`r`n" + $tipBody), (New-Object Text.UTF8Encoding($false)))
    Start-Process -FilePath (Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe') -ArgumentList '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $notifyScript, '-FromFile', $tipFile -WindowStyle Hidden
}

if (-not $Quiet) { Write-Output $lineOut }

if ($issues.Count -gt 0) { exit 1 }
exit 0
