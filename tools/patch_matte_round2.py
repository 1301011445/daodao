# -*- coding: utf-8 -*-
"""2026-11-25 白边第二刀：素材本身就带一圈「半透明 + 近白」的混色像素
（stand_6 有 32.8%、walk8_11 有 43.6% 的半透明像素是近白的），
它们不在泛洪可达范围（四边 alpha 已经是 0，泛洪从第一步就停了），所以之前 keyWhite 根本没碰到。
按「亮度定遮罩」处理：半透明 + 近白（lum≥215）的像素，alpha 按 (255-lum)/40 打折。
白色裙子/袜子是不透明白（alpha=255），不受影响。"""
import io

OV = r"F:\Daodao\src\_apk\src\com\daodao\pet\DaoOverlay.java"
s = io.open(OV, encoding="utf-8").read()

anchor = """                b.setPixels(px, 0, w, 0, 0, w, h);
            } catch (Exception e) { }
        }"""
add = """                // 素材自带的「半透明近白」混色：这类像素四边 alpha 早就是 0，
                // 泛洪从第一步就够不着，所以只挖纯白是清不掉白边的。按亮度定遮罩。
                for (int i = 0; i < px.length; i++) {
                    int c = px[i];
                    int a = c >>> 24;
                    if (a <= 6 || a >= 250) continue;
                    int r = (c >> 16) & 0xFF, g = (c >> 8) & 0xFF, bl = c & 0xFF;
                    int lum = Math.min(r, Math.min(g, bl));
                    if (lum < 215) continue;                       // 只打近白，浅色衣服不动
                    float k = (255 - lum) / 40f;
                    if (k > 1f) k = 1f;
                    px[i] = ((int) (a * k) << 24) | (c & 0x00FFFFFF);
                }
                b.setPixels(px, 0, w, 0, 0, w, h);
            } catch (Exception e) { }
        }"""
assert anchor in s, "anchor miss"
s = s.replace(anchor, add, 1)
io.open(OV, "w", encoding="utf-8").write(s)
print("OK 白边第二刀")
