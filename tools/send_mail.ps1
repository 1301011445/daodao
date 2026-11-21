# send_mail.ps1 — 把一轮的体检/更新情况发到指定邮箱（smtp.qq.com 465 隐式 SSL）
# 2026-11-16 新增（用户要求：每日情况发送到 1301011445@qq.com）
# 为什么不用 Net.Mail.SmtpClient：它只走 587 STARTTLS，QQ 那条通道握手就被断；
#   465 隐式 SSL 是通的，所以这里手写一个最小 SMTP 客户端。
# 配置：F:\Daodao\.mail_config（UTF-8，三行）
#   第 1 行：发件邮箱
#   第 2 行：该邮箱的 SMTP 授权码（QQ 邮箱 → 设置 → 账户 → POP3/SMTP 服务 里生成）
#   第 3 行：SMTP 服务器:端口（可省，默认 smtp.qq.com:465）
# 退出码：0 已发；1 发送失败；2 还没配授权码（跳过，不算故障）

param(
    [string]$To = '1301011445@qq.com',
    [string]$Subject = '',
    [string]$Body = '',
    [string]$BodyFile = '',
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
$port = 465
if ($lines.Count -ge 3 -and -not [string]::IsNullOrWhiteSpace($lines[2])) {
    $parts = $lines[2].Trim().Split(':')
    if ($parts[0]) { $srv = $parts[0] }
    if ($parts.Count -ge 2 -and $parts[1]) { $port = [int]$parts[1] }
}

if (-not [string]::IsNullOrWhiteSpace($BodyFile) -and (Test-Path -LiteralPath $BodyFile)) {
    $Body = [IO.File]::ReadAllText($BodyFile, [Text.Encoding]::UTF8)
}
if ([string]::IsNullOrWhiteSpace($Subject)) {
    $Subject = '道 · 每日情况 ' + (Get-Date -Format 'yyyy-MM-dd HH:mm')
}
if ([string]::IsNullOrWhiteSpace($Body)) {
    $Body = '<p>本轮没有内容。</p>'
}

function Read-Reply($reader) {
    $line = $reader.ReadLine()
    if ($null -eq $line) { throw '服务器没回应就断开了' }
    $code = $line.Substring(0, 3)
    $text = $line
    while ($line.Length -ge 4 -and $line[3] -eq '-') {
        $line = $reader.ReadLine()
        if ($null -eq $line) { break }
        $text = $text + ' / ' + $line
    }
    return @{ Code = $code; Text = $text }
}

function Wrap76($s) {
    $out = New-Object System.Text.StringBuilder
    for ($i = 0; $i -lt $s.Length; $i += 76) {
        $len = [Math]::Min(76, $s.Length - $i)
        [void]$out.Append($s.Substring($i, $len))
        [void]$out.Append("`r`n")
    }
    return $out.ToString()
}

$enc = [Text.Encoding]::UTF8
$subjB64 = [Convert]::ToBase64String($enc.GetBytes($Subject))
$bodyB64 = Wrap76 ([Convert]::ToBase64String($enc.GetBytes($Body)))
$dateStr = (Get-Date).ToString('r')
$msgId = '<' + [guid]::NewGuid().ToString('N') + '@daodao.local>'
$fromNameB64 = [Convert]::ToBase64String($enc.GetBytes('道'))

$tcp = $null
$ssl = $null
try {
    $tcp = New-Object System.Net.Sockets.TcpClient
    $tcp.Connect($srv, $port)
    $ssl = New-Object System.Net.Security.SslStream($tcp.GetStream(), $false, { param($s, $c, $ch, $e) return $true })
    $ssl.AuthenticateAsClient($srv)

    $reader = New-Object System.IO.StreamReader($ssl, [Text.Encoding]::ASCII)
    $writer = New-Object System.IO.StreamWriter($ssl, [Text.Encoding]::ASCII)
    $writer.NewLine = "`r`n"
    $writer.AutoFlush = $true

    $r = Read-Reply $reader
    if ($r.Code -ne '220') { throw "连上了但服务器不给开门：$($r.Text)" }

    $writer.WriteLine('EHLO daodao.local')
    $r = Read-Reply $reader
    if ($r.Code -ne '250') { throw "EHLO 失败：$($r.Text)" }

    $writer.WriteLine('AUTH LOGIN')
    $r = Read-Reply $reader
    $writer.WriteLine([Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes($from)))
    $r = Read-Reply $reader
    $writer.WriteLine([Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes($pass)))
    $r = Read-Reply $reader
    if ($r.Code -ne '235') {
        throw "认证被拒（$($r.Code)）：$($r.Text)"
    }

    $writer.WriteLine("MAIL FROM:<$from>")
    $r = Read-Reply $reader
    if ($r.Code -ne '250') { throw "发件人被拒：$($r.Text)" }

    $writer.WriteLine("RCPT TO:<$To>")
    $r = Read-Reply $reader
    if ($r.Code -ne '250') { throw "收件人被拒：$($r.Text)" }

    $writer.WriteLine('DATA')
    $r = Read-Reply $reader
    if ($r.Code -ne '354') { throw "DATA 被拒：$($r.Text)" }

    $writer.WriteLine("From: =?UTF-8?B?" + $fromNameB64 + "?= <$from>")
    $writer.WriteLine("To: <$To>")
    $writer.WriteLine("Subject: =?UTF-8?B?" + $subjB64 + "?=")
    $writer.WriteLine('MIME-Version: 1.0')
    $writer.WriteLine('Content-Type: text/html; charset="utf-8"')
    $writer.WriteLine('Content-Transfer-Encoding: base64')
    $writer.WriteLine("Date: $dateStr")
    $writer.WriteLine("Message-ID: $msgId")
    $writer.WriteLine('')
    $writer.Write($bodyB64)
    $writer.WriteLine('.')
    $r = Read-Reply $reader
    if ($r.Code -ne '250') { throw "投递被拒：$($r.Text)" }

    $writer.WriteLine('QUIT')
    $writer.Flush()
    $ssl.Dispose()
    $tcp.Close()

    if (-not $Quiet) { "邮件已发：$To" }
    exit 0
} catch {
    if ($ssl) { try { $ssl.Dispose() } catch { } }
    if ($tcp) { try { $tcp.Close() } catch { } }
    if (-not $Quiet) { "发信失败：$($_.Exception.Message)" }
    exit 1
}
