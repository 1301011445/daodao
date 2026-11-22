# 程序版本：v0.1 | 2026-11-22 | 基线建档（此前无版本头）
# send_mail.ps1 — 把消息发到指定邮箱（支持 QQ / 163 / 126 / Gmail / Outlook / 企业邮箱等多家通道）
# 为什么不用 Net.Mail.SmtpClient：它只走 587 STARTTLS，QQ 那条通道握手就被断；这里手写最小 SMTP 客户端，
#   465（隐式 SSL）和 587（STARTTLS）两种通道都支持。
# 配置：F:\Daodao\.mail_config（UTF-8）。两种写法都认：
#   A. key=value（推荐）
#        user=发件邮箱
#        pass=该邮箱的 SMTP 授权码/应用专用密码
#        smtp=（可省，留空按发件域名自动选服务器）
#        port=（可省，留空按通道默认 465/587）
#        ssl=（可省，1=隐式 SSL，2=STARTTLS；留空按端口猜：465→隐式，587→STARTTLS）
#   B. 旧的三行位置写法：第1行发件邮箱、第2行授权码、第3行 smtp服务器:端口（可省）
# 收件人：-To 支持多个，用逗号/分号隔开，例如 "a@qq.com,b@163.com"
# 退出码：0 已发；1 发送失败；2 还没配授权码（跳过，不算故障）

param(
    [string]$To = '',
    [string]$Subject = '',
    [string]$Body = '',
    [string]$BodyFile = '',
    [switch]$Quiet
)

$ErrorActionPreference = 'Stop'
$cfg = 'F:\Daodao\.mail_config'

# 2026-11-21：不传 -To 时从 F:\Daodao\通知.ini 的 to= 取收件人。
# 以前这里默认空串，check_and_feed 每轮都报「邮件失败 / 收件人地址不对」，
# 实际是收件人根本没接上。改完 -To 仍是最高优先（临时发给别人用 -To）。
if ([string]::IsNullOrWhiteSpace($To)) {
    $ini = 'F:\Daodao\通知.ini'
    if (Test-Path -LiteralPath $ini) {
        foreach ($ln in (Get-Content -LiteralPath $ini -Encoding UTF8)) {
            if ($ln -match '^\s*to\s*=\s*(.+)$') { $To = $Matches[1].Trim(); break }
        }
    }
}

# 发件域名 → SMTP 服务器（ssl 模式：1=隐式 465，2=STARTTLS 587）
$presets = @{
    'qq.com'          = @('smtp.qq.com', 465, 1)
    'foxmail.com'     = @('smtp.qq.com', 465, 1)
    'exmail.qq.com'   = @('smtp.exmail.qq.com', 465, 1)
    '163.com'         = @('smtp.163.com', 465, 1)
    '126.com'         = @('smtp.126.com', 465, 1)
    'yeah.net'        = @('smtp.yeah.net', 465, 1)
    'sina.com'        = @('smtp.sina.com', 465, 1)
    'sina.cn'         = @('smtp.sina.com', 465, 1)
    'sohu.com'        = @('smtp.sohu.com', 465, 1)
    '139.com'         = @('smtp.139.com', 465, 1)
    'aliyun.com'      = @('smtp.aliyun.com', 465, 1)
    'gmail.com'       = @('smtp.gmail.com', 465, 1)
    'googlemail.com'  = @('smtp.gmail.com', 465, 1)
    'outlook.com'     = @('smtp-mail.outlook.com', 587, 2)
    'hotmail.com'     = @('smtp-mail.outlook.com', 587, 2)
    'live.com'        = @('smtp-mail.outlook.com', 587, 2)
    'msn.com'         = @('smtp-mail.outlook.com', 587, 2)
    'yahoo.com'       = @('smtp.mail.yahoo.com', 465, 1)
    'icloud.com'      = @('smtp.mail.me.com', 587, 2)
    'me.com'          = @('smtp.mail.me.com', 587, 2)
    'protonmail.com'  = @('smtp.protonmail.com', 587, 2)
    'zoho.com'        = @('smtp.zoho.com', 465, 1)
    'yandex.com'      = @('smtp.yandex.com', 465, 1)
}

if (-not (Test-Path -LiteralPath $cfg)) {
    if (-not $Quiet) { '没找到 .mail_config，邮件没发（配置好授权码后自动生效）' }
    exit 2
}

$lines = @(Get-Content -LiteralPath $cfg -Encoding UTF8 | ForEach-Object { $_.Trim() } | Where-Object { $_ -ne '' -and -not $_.StartsWith('#') })
$kv = @{}
$pos = @()
foreach ($ln in $lines) {
    $eq = $ln.IndexOf('=')
    if ($eq -gt 0) {
        $k = $ln.Substring(0, $eq).Trim().ToLower()
        $v = $ln.Substring($eq + 1).Trim()
        if ($v.Length -ge 2 -and $v.StartsWith('"') -and $v.EndsWith('"')) { $v = $v.Substring(1, $v.Length - 2) }
        $kv[$k] = $v
    } else { $pos += $ln }
}

$from = $kv['user']; if (-not $from) { $from = $kv['from'] }
$pass = $kv['pass']; if (-not $pass) { $pass = $kv['auth'] }
if (-not $from -and $pos.Count -ge 1) { $from = $pos[0] }
if (-not $pass -and $pos.Count -ge 2) { $pass = $pos[1] }

