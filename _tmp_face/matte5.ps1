Add-Type -AssemblyName System.Drawing
$code = @'
using System;
using System.Collections.Generic;
using System.Drawing;
using System.Drawing.Imaging;
using System.Drawing.Drawing2D;

public class Matte5
{
    static bool IsWhite(Color c, int tol)
    {
        return c.R > 255 - tol && c.G > 255 - tol && c.B > 255 - tol;
    }

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

            // sample corners to decide whether background is already transparent
            int cornerAlpha = 0;
            foreach (int[] p in new int[][] { new int[]{0,0}, new int[]{w-1,0}, new int[]{0,h-1}, new int[]{w-1,h-1} })
            {
                Color c = bmp.GetPixel(p[0], p[1]);
                cornerAlpha += c.A;
            }

            int cleared = 0;
            if (cornerAlpha > 100)
            {
                // flood fill from border over near-white pixels
                var st = new Stack<int[]>();
                var seen = new bool[w * h];
                for (int x = 0; x < w; x++) { st.Push(new int[] { x, 0 }); st.Push(new int[] { x, h - 1 }); }
                for (int y = 0; y < h; y++) { st.Push(new int[] { 0, y }); st.Push(new int[] { w - 1, y }); }
                int tol = 26;
                while (st.Count > 0)
                {
                    int[] p = st.Pop();
                    int x = p[0], y = p[1];
                    if (x < 0 || y < 0 || x >= w || y >= h) continue;
                    int id = y * w + x;
                    if (seen[id]) continue;
                    seen[id] = true;
                    Color c = bmp.GetPixel(x, y);
                    if (!IsWhite(c, tol)) continue;
                    bmp.SetPixel(x, y, Color.FromArgb(0, c.R, c.G, c.B));
                    cleared++;
                    st.Push(new int[] { x + 1, y }); st.Push(new int[] { x - 1, y });
                    st.Push(new int[] { x, y + 1 }); st.Push(new int[] { x, y - 1 });
                }
            }

            // crop to visible bounds then scale to target height
            int minX = w, minY = h, maxX = -1, maxY = -1;
            for (int y = 0; y < h; y++)
                for (int x = 0; x < w; x++)
                    if (bmp.GetPixel(x, y).A > 12)
                    {
                        if (x < minX) minX = x; if (x > maxX) maxX = x;
                        if (y < minY) minY = y; if (y > maxY) maxY = y;
                    }
            if (maxX < 0) { minX = 0; minY = 0; maxX = w - 1; maxY = h - 1; }
            int cw = maxX - minX + 1, ch = maxY - minY + 1;
            int nw = (int)Math.Round((double)cw * targetH / ch);
            var ob = new Bitmap(nw, targetH, PixelFormat.Format32bppArgb);
            using (var g = Graphics.FromImage(ob))
            {
                g.CompositingMode = CompositingMode.SourceCopy;
                g.InterpolationMode = InterpolationMode.HighQualityBicubic;
                g.PixelOffsetMode = PixelOffsetMode.HighQuality;
                g.CompositingQuality = CompositingQuality.HighQuality;
                g.DrawImage(bmp, new Rectangle(0, 0, nw, targetH),
                    new Rectangle(minX, minY, cw, ch), GraphicsUnit.Pixel);
            }
            ob.Save(dst, ImageFormat.Png);
            Color check = ob.GetPixel(0, 0);
            string res = "OK " + w + "x" + h + " -> " + nw + "x" + targetH + " bg=" + cleared + " cornerA=" + check.A;
            ob.Dispose();
            bmp.Dispose();
            return res;
        }
    }
}
'@
Add-Type -TypeDefinition $code -ReferencedAssemblies System.Drawing

foreach ($n in @('00', '01', '02', '03'))
{
    $r = [Matte5]::Run("F:\Daodao\_tmp_face\new\g$n.png", "F:\Daodao\_tmp_face\out_$n.png", 512)
    $sz = [math]::Round((Get-Item -LiteralPath "F:\Daodao\_tmp_face\out_$n.png").Length / 1KB)
    "$n $r ${sz}KB"
}
