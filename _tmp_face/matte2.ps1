Add-Type -AssemblyName System.Drawing
$code = @'
using System;
using System.Drawing;
using System.Drawing.Imaging;
using System.Drawing.Drawing2D;
using System.Collections.Generic;
using System.Runtime.InteropServices;

public class MatteCut
{
    static bool White(byte[] px, int stride, int x, int y, int tol)
    {
        int i = y * stride + x * 4;
        byte B = px[i], G = px[i + 1], R = px[i + 2];
        return (255 - R) <= tol && (255 - G) <= tol && (255 - B) <= tol;
    }

    public static string Run(string src, string dst, int targetH, int tol)
    {
        using (var bmp = new Bitmap(src))
        {
            int w = bmp.Width, h = bmp.Height;
            var data = bmp.LockBits(new Rectangle(0, 0, w, h), ImageLockMode.ReadWrite, PixelFormat.Format32bppArgb);
            int stride = data.Stride;
            byte[] px = new byte[stride * h];
            Marshal.Copy(data.Scan0, px, 0, px.Length);

            bool[] bg = new bool[w * h];
            var q = new Queue<int>();
            for (int x = 0; x < w; x++)
            {
                if (White(px, stride, x, 0, tol) && !bg[x]) { bg[x] = true; q.Enqueue(x); }
                int i2 = (h - 1) * w + x;
                if (White(px, stride, x, h - 1, tol) && !bg[i2]) { bg[i2] = true; q.Enqueue(i2); }
            }
            for (int y = 0; y < h; y++)
            {
                if (White(px, stride, 0, y, tol) && !bg[y * w]) { bg[y * w] = true; q.Enqueue(y * w); }
                int i2 = y * w + w - 1;
                if (White(px, stride, w - 1, y, tol) && !bg[i2]) { bg[i2] = true; q.Enqueue(i2); }
            }
            int[] dx = { 1, -1, 0, 0 };
            int[] dy = { 0, 0, 1, -1 };
            while (q.Count > 0)
            {
                int cur = q.Dequeue();
                int cy = cur / w, cx = cur % w;
                for (int k = 0; k < 4; k++)
                {
                    int nx = cx + dx[k], ny = cy + dy[k];
                    if (nx < 0 || ny < 0 || nx >= w || ny >= h) continue;
                    int ni = ny * w + nx;
                    if (bg[ni]) continue;
                    if (!White(px, stride, nx, ny, tol)) continue;
                    bg[ni] = true;
                    q.Enqueue(ni);
                }
            }

            int removed = 0;
            for (int y = 0; y < h; y++)
                for (int x = 0; x < w; x++)
                {
                    int ni = y * w + x, i = y * stride + x * 4;
                    if (bg[ni]) { px[i] = 0; px[i + 1] = 0; px[i + 2] = 0; px[i + 3] = 0; removed++; }
                }

            for (int y = 0; y < h; y++)
                for (int x = 0; x < w; x++)
                {
                    int ni = y * w + x;
                    if (bg[ni]) continue;
                    bool edge = false;
                    if (x > 0 && bg[ni - 1]) edge = true;
                    if (x < w - 1 && bg[ni + 1]) edge = true;
                    if (y > 0 && bg[ni - w]) edge = true;
                    if (y < h - 1 && bg[ni + w]) edge = true;
                    if (edge)
                    {
                        int i = y * stride + x * 4;
                        byte B = px[i], G = px[i + 1], R = px[i + 2];
                        int mn = Math.Min(R, Math.Min(G, B));
                        if (mn > 190) { px[i] = 0; px[i + 1] = 0; px[i + 2] = 0; px[i + 3] = 0; }
                    }
                }

            Marshal.Copy(px, 0, data.Scan0, px.Length);
            bmp.UnlockBits(data);

            int nw = (int)Math.Round((double)w * targetH / h);
            if (nw < 1) nw = 1;
            var ob = new Bitmap(nw, targetH, PixelFormat.Format32bppArgb);
            using (var g = Graphics.FromImage(ob))
            {
                g.InterpolationMode = InterpolationMode.HighQualityBicubic;
                g.PixelOffsetMode = PixelOffsetMode.HighQuality;
                g.CompositingQuality = CompositingQuality.HighQuality;
                g.DrawImage(bmp, new Rectangle(0, 0, nw, targetH), new Rectangle(0, 0, w, h), GraphicsUnit.Pixel);
            }
            ob.Save(dst, ImageFormat.Png);
            ob.Dispose();
            return "OK " + w + "x" + h + " -> " + nw + "x" + targetH + " bg=" + removed;
        }
    }
}
'@
Add-Type -TypeDefinition $code -ReferencedAssemblies System.Drawing

[MatteCut]::Run('F:\Daodao\_tmp_face\boy.png', 'F:\Daodao\_tmp_face\out_12.png', 512, 14)
[MatteCut]::Run('F:\Daodao\_tmp_face\girl.png', 'F:\Daodao\_tmp_face\out_13.png', 512, 14)

foreach ($n in @('out_12.png', 'out_13.png'))
{
    $p = "F:\Daodao\_tmp_face\$n"
    if (Test-Path -LiteralPath $p)
    {
        $i = [System.Drawing.Bitmap]::FromFile($p)
        "{0}: {1}x{2} cornerA={3} {4}KB" -f $n, $i.Width, $i.Height, $i.GetPixel(1, 1).A, [math]::Round((Get-Item -LiteralPath $p).Length / 1KB)
        $i.Dispose()
    }
    else { "$n MISSING" }
}
