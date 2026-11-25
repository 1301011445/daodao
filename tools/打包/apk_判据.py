# -*- coding: utf-8 -*-
# 程序版本：v0.1 | 2026-11-25 | 第7类副攻判据：打包链（zipalign / apksigner / aapt2）每条都要能独立复跑
"""apk 打包链判据（第7类 Android build-tools 与 apksigner）

判据来源：
  https://developer.android.com/tools/zipalign          （4 字节对齐，未对齐会让 mmap 读不开）
  https://developer.android.com/tools/apksigner         （v2/v3 签名方案，minSdk≥24 只签 v1 会被拒装）
  https://developer.android.com/studio/command-line/aapt2 （badging 取 versionCode/versionName/sdk）

判据：
  A1 apksigner verify 通过，且启用了 v2 或 v3（不是只签 v1）
  A2 证书 CN=Dao（与历史包同一把钥匙，升级才不会被系统当换签名）
  A3 zipalign -c -v 4 全 PASS（4 字节对齐）
  A4 badging 能解析 versionCode/versionName，targetSdk ≥ 33
  A5 包内只有一个 classes.dex（多 dex 没配 multidex 会 NoClassDefFound）
  A6 包内没有 .bak / 没有重复 assets 目录（体积不虚）
"""
import os, re, subprocess, sys, zipfile

APK = sys.argv[1] if len(sys.argv) > 1 else r"F:\Daodao\道.apk"
BT = r"E:\AndroidTools\sdk\build-tools\34.0.0"
JDK = r"E:\AndroidTools\jdk_ext\jdk-17.0.20.1+1"
ENV = dict(os.environ, JAVA_HOME=JDK)


def run(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", env=ENV)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def main():
    if not os.path.exists(APK):
        print("FAIL | 包不存在 | %s" % APK)
        return 1
    fails = 0

    # A1 / A2 签名
    rc, out = run(["cmd", "/c", os.path.join(BT, "apksigner.bat"), "verify", "-v", "--print-certs", APK])
    v2 = "v2 scheme (APK Signature Scheme v2): true" in out or "Verified using v2 scheme" in out
    v3 = "v3 scheme" in out and "true" in out.split("v3 scheme")[1][:40]
    cn = re.search(r"certificate DN: (.*)", out)
    dn = cn.group(1).strip() if cn else "-"
    ok = rc == 0 and (v2 or v3)
    print("%s | A1 apksigner 通过且有 v2/v3 | rc=%d v2=%s v3=%s" % ("PASS" if ok else "FAIL", rc, v2, v3))
    if not ok:
        fails += 1
    ok = "CN=Dao" in dn
    print("%s | A2 证书 CN=Dao | %s" % ("PASS" if ok else "FAIL", dn))
    if not ok:
        fails += 1

    # A3 对齐
    rc, out = run([os.path.join(BT, "zipalign.exe"), "-c", "-v", "4", APK])
    bad = [l for l in out.splitlines() if "BAD" in l or "FAILED" in l]
    ok = rc == 0 and not bad
    print("%s | A3 zipalign 4 字节对齐 | rc=%d 问题行=%d" % ("PASS" if ok else "FAIL", rc, len(bad)))
    if not ok:
        fails += 1

    # A4 badging
    rc, out = run([os.path.join(BT, "aapt2.exe"), "dump", "badging", APK])
    vc = re.search(r"versionCode='([^']+)'", out)
    vn = re.search(r"versionName='([^']+)'", out)
    ts = re.search(r"targetSdkVersion:'([^']+)'", out)
    ok = bool(vc and vn) and bool(ts) and int(ts.group(1)) >= 33
    print("%s | A4 badging 版本与 targetSdk≥33 | vc=%s vn=%s target=%s"
          % ("PASS" if ok else "FAIL", vc.group(1) if vc else "-", vn.group(1) if vn else "-", ts.group(1) if ts else "-"))
    if not ok:
        fails += 1

    # A5 单 dex
    with zipfile.ZipFile(APK) as z:
        names = z.namelist()
    dex = [n for n in names if re.match(r"classes(\d*)\.dex$", n)]
    ok = len(dex) == 1
    print("%s | A5 单 classes.dex | %d 个 %s" % ("PASS" if ok else "FAIL", len(dex), ",".join(dex)))
    if not ok:
        fails += 1

    # A6 垃圾文件
    junk = [n for n in names if n.lower().endswith(".bak") or "/assets/assets/" in n]
    ok = not junk
    print("%s | A6 包内无 .bak/重复 assets | %d 处" % ("PASS" if ok else "FAIL", len(junk)))
    if not ok:
        fails += 1

    print("汇总：6 项判据 | 过 %d | 未过 %d | %s" % (6 - fails, fails, "PASS" if fails == 0 else "FAIL"))
    return 0 if fails == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