if ([string]::IsNullOrWhiteSpace($from)) {
    if (-not $Quiet) { '.mail_config 里没有发件邮箱，邮件没发' }
    exit 2
}
if ([string]::IsNullOrWhiteSpace($pass)) {
    if (-not $Quiet) { '.mail_config 里授权码是空的，邮件没发' }
    exit 2
}

$srv = $kv['smtp']; $port = 0; $mode = 0
if ($kv['port']) { try { $port = [int]$kv['port'] } catch { $port = 0 } }
if ($kv['ssl']) { try { $mode = [int]$kv['ssl'] } catch { $mode = 0 } }

# 旧位置写法第 3 行 smtp服务器:端口
if (-not $srv -and $pos.Count -ge 3 -and $pos[2]) {
    $parts = $pos[2].Split(':')
    if ($parts[0]) { $srv = $parts[0] }
    if ($parts.Count -ge 2 -and $parts[1]) { try { $port = [int]$parts[1] } catch { } }
}

$dom = ($from.Split('@')[-1]).ToLower()
if (-not $srv) {
    if ($presets.ContainsKey($dom)) {
        $srv = $presets[$dom][0]
        if (-not $port) { $port = $presets[$dom][1] }
        if (-not $mode) { $mode = $presets[$dom][2] }
    } else {
        $srv = 'smtp.' + $dom   # 自建/企业邮箱多半是 smtp.<域名>
    }
}
if (-not $port) { $port = 465 }
if (-not $mode) { $mode = if ($port -eq 587) { 2 } else { 1 } }

# ---- 收件人：支持多个（逗号/分号/空格/顿号分隔）----
$To = ($To -replace '[；;、\s]+', ',')
$toList = @($To.Split(',') | ForEach-Object { $_.Trim() } | Where-Object { $_ -ne '' })
$goodTo = @($toList | Where-Object { $_ -match '^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$' })
if ($goodTo.Count -eq 0) {
    if (-not $Quiet) { "收件人地址不对：$To" }
    exit 1
}
$To = ($goodTo -join ',')

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

    $authcb = [System.Net.Security.RemoteCertificateValidationCallback] { param($s, $c, $ch, $e) return $true }
    if ($mode -eq 1) {
        # 465 隐式 SSL：先握手再说话
        $ssl = New-Object System.Net.Security.SslStream($tcp.GetStream(), $false, $authcb)
        $ssl.AuthenticateAsClient($srv)
    } else {
        # 587：先明文 EHLO，再 STARTTLS 升到加密
        $ssl = $null
    }

    $stream = if ($ssl) { $ssl } else { $tcp.GetStream() }
    $reader = New-Object System.IO.StreamReader($stream, [Text.Encoding]::ASCII)
    $writer = New-Object System.IO.StreamWriter($stream, [Text.Encoding]::ASCII)
    $writer.NewLine = "`r`n"
    $writer.AutoFlush = $true

    $r = Read-Reply $reader
    if ($r.Code -ne '220') { throw "连上了但服务器不给开门：$($r.Text)" }

    $writer.WriteLine('EHLO daodao.local')
    $r = Read-Reply $reader
    if ($r.Code -ne '250') { throw "EHLO 失败：$($r.Text)" }

    if ($mode -eq 2) {
        $writer.WriteLine('STARTTLS')
        $r = Read-Reply $reader
        if ($r.Code -ne '220') { throw "STARTTLS 被拒：$($r.Text)" }
        $ssl = New-Object System.Net.Security.SslStream($tcp.GetStream(), $false, $authcb)
        $ssl.AuthenticateAsClient($srv)
        $reader = New-Object System.IO.StreamReader($ssl, [Text.Encoding]::ASCII)
        $writer = New-Object System.IO.StreamWriter($ssl, [Text.Encoding]::ASCII)
        $writer.NewLine = "`r`n"
        $writer.AutoFlush = $true
        $writer.WriteLine('EHLO daodao.local')
        $r = Read-Reply $reader
        if ($r.Code -ne '250') { throw "STARTTLS 后 EHLO 失败：$($r.Text)" }
    }

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

    $rcptFail = @()
    foreach ($one in $goodTo) {
        $writer.WriteLine("RCPT TO:<$one>")
        $rr = Read-Reply $reader
        if ($rr.Code -ne '250' -and $rr.Code -ne '251') { $rcptFail += "$one（$($rr.Code)）" }
    }
    if ($goodTo.Count -eq $rcptFail.Count) { throw "收件人全被拒：$($rcptFail -join '、')" }

    $writer.WriteLine('DATA')
    $r = Read-Reply $reader
    if ($r.Code -ne '354') { throw "DATA 被拒：$($r.Text)" }

    $writer.WriteLine("From: =?UTF-8?B?" + $fromNameB64 + "?= <$from>")
    $writer.WriteLine("To: $($goodTo -join ', ')")
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
    if ($ssl) { $ssl.Dispose() }
    $tcp.Close()

    if (-not $Quiet) {
        $msg = "邮件已发（$srv`:$port，$($goodTo.Count) 个收件人）：$To"
        if ($rcptFail.Count -gt 0) { $msg += "；被拒：$($rcptFail -join '、')" }
        $msg
    }
    exit 0
} catch {
    if ($ssl) { try { $ssl.Dispose() } catch { } }
    if ($tcp) { try { $tcp.Close() } catch { } }
    if (-not $Quiet) { "发信失败（$srv`:$port）：$($_.Exception.Message)" }
    exit 1
}
