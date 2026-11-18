# Dao (道) — a desktop companion that audits itself

Dao is a small figure who lives on your Windows desktop, with the same character running on Android.
It walks, speaks, learns, and — the unusual part — **keeps a ledger on itself** and runs a full
self-audit once a day, then fixes what scores low.

Built for personal use, shipped as-is: Windows 10/11 executable (no installer) and an Android APK.
Current release **v58** — 12.5 MB (Windows) / 4.9 MB (Android).

---

## What it actually does

- **14 characters, one rig.** Every character is drawn as a figure-grade 3D reference first, then cut
  into 96×152 sprites with a hard edge and one outline pass, so a 96-pixel-wide figure still reads on a
  desktop. The whole set shares one skeleton and one voice table — motion and speech are the same
  pipeline, not two unrelated systems.
- **Animation that is really drawn, not translated.** 8-frame walk cycles (contact, down, passing,
  up, then the other foot) per character; 14 face plates, 48 expression frames, 20 poses, 16 walk
  frames. Walking too fast and it steps onto a sword and flies instead.
- **Speech in 14 voices.** Offline Chinese ASR (Vosk) for wake-word and first-pass hearing, an LLM
  (GLM) for understanding and replies, edge-tts for synthesis, played locally — no subtitle-style
  narration.
- **Self-updating.** On launch it checks the network after 5 seconds, then every 4 hours. Over public
  internet, so it updates on any Wi-Fi, in any city. The Windows build downloads, swaps itself and
  restarts (a one-second gap is normal); the Android build fetches the new APK on demand.
- **Two ends, one character.** Desktop and phone find each other and talk over a local bridge
  (`192.168.x.x:8848` style ping), so the phone side can hold a conversation with the desktop side.
- **Keeps notes.** Things you said and things it learned land in its own notebook and in the
  right-click menu.

## The part that makes it different: it grades itself

Most pets are static. Dao carries an explicit self-model, and every claim in it has to be
recomputable from files on disk.

| Component | What it is | Where it lives |
|---|---|---|
| Joy value | 0–100, starts at 50; ±5 per day, capped | `自我状态/愉悦值.json` + `愉悦值制度.md` |
| Ten abilities | action, speech, creation, coordination, learning, feedback, correction, reaction, thinking, reflection — 2–3 sub-scores each, scored from evidence, not impressions | `自我状态/能力激励.json` + `能力激励制度.md` |
| Issue library | every defect gets an ID, a severity (P0–P3), a root cause and a verification step; reopening a fixed issue raises its recurrence count and costs more each time | `自我状态/问题库.json`, tool: `tools/问题库.py` |
| Weekly optimization list | rebuilt every audit from the real gaps, with the next action written next to each gap | `自我状态/每周优化清单.md` |
| Daily audit | one full inspection per day: both-end versions, sprite counts, package sizes, API ping, scheduled tasks, music library, joy/issues, capability ledger | `tools/inspect_dao.py` → `巡检报告/` |

Two rules keep the numbers honest:

- **One event, one point.** Every credit entry carries a fingerprint (type + issue id / first 24
  characters of the reason). A repeat of the same event on the same day is forced to 0 and reported
  as *skipped*; per-type daily caps (praise ≤ 9, likes ≤ 5, learning ≤ 3, audit pass ≤ 1, ability ≤ 5)
  clip anything above them. The audit prints `anti-farming: N duplicates skipped, M clipped, X points
  blocked`.
- **No double-dipping.** One artifact feeds one ability only. Music-theory notes score *learning*,
  never *creation*; creation is scored on finished masters (170–200 s only), near-finished takes,
  lyric sheets and lyric-track pairing.

If joy drops below 45, or an ability below 30, the audit files a P1 itself and the next round has to
deal with it first. Nothing is marked done unless there is a file, a number, or a passing check behind
it.

## Repository layout

| Path | Contents |
|---|---|
| `src/桌面分身/` | Character art + sprite bundles (`face/`, `expr/`, `pose/`, `walk8/`), voice table, name table, notebook corpus |
| `src/桌面分身/_bundle/` | Packed runtime assets: `voice.py`, `hear.py`, `trans.py`, `我说的话.txt`, `知识库.txt` |
| `src/_apk/` | Android build: `dao.html` (the phone-side UI), `AndroidManifest.xml`, `build.ps1` |
| `tools/inspect_dao.py` | The daily audit — every number in the report comes from a real check |
| `tools/愉悦值检查.py` | Joy-value settlement, including the anti-farming guard |
| `tools/能力激励.py` | Ten-ability scoring from evidence |
| `tools/问题库.py` | Issue library: register / close / summary, with fuzzy duplicate detection |
| `tools/build_exe.ps1`, `src/_apk/build.ps1` | Windows and Android builds |
| `自我状态/` | The ledger itself: joy, abilities, issues, policies, weekly list |
| `巡检报告/` | One report per audit, named `巡检_YYYYMMDD_HHMM.txt` |
| `曲库/`, `学习归档/` | Music masters and the learning archive |
| `引导页_src/`, `版本清单_src/` | Download page and version page sources (published separately) |

## Build and run

Windows (Python 3.13):

```
pip install vosk miniaudio sounddevice edge-tts Pillow
python src\桌面分身\_bundle\voice.py
```

Android APK (JDK 17 + Android build-tools 34):

```
powershell -File src\_apk\build.ps1
```

The offline ASR model (`vosk-model-cn`) is large and is **not** in this repo — drop it next to the
runtime before expecting wake-word recognition to work.

## Download

Desktop and Android builds are served from the download page:
<https://4mf81m04wehh3.doubao.link/app/app_17hnj8acgs2>

## What is deliberately not in this repo

Source code and art only. Personal conversations, runtime logs, state databases, payment QR codes,
access tokens and the ASR model stay out of version control (see `.gitignore`).

## Status

Personal project, shared as-is. No license is claimed; if you want to reuse the art or the code,
open an issue first and ask.
