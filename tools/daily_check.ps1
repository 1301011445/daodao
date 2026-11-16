# Daily auto inspection runner for Dao (ASCII only, run by scheduled task)
$ErrorActionPreference = 'Continue'
$py = 'F:\Daodao\tools\inspect_dao.py'
$log = 'F:\Daodao\tools\_inspect_out.txt'
$dst = 'F:\Daodao\tools\_last_run.txt'

python $py *> $log
$code = $LASTEXITCODE

try {
    Copy-Item -LiteralPath $log -Destination $dst -Force
} catch { }

$stamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
Add-Content -LiteralPath $dst -Value ("[runner] " + $stamp + " exit=" + $code) -Encoding UTF8
exit $code
