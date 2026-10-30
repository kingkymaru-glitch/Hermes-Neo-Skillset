# Bybit DNS Sinkhole Fix (this Mac)

## Symptom
Bybit network calls hang/time out from `crypto_bot` even though general internet works.
- `socket.create_connection(("stream.bybit.com",443))` → timeout
- `8.8.8.8:443` and `google.com` connect fine
- Local `socket.gethostbyname("stream.bybit.com")` returns `175.139.142.25` (a dead
  TM-Malaysia / Telekom Malaysia range) — a DNS sinkhole / block.

## Root cause
Local DNS intentionally returns a non-routable TM IP for Bybit hostnames. The real
Bybit endpoints are on CloudFront. Confirmed via Cloudflare DoH:
`curl 'https://1.1.1.1/dns-query?name=stream.bybit.com&type=A'`
→ answers like `13.35.202.94`, `13.35.202.112`, `13.35.202.52` (CloudFront).

## Fix (in-app, no sudo)
Pin the hostname→IP mapping by monkey-patching `socket.getaddrinfo` BEFORE any
network use. Lives in `crypto_bot/live_1m/config.py::apply_dns_override()`:

```python
import socket
BYBIT_HOSTS = {"stream.bybit.com": "13.35.202.94", "api.bybit.com": "13.35.202.94"}
_orig = socket.getaddrinfo
def _patched(host, port, *a, **k):
    if host in BYBIT_HOSTS:
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (BYBIT_HOSTS[host], port))]
    return _orig(host, port, *a, **k)
socket.getaddrinfo = _patched
```

Call `C.apply_dns_override()` at the very top of `app.py` / `smoke_test.py` before
importing `market_feed` / `ccxt`.

## Maintenance
The pinned IP (13.35.202.94) can rotate as CloudFront shifts. If connections die later:
1. Re-resolve via Cloudflare DoH (command above) to get current IPs.
2. Update `BYBIT_HOSTS` with a live IP from the answer set.
(Do NOT add the IP to `/etc/hosts` — that needs sudo and this Mac blocks it.)

## Why not /etc/hosts?
`sudo` is unavailable in this environment, so the override is done in-process.
