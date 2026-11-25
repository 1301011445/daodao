# -*- coding: utf-8 -*-
"""2026-11-25：把骨链参数从代码里外置到 骨架/bones.json，程序启动读一次，读不到就用原常量。
只改动 rigY / rigW / rigL / rigSum 的声明与一个加载函数，不碰绘画逻辑。"""
import io

P = r"F:\Daodao\src\桌面分身\pet.cs"
src = io.open(P, encoding="utf-8").read()
hits = []

def sub(old, new, tag):
    global src
    if old not in src:
        hits.append((tag, 0)); return
    src = src.replace(old, new, 1); hits.append((tag, 1))

sub("    static readonly float[] rigY = { 0.20f, 0.42f, 0.62f, 0.80f, 0.90f, 1.00f };",
    "    // 2026-11-25：骨链参数外置到 骨架/bones.json（启动读一次，读不到就用下面这套默认值）\n"
    "    static float[] rigY = { 0.20f, 0.42f, 0.62f, 0.80f, 0.90f, 1.00f };", "rigY")
sub("    static readonly float[] rigW = { 0.34f, 0.42f, 0.52f, 0.62f, 0.86f, 1.00f };",
    "    static float[] rigW = { 0.34f, 0.42f, 0.52f, 0.62f, 0.86f, 1.00f };", "rigW")
sub("    static readonly float[] rigL = { 0.00f, 0.55f, 1.15f, 1.75f, 2.30f, 2.90f };",
    "    static float[] rigL = { 0.00f, 0.55f, 1.15f, 1.75f, 2.30f, 2.90f };", "rigL")
sub("    static readonly float rigSum = 3.76f;   // = ΣrigW（3.76）；原来是 3.36，会让摆幅超过 1.0 约 12%，顶端会过冲",
    "    static float rigSum = 3.76f;   // = ΣrigW（3.76）；原来是 3.36，会让摆幅超过 1.0 约 12%，顶端会过冲", "rigSum")

loader = '''
    // 2026-11-25：骨链参数外置。找不到文件、字段缺失、解析失败，都静默回落默认常量，
    // 不允许因为一个配置文件把桌宠启动搞挂。
    static bool rigLoaded = false;
    static void LoadRig()
    {
        if (rigLoaded) return;
        rigLoaded = true;
        try
        {
            string[] cands = { Path.Combine(AppDir(), "骨架", "bones.json"),
                               Path.Combine(AppDir(), "bones.json"),
                               Path.Combine(Path.GetDirectoryName(Application.ExecutablePath), "骨架", "bones.json") };
            string path = null;
            foreach (string c in cands) if (File.Exists(c)) { path = c; break; }
            if (path == null) return;
            string s = File.ReadAllText(path, Encoding.UTF8);
            float[] y = ParseRigArr(s, "y"), w = ParseRigArr(s, "w"), l = ParseRigArr(s, "l");
            if (y == null || w == null || l == null) return;
            if (y.Length != 6 || w.Length != 6 || l.Length != 6) return;
            rigY = y; rigW = w; rigL = l;
            float sum = 0f;
            for (int i = 0; i < w.Length; i++) sum += w[i];
            if (sum > 0.01f) rigSum = sum;
        }
        catch { }
    }

    // 取 "key": [a, b, c, ...] 里的一串数字；没有就返回 null
    static float[] ParseRigArr(string json, string key)
    {
        string pat = "\\"" + key + "\\"";
        int k = json.IndexOf(pat, StringComparison.Ordinal);
        if (k < 0) return null;
        int lb = json.IndexOf('[', k);
        int rb = lb < 0 ? -1 : json.IndexOf(']', lb);
        if (lb < 0 || rb <= lb) return null;
        string body = json.Substring(lb + 1, rb - lb - 1);
        string[] parts = body.Split(',');
        if (parts.Length < 6) return null;
        float[] r = new float[parts.Length];
        for (int i = 0; i < parts.Length; i++)
        {
            string t = parts[i].Trim();
            if (t.Length == 0) return null;
            try { r[i] = float.Parse(t, System.Globalization.CultureInfo.InvariantCulture); }
            catch { return null; }
        }
        return r;
    }
'''

sub("    // 某个高度（0 脚底 ~ 1 头顶）被骨链推开多少，返回的是\"幅值倍数\"",
    loader + "\n    // 某个高度（0 脚底 ~ 1 头顶）被骨链推开多少，返回的是\"幅值倍数\"", "loader")

sub("    static float BoneSway(float fy, float ph)\n    {\n        float s2 = 0f;",
    "    static float BoneSway(float fy, float ph)\n    {\n        LoadRig();\n        float s2 = 0f;", "call")

io.open(P, "w", encoding="utf-8").write(src)
for tag, ok in hits:
    print(("OK   " if ok else "MISS ") + tag)
print("all_ok=", all(ok for _, ok in hits))
