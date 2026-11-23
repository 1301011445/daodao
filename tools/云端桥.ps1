# 云端桥：电脑端（常开节点）负责把 GitHub 和云主机笔记对齐
# 做三件事：
#   1) 拉 origin/cloud-notes，把 云端/ 下的笔记导出到 F:\Daodao\云端收件\
#   2) 跑 github_push.ps1，把本地改动提交推到 main
#   3) 记一条日志到 自我状态\云端笔记同步.md
# 由 Windows 计划任务 DaoGithubPush 触发（开机/登录/每 30 分钟），电脑一开就自动跑。
param(
    [string]$Repo = 'F:\Daodao',
    [string]$Branch = 'cloud-notes',
    [string]$OutDir = 'F:\Daodao\云端收件',
    [string]$NoteFile = 'F:\Daodao\自我状态\云端笔记同步.md'
)
$git = 'E:\Git\cmd\git.exe'
$stamp = Get-Date -f 'yyyy-MM-dd HH:mm'
function Log([string]$m) {
    $dir = Split-Path -Parent $NoteFile
    if (-not (Test-Path -LiteralPath $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
    Add-Content -LiteralPath $NoteFile -Value ("- [$stamp] " + $m) -Encoding UTF8
}

# 0) 清锁（沿用 github_push 里的做法，避免 .lock 残骸污染 refs）
$junkDir = Join-Path $Repo '.git_垃圾'
if (-not (Test-Path -LiteralPath $junkDir)) { New-Item -ItemType Directory -Path $junkDir -Force | Out-Null }
Get-ChildItem -LiteralPath (Join-Path $Repo '.git') -Recurse -Force -File -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -match '\.lock(\.|$)' } | ForEach-Object {
        try { Move-Item -LiteralPath $_.FullName -Destination (Join-Path $junkDir ($_.Name + '_' + [guid]::NewGuid().ToString('N').Substring(0, 6))) -Force -ErrorAction Stop } catch {}
    }

# 1) 拉云端分支并导出笔记
$before = (& $git -C $Repo rev-parse --verify --quiet "origin/$Branch" 2>&1 | Out-String).Trim()
& $git -C $Repo fetch -q origin $Branch 2>$null
$after = (& $git -C $Repo rev-parse --verify --quiet "origin/$Branch" 2>&1 | Out-String).Trim()
if ($LASTEXITCODE -ne 0 -or -not $after) {
    Log '拉取 cloud-notes 失败（网络或分支不存在）'
} else {
    if ($before -ne $after) {
        if (-not (Test-Path -LiteralPath $OutDir)) { New-Item -ItemType Directory -Path $OutDir -Force | Out-Null }
        $files = (& $git -C $Repo ls-tree -r --name-only "origin/$Branch" -- 云端 2>&1 | Out-String) -split "`n" | Where-Object { $_.Trim() }
        $n = 0
        foreach ($f in $files) {
            $rel = $f.Trim()
            $target = Join-Path $OutDir (Split-Path -Leaf $rel)
            try {
                $content = & $git -C $Repo show ("origin/${Branch}:" + $rel) 2>$null
                Set-Content -LiteralPath $target -Value ($content -join "`n") -Encoding UTF8
                $n++
            } catch {}
        }
        Log ("云端有新提交 " + $before.Substring(0,7) + " -> " + $after.Substring(0,7) + "，导出 $n 个笔记到 云端收件")
    } else {
        Log ("云端无新提交（" + $after.Substring(0,7) + "）")
    }
}

# 2) 把本地改动推上 main（同进程调用，避免再起一个 powershell）
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $Repo 'tools\github_push.ps1') 2>$null | Out-Null
Log '已执行 github_push（本地 -> main）'
