Add-Type -AssemblyName System.Drawing
$p = 'F:\Daodao\icons\current.ico'
$ico = New-Object System.Drawing.Icon($p)
$bmp = $ico.ToBitmap()
$w = $bmp.Width
$h = $bmp.Height
$out = @()
$pts = @()
$pts += ,@(0, 0)
$pts += ,@(($w - 1), 0)
$pts += ,@(0, ($h - 1))
$pts += ,@(($w - 1), ($h - 1))
foreach ($pt in $pts) {
    $c = $bmp.GetPixel([int]$pt[0], [int]$pt[1])
    $out += ("(" + $pt[0] + "," + $pt[1] + ")=A" + $c.A)
}
$midA = $bmp.GetPixel([int]($w / 2), [int]($h / 2)).A
$edgeA = $bmp.GetPixel([int]($w / 2), 0).A
Write-Output ("size=" + $w + "x" + $h + " corners: " + ($out -join " | ") + " centerA=" + $midA + " topMidA=" + $edgeA)
$bmp.Dispose()
$ico.Dispose()
