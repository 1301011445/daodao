# send_mail.ps1 — 把一轮的体检/更新情况发到指定邮箱
# 2026-11-16 新增（用户要求：每日情况发送到 1301011445@qq.com）
# 配置：F:\Daodao\.mail_config（UTF-8，三行）
#   第 1 行：发件邮箱（例如 1301011445@qq.com）
#   第 2 行：该邮箱的 SMTP 授权码（QQ 邮箱在 设置→账户→POP3/SMTP服务 里生成）
#   第 3 行：SMTP 服务器:端口（可省，默认 smtp.qq.com:587）
# 退出码：0 已发；1 发送失败；2 还没配授权码（跳过，不算故障）

param(
    [string]$To = '1301011445@qq.com',
    [string]$Subject = '',
    [string]$Body = '',
    [switch]$Quiet
)

$ErrorActionPreference = 'Stop'
$cfg = 'F:\Daodao\.mail_config'

if (-not (Test-Path -LiteralPath $cfg)) {
    if (-not $Quiet) { '没找到 .mail_config，邮件没发（配置好授权码后自动生效）' }
    exit 2
}

$lines = @(Get-Content -LiteralPath $cfg -Encoding UTF8)
if ($lines.Count -lt 2) {
    if (-not $Quiet) { '.mail_config 行数不够，邮件没发' }
    exit 2
}

$from = $lines[0].Trim()
$pass = $lines[1].Trim()
if ([string]::IsNullOrWhiteSpace($pass)) {
    if (-not $Quiet) { '.mail_config 里授权码是空的，邮件没发' }
    exit 2
}

$srv = 'smtp.qq.com'
$port = 587
if ($lines.Count -ge 3) {
    $parts = $lines[2].Trim().Split(':')
    if ($parts[0]) { $srv = $parts[0] }
    if ($parts.Count -ge 2 -and $parts[1]) { $port = [int]$parts[1] }
}

if ([string]::IsNullOrWhiteSpace($Subject)) {
    $Subject = '道 · 每日情况 ' + (Get-Date -Format 'yyyy-MM-dd HH:mm')
}
if ([string]::IsNullOrWhiteSpace($Body)) {
    $Body = "<p>本轮没有内容。</p>"
}

try {
    $mail = New-Object System.Net.Mail.MailMessage
    $mail.From = New-Object System.Net.Mail.MailAddress($from, '道')
    $mail.To.Add($To)
    $mail.Subject = $Subject
    $mail.SubjectEncoding = [Text.Encoding]::UTF8
    $mail.Body = $Body
    $mail.BodyEncoding = [Text.Encoding]::UTF8
    $mail.IsBodyHtml = $true

    $cli = New-Object System.Net.Mail.SmtpClient($srv, $port)
    $cli.EnableSsl = $true
    $cli.Timeout = 25000
    $cli.Credentials = New-Object System.Net.NetworkCredential($from, $pass)
    $cli.Send($mail)
    $cli.Dispose()
    $mail.Dispose()

    if (-not $Quiet) { "邮件已发：$To" }
    exit 0
} catch {
    if (-not $Quiet) { "发信失败：$($_.Exception.Message)" }
    exit 1
}
