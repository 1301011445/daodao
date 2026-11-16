Add-Type -AssemblyName System.Drawing
function ScaleTo($src, $dst, $targetH)
{
    $orig = [System.Drawing.Bitmap]::FromFile($src)
    $w = $orig.Width; $h = $orig.Height
    $nw = [int][Math]::Round(([double]$w * $targetH / $h))
    if ($nw -lt 1) { $nw = 1 }
    $ob = New-Object System.Drawing.Bitmap($nw, $targetH, [System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
    $g = [System.Drawing.Graphics]::FromImage($ob)
    $g.CompositingMode = [System.Drawing.Drawing2D.CompositingMode]::SourceCopy
    $g.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
    $g.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::HighQuality
    $g.CompositingQuality = [System.Drawing.Drawing2D.CompositingQuality]::HighQuality
    $g.DrawImage($orig, (New-Object System.Drawing.Rectangle(0, 0, $nw, $targetH)), (New-Object System.Drawing.Rectangle(0, 0, $w, $h)), [System.Drawing.GraphicsUnit]::Pixel)
    $ob.Save($dst, [System.Drawing.Imaging.ImageFormat]::Png)
    $g.Dispose(); $ob.Dispose(); $orig.Dispose()
    "OK $src -> $dst ${nw}x${targetH}"
}

ScaleTo 'F:\Daodao\_tmp_face\out_12.png' 'F:\Daodao\_tmp_face\for_apk_12.png' 300
ScaleTo 'F:\Daodao\_tmp_face\out_13.png' 'F:\Daodao\_tmp_face\for_apk_13.png' 300
