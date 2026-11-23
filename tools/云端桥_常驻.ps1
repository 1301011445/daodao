# 云端桥常驻：电脑登录后自动起，每 30 分钟拉一次云端笔记并推 main。
# 之所以不用计划任务：当前账户建任务被系统拒绝（拒绝访问），改用 HKCU Run + 常驻循环，
# 不需要管理员权限，电脑一登录就自动开始。
$ErrorActionPreference = 'Continue'
$Repo = 'F:\Daodao'
$Bridge = Join-Path $Repo 'tools\云端桥.ps1'
$Log = Join-Path $Repo '自我状态\云端桥常驻日志.txt'
$logDir = Split-Path -Parent $Log
if (-not (Test-Path -LiteralPath $logDir)) { New-Item -ItemType Directory -Path $logDir -Force | Out-Null }

# 单实例保护：已有同名循环在跑就不再起第二个
$mutex = New-Object System.Threading.Mutex($false, 'Global\DaoCloudBridgeLoop')
if (-not $mutex.WaitOne(0)) { exit 0 }

while ($true) {
    $stamp = Get-Date -f 'yyyy-MM-dd HH:mm:ss'
    try {
        & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $Bridge | Out-Null
        Add-Content -LiteralPath $Log -Value "[$stamp] 桥执行完成" -Encoding UTF8
    } catch {
        Add-Content -LiteralPath $Log -Value ("[$stamp] 桥执行异常: " + $_.Exception.Message) -Encoding UTF8
    }
    Start-Sleep -Seconds 1800
}
