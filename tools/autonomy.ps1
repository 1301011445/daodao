$ErrorActionPreference='Continue'
$env:PYTHONUTF8='1'; $env:PYTHONIOENCODING='utf-8'
[Console]::OutputEncoding=[Text.Encoding]::UTF8
$log='F:\Daodao\同步日志.txt'
$t=Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
try{
  $out = & 'E:\Python313\python.exe' -X utf8 'F:\Daodao\tools\道自动流水线.py' 2>&1 | Out-String
  Add-Content -LiteralPath $log -Value ("[$t] 自治流水线 OK`r`n" + $out.Trim()) -Encoding utf8
}catch{
  Add-Content -LiteralPath $log -Value ("[$t] 自治流水线 FAIL " + $_.Exception.Message) -Encoding utf8
  exit 1
}