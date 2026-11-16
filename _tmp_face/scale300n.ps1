Add-Type -AssemblyName System.Drawing
$code = @'
using System;
using System.Drawing;
using System.Drawing.Imaging;
using System.Drawing.Drawing2D;

public class ScaleN
{
    public static string Run(string src, string dst, int targetH)
    {
        using (var orig = new Bitmap(src))
        {
            int w = orig.Width, h = orig.Height;
            var bmp = new Bitmap(w, h, PixelFormat.Format32bppArgb);
            using (var g0 = Graphics.FromImage(bmp))
            {
                g0.CompositingMode = CompositingMode.SourceCopy;
                g0.DrawImage(orig, new Rectangle(0, 0, w, h), new Rectangle(0, 0, w, h), GraphicsUnit.Pixel);
            }
            int nw = (int)Math.Round((double)w * targetH / h);
            var ob = new Bitmap(nw, targetH, PixelFormat.Format32bppArgb);
            using (var g = Graphics.FromImage(ob))
            {
                g.CompositingMode = CompositingMode.SourceCopy;
                g.InterpolationMode = InterpolationMode.HighQualityBicubic;
                g.PixelOffsetMode = PixelOffsetMode.HighQuality;
                g.CompositingQuality = CompositingQuality.HighQuality;
                g.DrawImage(bmp, new Rectangle(0, 0, nw, targetH), new Rectangle(0, 0, w, h), GraphicsUnit.Pixel);
            }
            ob.Save(dst, ImageFormat.Png);
            ob.Dispose();
            bmp.Dispose();
            return "OK " + nw + "x" + targetH;
        }
    }
}
'@
Add-Type -TypeDefinition $code -ReferencedAssemblies System.Drawing

foreach ($n in @('00', '01', '02', '03'))
{
    $r = [ScaleN]::Run("F:\Daodao\_tmp_face\out_$n.png", "F:\Daodao\_tmp_face\for_apk_$n.png", 300)
    "$n -> $r $([math]::Round((Get-Item -LiteralPath "F:\Daodao\_tmp_face\for_apk_$n.png").Length / 1KB))KB"
}
