# 程序版本：v0.1 | 2026-11-22 | 塞 dex 改走 add_dex.py 并硬校验；素材目录清掉 .bak 备份
$logs = New-Object System.Collections.ArrayList
function W($s) { [void]$logs.Add([string]$s) }

$jdk = 'E:\AndroidTools\jdk_ext\jdk-17.0.20.1+1'
$sdk = 'E:\AndroidTools\sdk'
$bt  = "$sdk\build-tools\34.0.0"
$aj  = "$sdk\platforms\android-33\android.jar"
$a   = 'F:\Daodao\src\_apk'

$env:JAVA_HOME = $jdk
$env:PATH = "$jdk\bin;$bt;$env:PATH"

W ("jdk=" + (Test-Path $jdk) + " bt=" + (Test-Path $bt) + " jar=" + (Test-Path $aj))

# 2026-11-22：Windows 上 obj/gen/dex 常被扫描器短暂占用，硬删会抛 "The directory is not empty"。
# 策略：先尽力删；删不掉就换一个带时间戳的新目录，绝不复用旧目录（复用会把上一轮的 class 打进去）。
$stamp = Get-Date -Format 'yyMMddHHmmss'
function Fresh($p) {
    if (-not (Test-Path -LiteralPath $p)) { return $p }
    for ($i = 0; $i -lt 15; $i++) {
        try { [IO.Directory]::Delete($p, $true); return $p } catch { Start-Sleep -Milliseconds 800 }
    }
    $alt = $p + '_' + $stamp
    W ("WARN 删不掉 " + $p + "，改用 " + $alt)
    return $alt
}
$obj = Fresh "$a\obj"
$dex = Fresh "$a\dex"
$gen = Fresh "$a\gen"
foreach ($f in @("$a\res.zip", "$a\base.apk", "$a\aligned.apk", "$a\Dao.apk")) {
    if (Test-Path -LiteralPath $f) { Remove-Item -LiteralPath $f -Force }
}

W "== 1 aapt2 compile =="
$r = & "$bt\aapt2.exe" compile --dir "$a\res" -o "$a\res.zip" 2>&1 | Out-String
W $r.Trim()
W ("exit=" + $LASTEXITCODE)
W ("res.zip=" + (Test-Path -LiteralPath "$a\res.zip"))

W "== 2 aapt2 link =="
$r = & "$bt\aapt2.exe" link -o "$a\base.apk" -I $aj --manifest "$a\AndroidManifest.xml" -R "$a\res.zip" --java $gen --min-sdk-version 21 --target-sdk-version 33 -A "$a\assets" --auto-add-overlay 2>&1 | Out-String
W $r.Trim()
W ("exit=" + $LASTEXITCODE)
W ("base.apk=" + (Test-Path -LiteralPath "$a\base.apk"))

W "== 3 javac =="
New-Item -ItemType Directory -Path $obj -Force | Out-Null
$srcFiles = @(Get-ChildItem -LiteralPath "$a\src" -Recurse -Filter *.java | ForEach-Object { $_.FullName })
$genFiles = @(Get-ChildItem -LiteralPath $gen -Recurse -Filter *.java -ErrorAction SilentlyContinue | ForEach-Object { $_.FullName })
W ("src=" + $srcFiles.Count + " gen=" + $genFiles.Count)
$allSrc = @($srcFiles) + @($genFiles)
$r = & "$jdk\bin\javac.exe" -encoding UTF-8 -source 8 -target 8 -bootclasspath $aj -d $obj $allSrc 2>&1 | Out-String
W $r.Trim()
W ("exit=" + $LASTEXITCODE)

W "== 4 d8 =="
New-Item -ItemType Directory -Path $dex -Force | Out-Null
$clsFiles = @(Get-ChildItem -LiteralPath $obj -Recurse -Filter *.class | ForEach-Object { $_.FullName })
W ("classes=" + $clsFiles.Count)
$r = & "$bt\d8.bat" --lib $aj --min-api 21 --output $dex $clsFiles 2>&1 | Out-String
W $r.Trim()
W ("exit=" + $LASTEXITCODE)
W ("classes.dex=" + (Test-Path -LiteralPath (Join-Path $dex 'classes.dex')))

W "== 5 add dex =="
# 2026-11-22 换实现：原来用 7z 往 base.apk 里塞 dex，7z 最后一步改名 base.apk.tmp1 -> base.apk
# 会因目标被占用失败，脚本没拦住，照样往下 zipalign/签名，打出没有 classes.dex 的假包（装上就崩）。
# 改成 tools\add_dex.py：纯 Python 重写 zip，写完立刻校验 dex 在不在，不在就 abort。
$r = & 'E:\Python313\python.exe' 'F:\Daodao\tools\add_dex.py' "$a\base.apk" (Join-Path $dex 'classes.dex') 2>&1 | Out-String
W $r.Trim()
W ("add_dex exit=" + $LASTEXITCODE)
if ($LASTEXITCODE -ne 0) {
    W "BUILD_APK_FAIL: dex 没塞进去"
    [IO.File]::WriteAllText("$a\_build.txt", ($logs -join "`r`n"), (New-Object Text.UTF8Encoding($true)))
    'BUILD_APK_FAIL'
    exit 1
}

W "== 6 zipalign =="
$r = & "$bt\zipalign.exe" -f -p 4 "$a\base.apk" "$a\aligned.apk" 2>&1 | Out-String
W $r.Trim()
W ("exit=" + $LASTEXITCODE)
W ("aligned.apk=" + (Test-Path -LiteralPath "$a\aligned.apk"))

W "== 7 keytool =="
$ks = "$a\dao.jks"
if (Test-Path -LiteralPath $ks) {
    W "keystore reuse=True"
} else {
    $r = & "$jdk\bin\keytool.exe" -genkeypair -keystore $ks -alias dao -keyalg RSA -keysize 2048 -validity 10000 -storepass daodao123 -keypass daodao123 -dname "CN=Dao, OU=Dao, O=Dao, L=Meizhou, ST=Guangdong, C=CN" -noprompt 2>&1 | Out-String
    W $r.Trim()
    W ("exit=" + $LASTEXITCODE)
}
W ("keystore=" + (Test-Path -LiteralPath $ks))

W "== 8 apksigner sign =="
$r = & "$bt\apksigner.bat" sign --ks $ks --ks-pass "pass:daodao123" --key-pass "pass:daodao123" --out "$a\Dao.apk" "$a\aligned.apk" 2>&1 | Out-String
W $r.Trim()
W ("exit=" + $LASTEXITCODE)

W "== 9 verify =="
$r = & "$bt\apksigner.bat" verify --verbose "$a\Dao.apk" 2>&1 | Out-String
W $r.Trim()
W ("exit=" + $LASTEXITCODE)

if (Test-Path -LiteralPath "$a\Dao.apk") {
    W ("APK_MB=" + [math]::Round((Get-Item -LiteralPath "$a\Dao.apk").Length / 1MB, 2))
} else {
    W "APK_MISSING"
}

[IO.File]::WriteAllText("$a\_build.txt", ($logs -join "`r`n"), (New-Object Text.UTF8Encoding($true)))
'done'
