# -*- coding: utf-8 -*-
import io, json, shutil, os, datetime
base = r"F:\Daodao\tools\音乐\音色"
today = "2026-11-24"
lib = json.load(io.open(os.path.join(base, "音色库.json"), encoding="utf-8"))
# 备份旧库
bak = os.path.join(base, "音色库_旧_%s.bak.json" % today)
if not os.path.exists(bak):
    shutil.copy2(os.path.join(base, "音色库.json"), bak)

legacy = lib.get("profiles", {})
new_profiles = {
    "少年声": {"feats": {"f0": 214.0, "range_semi": 16.0, "vib_rate": 5.0, "vib_depth": 0.022,
                        "breath": 0.14, "centroid": 2300.0, "tilt": 0.44, "dyn": 0.60, "mix": 0.42},
             "用法": "清亮偏高，成长/校园/轻快段"},
    "自然声": {"feats": {"f0": 188.0, "range_semi": 13.0, "vib_rate": 5.2, "vib_depth": 0.028,
                        "breath": 0.24, "centroid": 1760.0, "tilt": 0.55, "dyn": 0.52, "mix": 0.40},
             "用法": "不加修饰的日常感，叙事主歌/对白"},
    "低语声": {"feats": {"f0": 158.0, "range_semi": 11.0, "vib_rate": 4.6, "vib_depth": 0.036,
                        "breath": 0.36, "centroid": 1440.0, "tilt": 0.64, "dyn": 0.48, "mix": 0.36},
             "用法": "气声叙事，桥段/尾奏/低沉段"},
}
lib2 = {
    "版本": "v2_2026-11-24",
    "说明": "用户判定旧音色不喜欢，参考歌手融合档全部退役（数据留在 legacy，不再参与融合）；"
            "改为道自己的三声型：少年声 / 自然声 / 低语声，每首歌至少用 2 种。",
    "dao_base": {"f0": 198.0, "range_semi": 14.0, "vib_rate": 5.2, "vib_depth": 0.025,
                 "breath": 0.20, "centroid": 1880.0, "tilt": 0.52, "dyn": 0.55, "mix": 0.40},
    "profiles": new_profiles,
    "legacy": legacy,
}
json.dump(lib2, io.open(os.path.join(base, "音色库.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("音色库已换：profiles =", list(new_profiles), "| legacy 保留", len(legacy), "条")

# 融合配置 v2
ratio = {"少年声": 0.45, "自然声": 0.42, "低语声": 0.13}
feats = {}
for k, w in ratio.items():
    for f, v in new_profiles[k]["feats"].items():
        feats[f] = feats.get(f, 0.0) + v * w
mixj = {
    "日期": today,
    "版本": "v2",
    "说明": "旧版（李健30/单依纯30/王菲15/那英10/童声15）整套退役，改为道自己的三声型",
    "融合比例": ratio,
    "融合目标特征": {k: round(v, 3) for k, v in feats.items()},
    "后处理链": ["chain v2（暖/暗）", "highpass 80Hz", "lowshelf 160Hz +2.0dB", "lowshelf 300Hz +1.0dB",
                 "peaking 900Hz -1.5dB", "peaking 2600Hz -1.0dB", "highshelf 5000Hz -2.0dB",
                 "highshelf 11000Hz -1.2dB", "轻度齿音收敛", "峰值归一"],
}
old = os.path.join(base, "音色应用_融合.json")
bak2 = os.path.join(base, "音色应用_融合_旧_%s.bak.json" % today)
if not os.path.exists(bak2):
    shutil.copy2(old, bak2)
json.dump(mixj, io.open(old, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("融合配置已换：", ratio, "目标 f0 %.1f centroid %.0f" % (feats["f0"], feats["centroid"]))
