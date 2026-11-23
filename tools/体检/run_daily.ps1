# Daily LLM self-check for Dao. Called by Windows Task Scheduler "DAO_DailyLLMCheck" at 21:30.
$ErrorActionPreference = 'Stop'
$env:PYTHONPATH = 'F:\Daodao\tools\_py_libs'
$py = 'E:\Python313\python.exe'
$script = 'F:\Daodao\tools\体检\大模型体检.py'
$log = 'F:\Daodao\同步日志.txt'
$stamp = Get-Date -Format 'yyyy-MM-dd HH:mm'

$out = & $py $script 2>&1 | Out-String
$code = $LASTEXITCODE
$summary = ($out -split "`r?`n" | Where-Object { $_ -match 'REPORT|ERR|new=' }) -join ' ; '
Add-Content -LiteralPath $log -Value ("{0} [cron-llm-check] exit={1} {2}" -f $stamp, $code, $summary) -Encoding utf8
# also drop raw output next to the report for debugging
$raw = 'F:\Daodao\巡检报告\_last_run.txt'
Set-Content -LiteralPath $raw -Value $out -Encoding utf8
if ($code -ne 0) { exit $code }
