# 任务记录：把完成的事按固定格式追加到自我状态\任务完成记录.md
# 目的：同类任务下次直接照着「复用」那栏做，不再重踩一遍坑。
# 用法示例：
#   & 'F:\Daodao\tools\任务记录.ps1' -Type '音乐' -Task 'v25 旋律重做' `
#       -Result '186.87s，R5/R6 节奏，词曲对齐校验通过' `
#       -Reuse '打工人歌_v25.py 的 verify() 判据；soundfile 直写 mp3' `
#       -Script 'tools\音乐\打工人歌\打工人歌_v25.py' -Minutes 90
param(
    [Parameter(Mandatory = $true)][string]$Task,
    [string]$Type = '通用',
    [string]$Result = '',
    [string]$Reuse = '',
    [string]$Script = '',
    [int]$Minutes = 0,
    [string]$File = 'F:\Daodao\自我状态\任务完成记录.md'
)

$dir = Split-Path -Parent $File
if (-not (Test-Path -LiteralPath $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
if (-not (Test-Path -LiteralPath $File)) {
    $head = "# 任务完成记录`r`n`r`n> 每完成一件事就追加一条。字段固定：任务 / 成果 / 复用 / 脚本 / 耗时。`r`n> 「复用」写给下一次的自己看：判据、命令、踩过的坑，具体到能照抄。`r`n"
    Set-Content -LiteralPath $File -Value $head -Encoding UTF8 -NoNewline
}

$now = Get-Date -Format 'yyyy-MM-dd HH:mm'
$sb = New-Object System.Text.StringBuilder
[void]$sb.AppendLine("")
[void]$sb.AppendLine("## $now · $Type")
[void]$sb.AppendLine("- 任务：$Task")
if ($Result) { [void]$sb.AppendLine("- 成果：$Result") }
if ($Reuse) { [void]$sb.AppendLine("- 复用：$Reuse") }
if ($Script) { [void]$sb.AppendLine("- 脚本：``$Script``") }
if ($Minutes -gt 0) { [void]$sb.AppendLine("- 耗时：$Minutes 分钟") }

Add-Content -LiteralPath $File -Value $sb.ToString() -Encoding UTF8
Write-Output ("RECORDED " + $now + " " + $Type + " " + $Task)
