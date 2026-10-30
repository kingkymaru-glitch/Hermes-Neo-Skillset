# DNS Sinkhole Fix — in-process getaddrinfo override

## Problem
Local DNS on the user's machine returns a dead/blocked IP for a hostname that should be
reachable (observed: Bybit `stream.bybit.com` / `api.bybit.com` → `175.139.142.25`, a
TM-Malaysia range that TCP-times-out; the real host is CloudFront `13.35.202.x`).

Confirmed signature:
- `socket.gethostbyname(host)` SUCCEEDS (so it's not a plain ENOTFOUND)
- TCP to that resolved IP HANGS/times out
- `8.8.8.8:443` and other sites connect fine
- Cloudflare DoH returns DIFFERENT (reachable) IPs for the same hostname

## Fix (no sudo; scoped to the running process)
Call `apply_dns_override()` BEFORE any websocket/requests/ccxt use. It monkeypatches
`socket.getaddrinfo` so the blocked hostnames resolve to the pinned good IP. TLS still validates
against the real hostname (SNI intact) — do NOT put the IP in the URL.

```python
import socket

BYBIT_HOSTS = {
    "stream.bybit.com": "13.35.202.94",
    "api.bybit.com": "13.35.202.94",
}

def apply_dns_override():
    _orig = socket.getaddrinfo
    def _patched(host, port, *a, **k):
        if host in BYBIT_HOSTS:
            ip = BYBIT_HOSTS[host]
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, port))]
        return _orig(host, port, *a, **k)
    socket.getaddrinfo = _patched
```

This covers `websocket-client`, `urllib`, `requests`, and `ccxt` (all ride on getaddrinfo).

## Caveats
- **CloudFront IPs rotate.** If the connection dies later, the pinned IP may have changed.
  Re-resolve via Cloudflare DoH and update `BYBIT_HOSTS`:
  `https://1.1.1.1/dns-query?name=stream.bybit.com&type=A` (accept: application/dns-json)
  → take first A-record `Answer[].data`.
- Prefer the broadest working edge IP (e.g. `13.35.202.94`) over a single narrow one.
- This is a machine-local DNS block, not a Bybit outage — general internet (Google, Cloudflare)
  works. Don't "fix" by switching exchanges unless the user wants that.

## Observed (2026-08-11, MARU Mac, crypto_bot/live_1m)
- WebSocket `wss://stream.bybit.com/v5/public/spot` would not open until override applied.
- After override: connected=True, 1m candles + publicTrade stream arrived within seconds.
- Indicators need ~200 1m candles (~3.3h) warm-up before the strategy fires.
