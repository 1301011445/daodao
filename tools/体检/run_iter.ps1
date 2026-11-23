# Daily LLM iteration for Dao:
#   1) 大模型迭代.py   —— 参数级白名单，改前备份、复测不回好就回滚
#   2) 八域优化.py     —— 动作/形象/语言/学习/音乐/记忆/检查/创作 八面体检 + 诊断 + 可验证落地
$env:PYTHONPATH = 'F:\Daodao\tools\_py_libs'
$py = 'E:\Python313\python.exe'
$log = 'F:\Daodao\同步日志.txt'
$rep = 'F:\Daodao\巡检报告'
$stamp = Get-Date -Format 'yyyy-MM-dd HH:mm'

function Run-One($script, $tag) {
  $tmp = Join-Path $rep ("_out_" + $tag + ".txt")
  $err = Join-Path $rep ("_err_" + $tag + ".txt")
  $code = 99
  try {
    $pr = Start-Process -FilePath $py -ArgumentList @('-X', 'utf8', $script) -NoNewWindow -Wait -PassThru -RedirectStandardOutput $tmp -RedirectStandardError $err
    $code = $pr.ExitCode
  } catch {
    Set-Content -LiteralPath $err -Value $_.Exception.Message -Encoding utf8
  }
  $msg = @()
  if (Test-Path $tmp) { $msg += (Get-Content -LiteralPath $tmp -Tail 3 -Encoding UTF8) }
  if (Test-Path $err) { $msg += (Get-Content -LiteralPath $err -Tail 2 -Encoding UTF8) }
  foreach ($m in $msg) { Add-Content -LiteralPath $log -Value ("{0} [cron-{1} exit={2}] {3}" -f $stamp, $tag, $code, $m) -Encoding utf8 }
  return $code
}

$c1 = Run-One 'F:\Daodao\tools\体检\大模型迭代.py' 'llm-iter'
$c2 = Run-One 'F:\Daodao\tools\体检\八域优化.py' 'llm-8dom'
if ($c1 -ne 0) { exit $c1 }
exit $c2
