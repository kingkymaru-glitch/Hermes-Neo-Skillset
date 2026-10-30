#!/usr/bin/env python3
"""
Local stdlib-only proxy to route an OpenAI-compatible desktop client (Cursor, etc.)
onto a different model than it hardcodes. Copies of this template are meant to be
modified per deployment: set PORT, TARGET_MODEL, and put the real upstream key in
key.txt / config.json / env (never hardcode). See SKILL.md for the full pattern.
"""
import json, os, sys, time, urllib.request, urllib.error
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

PORT = int(os.environ.get("PROXY_PORT", "8787"))
UPSTREAM_BASE = "https://openrouter.ai/api/v1"
TARGET_MODEL = os.environ.get("TARGET_MODEL", "tencent/hy3:free")
MAX_RETRIES = 3
RETRY_BACKOFF = 0.6
HERE = Path(__file__).resolve().parent
LOG_PATH = HERE / "proxy.log"

def log(msg):
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n"
    try:
        with open(LOG_PATH, "a") as f: f.write(line)
    except Exception: pass
    sys.stdout.write(line); sys.stdout.flush()

def load_api_key():
    k = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if k: return k
    f = HERE / "key.txt"
    if f.exists():
        t = f.read_text().strip()
        if t: return t
    c = HERE / "config.json"
    if c.exists():
        try:
            d = json.loads(c.read_text())
            kk = d.get("openrouter_api_key", "").strip()
            if kk: return kk
        except Exception as e: log(f"config.json parse error: {e}")
    return ""

API_KEY = load_api_key()
if API_KEY and "REPLACE_WITH" in API_KEY.upper():
    API_KEY = ""  # placeholder must count as NO key (honest health check)
if not API_KEY:
    log("WARNING: no upstream API key found.")

def rewrite_model(body):
    try: data = json.loads(body.decode("utf-8"))
    except Exception: return body
    if isinstance(data, dict): data["model"] = TARGET_MODEL
    return json.dumps(data).encode("utf-8")

def upstream_path(p):
    p = p.split("?")[0]
    if p.endswith("/chat/completions"): return f"{UPSTREAM_BASE}/chat/completions"
    if p.endswith("/embeddings"): return f"{UPSTREAM_BASE}/embeddings"
    if p.endswith("/models"): return f"{UPSTREAM_BASE}/models"
    return f"{UPSTREAM_BASE}{p}"

def models_response():
    return json.dumps({"object":"list","data":[{"id":TARGET_MODEL,"object":"model","created":1700000000,"owned_by":"openrouter"}]}).encode()

class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    def log_message(self, fmt, *a): log(f"HTTP {fmt % a}")
    def _body(self):
        n = int(self.headers.get("Content-Length", 0) or 0)
        return self.rfile.read(n) if n > 0 else b""
    def _json(self, code, payload, stream=False):
        b = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        if stream: self.send_header("Transfer-Encoding", "chunked")
        else: self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        if stream:
            self.wfile.write(f"{len(b):X}\r\n".encode()); self.wfile.write(b); self.wfile.write(b"\r\n0\r\n\r\n")
        else: self.wfile.write(b)
    def _err(self, code, msg):
        self._json(code, {"error":{"message":msg,"type":"proxy_error","code":code}})
    def do_GET(self):
        p = self.path.split("?")[0]
        if p.endswith("/models"): return self._json(200, json.loads(models_response().decode()))
        self._json(200, {"status":"ok","target_model":TARGET_MODEL,"has_key":bool(API_KEY)})
    def do_POST(self):
        p = self.path.split("?")[0]
        if p.endswith("/models"): return self._json(200, json.loads(models_response().decode()))
        raw = self._body()
        if not API_KEY: return self._err(401, "Upstream API key not configured.")
        body = rewrite_model(raw)
        url = upstream_path(self.path)
        headers = {"Content-Type":"application/json","Authorization":f"Bearer {API_KEY}",
                   "HTTP-Referer":"http://localhost/proxy","X-Title":"model-proxy"}
        last = None
        for attempt in range(1, MAX_RETRIES+1):
            try:
                req = urllib.request.Request(url, data=body, headers=headers, method="POST")
                resp = urllib.request.urlopen(req, timeout=120)
                ct = resp.headers.get("Content-Type", "application/json")
                self.send_response(resp.status)
                self.send_header("Content-Type", ct)
                if "text/event-stream" in ct:
                    self.send_header("Transfer-Encoding", "chunked"); self.end_headers()
                    try:
                        while True:
                            ch = resp.read(4096)
                            if not ch: break
                            self.wfile.write(f"{len(ch):X}\r\n".encode()); self.wfile.write(ch); self.wfile.write(b"\r\n"); self.wfile.flush()
                        self.wfile.write(b"0\r\n\r\n")
                    except (BrokenPipeError, ConnectionResetError) as e: log(f"client gone: {e}")
                    return
                else:
                    pl = resp.read(); self.send_header("Content-Length", str(len(pl))); self.end_headers(); self.wfile.write(pl); return
            except urllib.error.HTTPError as e:
                last = f"upstream HTTP {e.code}: {e.read().decode('utf-8','replace')[:500]}"; log(f"attempt {attempt}: {last}")
                if 400 <= e.code < 500: return self._err(502, last)
            except Exception as e:
                last = f"{type(e).__name__}: {e}"; log(f"attempt {attempt}: {last}")
            if attempt < MAX_RETRIES: time.sleep(RETRY_BACKOFF * attempt)
        self._err(502, f"all {MAX_RETRIES} attempts failed: {last}")

if __name__ == "__main__":
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    log(f"proxy on http://127.0.0.1:{PORT} -> {TARGET_MODEL} (key={bool(API_KEY)})")
    try: srv.serve_forever()
    except KeyboardInterrupt: srv.shutdown()
