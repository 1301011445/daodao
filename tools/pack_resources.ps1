# 把「道」运行时需要的嵌入资源按资源名收齐到 _bundle 目录
# 背景：v31 之后换用 build_exe.ps1 编译，它只输出代码不嵌资源，
# 结果 exe 里 0 个资源，形象/姿势/走路帧全部读不到，程序界面空白。
# 这个脚本按旧包（道_new.exe）里的 63 个资源名，把磁盘上对应的 png 找齐并按原名复制，
# 供 build_exe.ps1 用 /resource: 逐个嵌入。
param([string]$RefExe = 'F:\Daodao\src\桌面分身\道_new.exe')
$ErrorActionPreference = 'Stop'
$root   = 'F:\Daodao'
$srcDir = Join-Path $root 'src\桌面分身'
$bundle = Join-Path $srcDir '_bundle'

if (-not (Test-Path -LiteralPath $bundle)) { New-Item -ItemType Directory -Path $bundle -Force | Out-Null }

# 资源名来源：优先从旧包里反射读出（那就是程序真正查的名字）
$names = @()
if (Test-Path -LiteralPath $RefExe) {
    try {
        $asm = [System.Reflection.Assembly]::LoadFrom($RefExe)
        $names = @($asm.GetManifestResourceNames())
    } catch { $names = @() }
}
if ($names.Count -eq 0) { Write-Output 'PACK_FAIL no reference list'; exit 1 }

# 资源名 -> 磁盘文件 的映射规则
function Find-Source([string]$name) {
    if ($name -match '^pose_(\d+)_(stand|wave|walk|cheer|sit)\.png$') {
        $sp = $Matches[1]; $kind = $Matches[2]
        $p = Join-Path $srcDir ('_poses_dev' + $sp + '\' + $kind + '.png')
        if (Test-Path -LiteralPath $p) { return $p }
        $p2 = Join-Path $srcDir ('_poses_dev' + $sp + '\' + $kind + '.PNG')
        if (Test-Path -LiteralPath $p2) { return $p2 }
    }
    if ($name -match '^walk8_(\d+)_(\d+)\.png$') {
        $sp = $Matches[1]; $i = $Matches[2]
        # 注意：数组里不要写 ('a' + $x, 'b') 这种，逗号优先级高于加号会拼错目录名
        $dirs = @("_walk8_$sp", "_walk8_${sp}_v20", "_walk8_${sp}_v19")
        foreach ($d in $dirs) {
            $p = Join-Path $srcDir ($d + '\walk' + $i + '.png')
            if (Test-Path -LiteralPath $p) { return $p }
        }
    }
    if ($name -match '^swordfly_(\d+)\.png$') {
        $i = $Matches[1]
        $p = Join-Path $srcDir ('_swordfly\' + $i + '.png')
        if (Test-Path -LiteralPath $p) { return $p }
    }
    if ($name -match '^face_(\d+)\.png$') {
        foreach ($d in @('faces_cut4', 'faces_cut5', 'faces')) {
            $p = Join-Path $srcDir ($d + '\' + $name)
            if (Test-Path -LiteralPath $p) { return $p }
        }
    }
    if ($name -match '^expr_') {
        $p = Join-Path $srcDir ('_expr\' + $name)
        if (Test-Path -LiteralPath $p) { return $p }
    }
    # 兜底：整个 src 目录递归找同名文件
    $any = Get-ChildItem -LiteralPath $srcDir -Recurse -File -Filter $name -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($any) { return $any.FullName }
    # 再兜底：项目根目录
    $any2 = Get-ChildItem -LiteralPath $root -Depth 1 -File -Filter $name -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($any2) { return $any2.FullName }
    return $null
}

# 清掉上次残留，避免旧图混进来
Get-ChildItem -LiteralPath $bundle -File -Filter '*.png' -ErrorAction SilentlyContinue | Remove-Item -Force

$copied = 0
$missing = @()
foreach ($n in $names) {
    $s = Find-Source $n
    if ($s) {
        Copy-Item -LiteralPath $s -Destination (Join-Path $bundle $n) -Force
        $copied++
    } else {
        $missing += $n
    }
}

$total = (Get-ChildItem -LiteralPath $bundle -File -Filter '*.png' | Measure-Object Length -Sum).Sum
if ($missing.Count -eq 0) {
    Write-Output ('PACK_OK count=' + $copied + ' bytes=' + $total)
} else {
    Write-Output ('PACK_FAIL count=' + $copied + ' missing=' + $missing.Count)
    foreach ($m in $missing) { Write-Output ('  missing ' + $m) }
    exit 1
}
