Add-Type -AssemblyName System.Drawing
$code = @'
using System;
using System.Drawing;
using System.Drawing.Imaging;
using System.Drawing.Drawing2D;

public class Scale300
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

foreach ($n in @('06', '07', '08', '11'))
{
    $s = "F:\Daodao\_tmp_face\out_$n.png"
    $d = "F:\Daodao\_tmp_face\for_apk_$n.png"
    $r = [Scale300]::Run($s, $d, 300)
    "$n -> $r $([math]::Round((Get-Item -LiteralPath $d).Length / 1KB))KB"
}
