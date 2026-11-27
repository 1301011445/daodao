# 第6类 · piper / Coqui TTS 的韵律（2026-11-27）

## 来源
1. piper（rhasspy）仓库 README：prosody / 句末下倾、音素与时长控制
   https://github.com/rhasspy/piper/blob/master/README.md
2. Coqui TTS 文档：phoneme & duration control（音素时长可调，韵律由时长与 F0 共同决定）
   https://docs.coqui.ai/en/latest/
3. Sound On Sound · Speech synthesis 技巧（合成语音的自然度来自句末下倾与节奏变化）
   https://www.soundonsound.com/techniques/speech-synthesis

## 判据表（脚本 tools\语音\韵律判据.py，可独立跑）
| 编号 | 判据 | 阈值 | 本次实测 | 结果 |
|---|---|---|---|---|
| C1 | 陈述句句末下倾 | -3 ~ -1 Hz | -2 Hz | PASS |
| C2 | 情绪语速跨度 | ≥20 个百分点 | 30（+16% ~ -14%） | PASS |
| C3 | 问句末抬升 | ≥+4 Hz | +5 Hz | PASS |
| C4 | 音色数 | ≥2 | 16 | PASS |

真跑输出：
```
C1 陈述句句末下倾 hz=-2 阈值[-3,-1] -> PASS
C2 语速档位 [-14, -11, 3, 5, 9, 16] 跨度=30个百分点 阈值>=20 -> PASS
C3 问句末抬升 +5Hz 阈值>=4 -> PASS
C4 音色数=16 阈值>=2 -> PASS
PROSODY|PASS
```

## 本轮落地
- `pet.cs` 犯困语速 `-9%` → `-11%`（心情 6 档；配合 -5Hz 调门，听着更没精神）。改动位置 `CurRate()`。
- 走路摆幅基线 `swayAmpCur 0.8f → 0.86f`（手摆与落地对齐，属第4类 Flutter 缓动落地的延续）。
- 版本升到 v150（exe 28,848,640 B / apk 40,084,863 B），两端同号。

## 没做的
1. 真音频层面的「首字延迟 ≤150ms、RTF ≤0.1」仍未达标（Q-069：首字 3474ms），本轮只改韵律参数，没换引擎；短句 Piper、叙事 Kokoro 的替换方案仍停在方案层。
2. 无法用真机听感复核：本轮没有实机试听，只做了参数与判据层面验证。
3. 未做 F0 曲线的离线可视化（缺音素时长标注，需要先接 piper 的 phoneme timing 输出）。
