# 优化巡检：定时给「道」做一次可量化的体检，并吐出队列里下一条该做的事。
#
# 用法：& 'F:\Daodao\tools\优化巡检.ps1'
#
# 做什么：
#   1) 连采 3 个 10 秒窗口的 /diag（先 reset），记 tick 间隔与 paint 耗时；
#   2) 按「稳态口径」判：p95 > 45ms 或 max > 90ms 记一次告警（不是改阈值凑通过，
#      这是长期观察值，真 FAIL 就进优化队列）；
#   3) 写一份报告到 巡检报告\优化_<日期>_<时间>.md；
#   4) 打印 自我状态\优化队列.md 里第一条未完成项，方便下一轮直接做。
#
# 只在「道」正在运行时才有 /diag；没运行时脚本自己退出并说明，不算失败。
$ErrorActionPreference = 'Continue'
$repo = 'F:\Daodao'
$base = 'http://127.0.0.1:8848/diag'
$outDir = Join-Path $repo '巡检报告'

function Diag($url) {
    try { return (Invoke-RestMethod $url -TimeoutSec 10 | Out-String).Trim() } catch { return '' }
}

function Num($s, $k) {
    if ($s -match ($k + '=([\d\.]+)')) { return [double]$matches[1] }
    return $null
}

$first = Diag $base
if (-not $first) { Write-Output 'SKIP 道 未运行（/diag 无响应）'; exit 0 }

$windows = @()
foreach ($i in 1..3) {
    Diag ($base + '?reset=1') | Out-Null
    Start-Sleep -Seconds 10
    $d = Diag $base
    if (-not $d) { continue }
    $p95 = Num $d 'p95'
    $mx = Num $d 'max'
    $p50 = Num $d 'p50'
    $fps = Num $d 'fps'
    $paint = $null
    if ($d -match 'paint\([^)]*p95=([\d\.]+)') { $paint = [double]$matches[1] }
    $windows += [pscustomobject]@{
        raw = $d
        p95 = $p95
        max = $mx
        p50 = $p50
        fps = $fps
        paint95 = $paint
    }
    Start-Sleep -Seconds 2
}

$warn = @($windows | Where-Object { ($_.p95 -ne $null -and $_.p95 -gt 45) -or ($_.max -ne $null -and $_.max -gt 90) })
$verdict = if ($warn.Count -ge 2) { 'FAIL' } elseif ($warn.Count -eq 1) { 'WARN' } else { 'OK' }

$stamp = Get-Date -Format 'yyyyMMdd_HHmm'
if (-not (Test-Path -LiteralPath $outDir)) { New-Item -ItemType Directory -Path $outDir -Force | Out-Null }
$rep = Join-Path $outDir ("优化_" + $stamp + ".md")
$lines = @()
$lines += "# 优化巡检 " + (Get-Date -Format 'yyyy-MM-dd HH:mm')
$lines += ''
$lines += "判定：**$verdict**（稳态口径：p95>45ms 或 max>90ms 记告警，3 个窗口里 2 个告警算 FAIL）"
$lines += ''
$lines += '| 窗口 | p50 | p95 | max | paint p95 | fps |'
$lines += '|---|---|---|---|---|---|'
$n = 0
foreach ($w in $windows) {
    $n++
    $lines += ("| {0} | {1} | {2} | {3} | {4} | {5} |" -f $n, $w.p50, $w.p95, $w.max, $w.paint95, $w.fps)
}
$lines += ''
$lines += '原始：'
foreach ($w in $windows) { $lines += ('- ' + $w.raw) }

$queue = Join-Path $repo '自我状态\优化队列.md'
$next = ''
if (Test-Path -LiteralPath $queue) {
    $q = @(Get-Content -LiteralPath $queue -Encoding UTF8)
    $inQ = $false
    foreach ($l in $q) {
        if ($l -match '^## 当前队列') { $inQ = $true; continue }
        if ($inQ -and $l -match '^## ') { break }
        if ($inQ -and $l -match '^\d+\.\s+\*\*(.+?)\*\*') { $next = $matches[1]; break }
    }
}
$lines += ''
$lines += '下一件：' + $(if ($next) { $next } else { '队列为空' })

Set-Content -LiteralPath $rep -Value ($lines -join "`r`n") -Encoding UTF8
Write-Output ("VERDICT=" + $verdict + " REPORT=" + $rep)
foreach ($w in $windows) { Write-Output ("  " + $w.raw) }
if ($next) { Write-Output ("NEXT=" + $next) }
