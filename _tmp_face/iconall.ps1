Add-Type -AssemblyName System.Drawing
$dir = 'F:\Daodao\icons\ico'
foreach ($f in @(Get-ChildItem -LiteralPath $dir -Filter '*.ico' -File | Sort-Object Name)) {
    try {
        $ico = New-Object System.Drawing.Icon($f.FullName)
        $b = $ico.ToBitmap()
        $w = $b.Width; $h = $b.Height
        $a00 = $b.GetPixel(0, 0).A
        $a10 = $b.GetPixel($w - 1, 0).A
        $a01 = $b.GetPixel(0, $h - 1).A
        $a11 = $b.GetPixel($w - 1, $h - 1).A
        $mx = 0
        if ($a00 -gt $mx) { $mx = $a00 }
        if ($a10 -gt $mx) { $mx = $a10 }
        if ($a01 -gt $mx) { $mx = $a01 }
        if ($a11 -gt $mx) { $mx = $a11 }
        Write-Output ($f.Name + " " + $w + "x" + $h + " alpha=" + $a00 + "/" + $a10 + "/" + $a01 + "/" + $a11 + " maxCorner=" + $mx)
        $b.Dispose(); $ico.Dispose()
    } catch {
        Write-Output ($f.Name + " read-failed")
    }
}
