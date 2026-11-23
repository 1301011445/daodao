# Daily LLM self-check for Dao (called by Windows Task Scheduler).
$env:PYTHONPATH = 'F:\Daodao\tools\_py_libs'
$py = 'E:\Python313\python.exe'
$script = 'F:\Daodao\tools\体检\大模型体检.py'
$tmp = 'F:\Daodao\巡检报告\_last_run.txt'
$err = 'F:\Daodao\巡检报告\_last_err.txt'
$log = 'F:\Daodao\同步日志.txt'
$stamp = Get-Date -Format 'yyyy-MM-dd HH:mm'
$code = 99
try {
  $pr = Start-Process -FilePath $py -ArgumentList @($script) -NoNewWindow -Wait -PassThru -RedirectStandardOutput $tmp -RedirectStandardError $err
  $code = $pr.ExitCode
} catch {
  Set-Content -LiteralPath $err -Value $_.Exception.Message -Encoding utf8
}
$msg = @()
if (Test-Path $tmp) { $msg += (Get-Content -LiteralPath $tmp -Tail 4 -Encoding UTF8) }
if (Test-Path $err) { $msg += (Get-Content -LiteralPath $err -Tail 3 -Encoding UTF8) }
foreach ($m in $msg) { Add-Content -LiteralPath $log -Value ("{0} [cron-llm-check exit={1}] {2}" -f $stamp, $code, $m) -Encoding utf8 }
exit $code