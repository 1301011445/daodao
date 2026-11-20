# -*- coding: utf-8 -*-
# iPhone / iPad 用的局域网服务：把「道_iOS」页面发给手机，并把 /pc/* 转发给电脑上的道.exe(8848)
# 这样 iPhone Safari 打开 http://192.168.2.115:8849 就能看到道、让它说话、指挥它做动作，
# 而且页面和接口同源，不会被浏览器的混合内容规则拦掉。
import os, sys, json, urllib.request, urllib.parse
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

ROOT = r"C:\Users\LDY\Doubao\chats\2026-11-11\new-chat\道_iOS"
UP = "http://127.0.0.1:8848"
PORT = 8849

MIME = {".html": "text/html; charset=utf-8", ".png": "image/png", ".jpg": "image/jpeg",
        ".ico": "image/x-icon", ".css": "text/css", ".js": "application/javascript",
        ".mp3": "audio/mpeg", ".json": "application/json"}


class H(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        sys.stderr.write("[ios] " + fmt % args + "\n")

    def _send(self, code, ctype, data):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        try:
            self.wfile.write(data)
        except Exception:
            pass

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Allow", "GET,POST,OPTIONS")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        path = self.path
        if path.startswith("/pc/"):
            self.proxy("GET", path[3:])
            return
        rel = urllib.parse.unquote(path.split("?")[0]).lstrip("/")
        if rel == "":
            rel = "道_iOS.html"
        full = os.path.normpath(os.path.join(ROOT, rel))
        if not full.startswith(ROOT) or not os.path.isfile(full):
            self._send(404, "text/plain; charset=utf-8", "没有这个文件".encode("utf-8"))
            return
        ext = os.path.splitext(full)[1].lower()
        with open(full, "rb") as f:
            data = f.read()
        self._send(200, MIME.get(ext, "application/octet-stream"), data)

    def do_POST(self):
        if self.path.startswith("/pc/"):
            length = int(self.headers.get("Content-Length") or 0)
            body = self.rfile.read(length) if length else b""
            self.proxy("POST", self.path[3:], body)
            return
        self._send(404, "text/plain; charset=utf-8", b"no")

    def proxy(self, method, sub, body=None):
        url = UP + sub
        try:
            req = urllib.request.Request(url, data=body, method=method)
            if body:
                req.add_header("Content-Type", "application/x-www-form-urlencoded")
            with urllib.request.urlopen(req, timeout=45) as r:
                data = r.read()
                self._send(r.status, r.headers.get("Content-Type") or "application/octet-stream", data)
        except Exception as e:
            self._send(502, "text/plain; charset=utf-8", ("道.exe 没应答：%s" % e).encode("utf-8"))


if __name__ == "__main__":
    os.makedirs(ROOT, exist_ok=True)
    srv = ThreadingHTTPServer(("0.0.0.0", PORT), H)
    print("iOS 服务已启动 http://0.0.0.0:%d  (转发 %s)" % (PORT, UP))
    srv.serve_forever()
