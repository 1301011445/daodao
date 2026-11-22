# -*- coding: utf-8 -*-
import importlib.util, io
spec = importlib.util.spec_from_file_location("wtk", r"F:\Daodao\tools\问题库.py")
wtk = importlib.util.module_from_spec(spec); spec.loader.exec_module(wtk)

try:
    print("CLOSE", wtk.close("Q-095", "v0.112 两页与短链已发，云侧校验 5/5 PASS，线上 data-ver=112"))
except Exception as e:
    print("CLOSE_FAIL", repr(e))

try:
    print("REG", wtk.register("F:\\Daodao 仓库 git index.lock 反复出现，commit 连续两轮失败",
                            来源="2026-11-22 晚轮", 严重度="P1",
                            说明="清掉锁立刻又生成，疑似有别的进程（DaoGithubPush 或自建 watcher）在跑 git；先停该任务再提交"))
except Exception as e:
    print("REG_FAIL", repr(e))

with io.open(r"F:\Daodao\发版记录.txt", "a", encoding="utf-8") as f:
    f.write("""
2026-11-22 19:12 | v0.112 上线 | 短链 exe https://aka.doubaocdn.com/s/SjWvuCXbVj / apk https://aka.doubaocdn.com/s/H545YSvF9E | 两页 data-ver=112、正文 112（电脑 9,937,920 / 手机 8,196,174 字节）| 云侧 线上包校验.sh PASS 5/5（页面 112、短链同链、字节对得上、apk 内 HTML_VER=112、落地页 9 个资源全 200）| 本机 两端自用体检 17/17 PASS、自检 登记问题 0 条 | 仍差手机端上报（无真机，账本记 111）
""")

with io.open(r"F:\Daodao\同步日志.txt", "a", encoding="utf-8") as f:
    f.write("2026-11-22 19:12 v0.112 上线：两页 data-ver=112 + 新短链，云侧校验 5/5 PASS；巡检总控 13 项 23.3 秒\n")
print("TEXT_OK")
