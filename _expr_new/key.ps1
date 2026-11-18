
param([string]$src,[string]$dst,[int]$targetH)
Add-Type -AssemblyName System.Drawing
$img = [System.Drawing.Image]::FromFile($src)
$w = $img.Width; $h = $img.Height
$newH = $targetH
$newW = [int][Math]::Max(1, [Math]::Round($w * ($newH / [double]$h)))
$bmp = New-Object System.Drawing.Bitmap $newW, $newH, ([System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.InterpolationMode = 'HighQualityBicubic'
$g.Clear([System.Drawing.Color]::Transparent)
$g.DrawImage($img, 0, 0, $newW, $newH)
$g.Dispose(); $img.Dispose()

# 洋红键：R>170 且 B>170 且 G<120 视为背景；边缘像素按距离做过半处理
$rect = New-Object System.Drawing.Rectangle 0,0,$newW,$newH
$data = $bmp.LockBits($rect, [System.Drawing.Imaging.ImageLockMode]::ReadWrite, [System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
$bytes = New-Object byte[] ($data.Stride * $newH)
[System.Runtime.InteropServices.Marshal]::Copy($data.Scan0, $bytes, 0, $bytes.Length)
for ($y=0; $y -lt $newH; $y++) {
  $row = $y * $data.Stride
  for ($x=0; $x -lt $newW; $x++) {
    $i = $row + $x*4
    $b = $bytes[$i]; $gg = $bytes[$i+1]; $r = $bytes[$i+2]
    if ($r -gt 150 -and $b -gt 150 -and $gg -lt 130) { $bytes[$i+3] = 0 }
    elseif ($r -gt 120 -and $b -gt 120 -and $gg -lt 90 -and $b -gt $gg + 60 -and $r -gt $gg + 60) { $bytes[$i+3] = [byte]([Math]::Min($bytes[$i+3], 90)) }
  }
}
[System.Runtime.InteropServices.Marshal]::Copy($bytes, 0, $data.Scan0, $bytes.Length)
$bmp.UnlockBits($data)
$bmp.Save($dst, [System.Drawing.Imaging.ImageFormat]::Png)
$bmp.Dispose()
Write-Output "$(Split-Path $dst -Leaf) ${newW}x${newH}"
