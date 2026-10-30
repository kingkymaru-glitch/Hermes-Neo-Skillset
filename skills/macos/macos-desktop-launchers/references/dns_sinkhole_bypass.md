# Local DNS Sinkhole Bypass (e.g. Bybit blocked on the Mac)

## Symptom
WebSocket / HTTPS to a host (e.g. `stream.bybit.com`, `api.bybit.com`) times out, but
general internet works (google.com, 1.1.1.1, cloudflare connect fine).

## Diagnose
1. Raw IP egress works? `python3 -c "import socket;socket.create_connection(('8.8.8.8',443),8)"`
   → if OK, raw IP egress is fine.
2. DNS resolves to a weird IP? `python3 -c "import socket;print(socket.gethostbyname('stream.bybit.com'))"`
   → if it returns a non-CloudFront / TM-Malaysia ISP IP (e.g. 175.139.x.x) that TCP-times-out,
   you have a DNS sinkhole, not a network block.
3. Confirm real IP via an alternate resolver (Cloudflare DoH, bypasses local DNS):
   `curl -s 'https://1.1.1.1/dns-query?name=stream.bybit.com&type=A' | python3 -m json.tool`
   → real Bybit sits on CloudFront (13.35.202.x). Test one: `socket.create_connection(('13.35.202.94',443),8)`.

## Fix (no sudo, scoped to the app)
In the app's config/entry, monkeypatch `socket.getaddrinfo` to pin the hostname to the
known-good IP BEFORE any network use (WS/HTTP). Example:

```python
def apply_dns_override():
    import socket
    HOSTS = {"stream.bybit.com": "13.35.202.94", "api.bybit.com": "13.35.202.94"}
    orig = socket.getaddrinfo
    def patched(host, port, *a, **k):
        if host in HOSTS:
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (HOSTS[host], port))]
        return orig(host, port, *a, **k)
    socket.getaddrinfo = patched
```

Call `apply_dns_override()` at the very top of `app.py` / before creating the WS client.

## Caveat
CloudFront IPs rotate. If connection dies later, re-resolve via the DoH step and update HOSTS.
Don't hardcode in /etc/hosts (needs sudo + system-wide change); app-scoped override is cleaner.

## Note
This is NOT a durable rule about Bybit being "blocked" everywhere — it was a local DNS
policy on THIS Mac. The fix is the technique, not a claim about the service.
