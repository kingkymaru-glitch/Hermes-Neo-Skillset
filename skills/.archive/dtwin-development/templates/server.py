#!/usr/bin/env python3
"""DTWIN local server — web-first 3D capture -> Gaussian splat -> web/AR.

Run:  python3 server.py            # http://localhost:8753
Stdlib only. Serves the web app (ROOT), the Gaussian-splat assets
(web/assets/<name>/model.ply), and deployment pins (deployments/<deploy>/).

COOP/COEP headers are REQUIRED: gaussian-splats-3d uses a SharedArrayBuffer
sort worker, which only runs under cross-origin isolation.

Neo owns DTWIN :8753; Trinity owns TriniD :9877 (NOT 8787 — that's Hermes'
own msgsrvr). Coordinate before edits.
"""
import os
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.abspath(__file__))
PORT = int(os.environ.get("PORT", "8753"))


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=ROOT, **k)

    def end_headers(self):
        # Cross-origin isolation: required for SharedArrayBuffer (gaussian-splats-3d)
        self.send_header("Cross-Origin-Opener-Policy", "same-origin")
        self.send_header("Cross-Origin-Embedder-Policy", "require-corp")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        # Dev server: never cache (masked fixes are a top blank-canvas cause)
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        super().end_headers()

    def log_message(self, fmt, *args):
        pass  # quiet


if __name__ == "__main__":
    os.chdir(ROOT)
    httpd = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"DTWIN server on http://localhost:{PORT}  (root={ROOT})")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nshutting down")
        httpd.shutdown()
