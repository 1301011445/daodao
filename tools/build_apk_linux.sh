#!/bin/bash
# 2026-11-23 | 云端 Linux 版出包：把 src/_apk/build.ps1 的步骤搬到 bash，产物结构与 Windows 版一致。
# 依赖：JDK17(/home/user/tools/jdk-17*)、build-tools 34(/home/user/tools/android-14)、platform-33 jar(/home/user/tools/android-13/android.jar)
# 用法：bash tools/build_apk_linux.sh   （在仓库根目录跑）
set -euo pipefail
export LANG=C.UTF-8 LC_ALL=C.UTF-8

JDK=$(ls -d /home/user/tools/jdk-17* | head -1)
BT=/home/user/tools/android-14
AJ=/home/user/tools/android-13/android.jar
A=src/_apk
LOG=$A/_build_linux.txt

export JAVA_HOME="$JDK"
export PATH="$JDK/bin:$BT:$PATH"

: > "$LOG"
say() { echo "$*" | tee -a "$LOG"; }

say "== 0 环境 =="
say "jdk=$JDK exists=$([ -x "$JDK/bin/javac" ] && echo yes || echo no) bt=$BT jar=$AJ"

say "== 1 aapt2 compile =="
rm -f "$A/res.zip" "$A/base.apk" "$A/aligned.apk" "$A/Dao.apk"
"$BT/aapt2" compile --dir "$A/res" -o "$A/res.zip" 2>&1 | tee -a "$LOG"

say "== 2 aapt2 link =="
GEN=$(mktemp -d)
"$BT/aapt2" link -o "$A/base.apk" -I "$AJ" --manifest "$A/AndroidManifest.xml" \
  -R "$A/res.zip" --java "$GEN" --min-sdk-version 21 --target-sdk-version 33 \
  -A "$A/assets" --auto-add-overlay 2>&1 | tee -a "$LOG"

say "== 3 javac =="
OBJ=$(mktemp -d)
ROOT=$(pwd)
mapfile -t SRCS < <(find "$ROOT/$A/src" -name '*.java'; find "$GEN" -name '*.java')
say "src=${#SRCS[@]}"
"$JDK/bin/javac" -encoding UTF-8 -source 8 -target 8 -bootclasspath "$AJ" -d "$OBJ" "${SRCS[@]}" 2>&1 | tee -a "$LOG"

say "== 4 d8 =="
DEX=$(mktemp -d)
mapfile -t CLS < <(find "$OBJ" -name '*.class')
say "classes=${#CLS[@]}"
"$BT/d8" --lib "$AJ" --min-api 21 --output "$DEX" "${CLS[@]}" 2>&1 | tee -a "$LOG"
say "classes.dex=$([ -f "$DEX/classes.dex" ] && echo yes || echo no)"

say "== 5 add dex =="
python3 tools/add_dex.py "$A/base.apk" "$DEX/classes.dex" 2>&1 | tee -a "$LOG"
if [ ! -f "$A/base.apk" ]; then say "BUILD_APK_FAIL: 没有 base.apk"; exit 1; fi
if ! unzip -l "$A/base.apk" | grep -q 'classes.dex'; then say "BUILD_APK_FAIL: dex 没塞进去"; exit 1; fi

say "== 6 zipalign =="
"$BT/zipalign" -f -p 4 "$A/base.apk" "$A/aligned.apk" 2>&1 | tee -a "$LOG"

say "== 7 签名 =="
KS=$A/dao_cloud.jks   # 云端专用；电脑那份 dao.jks 不在仓库里，覆盖安装必须用电脑那份
ALIAS=dao-cloud
if [ ! -f "$KS" ]; then
  "$JDK/bin/keytool" -genkeypair -keystore "$KS" -alias "$ALIAS" -keyalg RSA -keysize 2048 \
    -validity 10000 -storepass daodao123 -keypass daodao123 \
    -dname "CN=DaoCloud, OU=Dao, O=Dao, L=Meizhou, ST=Guangdong, C=CN" -noprompt 2>&1 | tee -a "$LOG"
fi
"$BT/apksigner" sign --ks "$KS" --ks-pass pass:daodao123 --key-pass pass:daodao123 \
  --out "$A/Dao.apk" "$A/aligned.apk" 2>&1 | tee -a "$LOG"

say "== 8 校验 =="
"$BT/apksigner" verify "$A/Dao.apk" 2>&1 | tee -a "$LOG"
SIZE=$(stat -c%s "$A/Dao.apk")
say "APK_BYTES=$SIZE"
say "BUILD_OK"
cp -f "$A/Dao.apk" ./道_云端构建.apk
say "OUT=道_云端构建.apk"
