---
name: openai-client-model-proxy
description: >-
  Interpose a tiny local, dependency-free proxy in front of an OpenAI-compatible
  desktop client (Cursor, VS Code-based editors, any tool with an "override OpenAI
  base URL" setting) so it runs on a DIFFERENT model than the one it hardcodes in
  its request body — most commonly to route onto a FREE model (e.g. OpenRouter
  tencent/hy3:free). Use when a client only exposes its own hosted models in the
  picker, sends a fixed model name like "gpt-4" that the target provider rejects,
  but still supports pointing at a custom base URL + key. Covers the proxy design,
  the model-rewrite trick, streaming passthrough, launchd auto-start, the honest
  health check, and how to verify a provider actually serves the model for free.
---

# Route any OpenAI-compatible client onto a free/custom model via a local proxy

## The problem
Some desktop AI clients (Cursor is the canonical case) let you set a custom
"Override OpenAI Base URL" + API key, but they do NOT let you type an arbitrary
model name. They lock the picker to their own hosted models and **hardcode the
model field** (e.g. `"model": "gpt-4"`) in every request body. If you point the
base URL at a provider that only serves `tencent/hy3:free`, that provider rejects
`gpt-4` → the client silently errors.

So a bare base-URL override is not enough. You need a local proxy that rewrites
the model field on the way through.

## When to use this
- User wants <client> to talk to a model not in its picker (free tier, a
  self-hosted model, a different provider).
- The client has an "Override OpenAI Base URL" / custom-endpoint setting.
- Goal: keep using the client's UI normally, but every call actually hits the
  target model.

## The recipe (4 parts)
1. **Local proxy** (stdlib-only Python, no pip installs on the user's machine).
   See `templates/proxy.py` — a known-good, tested implementation. It:
   - Listens on `127.0.0.1:PORT` with `ThreadingHTTPServer`.
   - On any POST/chat, parses the JSON body and sets `data["model"] = TARGET_MODEL`
     (leaving everything else intact) — this is the core trick.
   - Injects the real upstream key as `Authorization: Bearer`.
   - Passes `/v1/models` through (returns a fake list advertising only the target
     model, so the client's picker/validation is happy).
   - **Streams SSE back** with chunked transfer encoding (do not buffer — Cursor
     hangs on non-streaming).
   - Retries transient upstream errors a few times with backoff (free tiers drop
     connections).
   - Returns clean JSON errors (never hangs) when the upstream fails.
2. **Cursor settings** (`~/Library/Application Support/Cursor/User/settings.json`):
   ```json
   "cursor.general.overrideOpenAIBaseUrl": "http://127.0.0.1:8787/v1",
   "cursor.general.openAIKey": "sk-local-proxy"
   ```
   Preserve any existing keys. Quit the client fully (Cmd+Q) after editing so it
   re-reads settings.
3. **Auto-start** via launchd so the proxy survives login/reboots/crashes.
   See `templates/com.example.model-proxy.plist` — set `Label`, `ProgramArguments`
   (`/usr/bin/python3 <abs path to proxy.py>`), `WorkingDirectory`, `RunAtLoad`
   true, `KeepAlive` true. Install to `~/Library/LaunchAgents/` and
   `launchctl load` it.
4. **Key storage** outside the proxy code: read from env `OPENROUTER_API_KEY`, or
   `key.txt`, or `config.json` — never hardcode. See pitfall about placeholder keys.

## Verifying a provider actually serves the model FOR FREE
Before building, confirm the model exists and is free. curl the upstream models
endpoint and parse pricing (OpenAI-compatible providers expose `/v1/models` with a
`pricing` map; `0` = free). Example:
```bash
curl -s -m 15 "https://openrouter.ai/api/v1/models" | python3 -c \
  "import sys,json; d=json.load(sys.stdin); [print(m['id'], m.get('pricing',{}).get('prompt','?')) for m in d.get('data',[]) if 'hy3' in m['id'].lower()]"
```
Verified reference values are in `references/openrouter-hy3-free.md` (do NOT trust
them long-term — re-check pricing before each fresh build; free tiers change).

## Testing the proxy WITHOUT a real key
- `GET /health` → `{"status":"ok","target_model":...,"has_key":...}`
- `GET /v1/models` → JSON listing the target model
- `POST /v1/chat/completions` with no valid key → clean error (401/502), NOT a hang
- Live call (needs real key):
  ```bash
  curl -s -m 30 -X POST http://127.0.0.1:8787/v1/chat/completions \
    -H "Content-Type: application/json" \
    -d '{"model":"gpt-4","messages":[{"role":"user","content":"say hi"}]}'
  ```

## Pitfalls (learned the hard way)
- **Bare base-URL override fails.** Cursor/et al. send `gpt-4`; the target provider
  rejects it. You MUST rewrite the model field in a proxy. (This is the #1 mistake.)
- **Placeholder keys must count as "no key".** If `config.json` ships with
  `"REPLACE_WITH_YOUR_KEY"`, the health check will falsely report `has_key: true`.
  Strip placeholder strings at load time: `if "REPLACE_WITH" in API_KEY.upper(): API_KEY = ""`.
- **Streaming must be pass-through, chunked.** If the proxy buffers the SSE
  response, Cursor shows a spinner forever. Detect `text/event-stream` in the
  upstream Content-Type and pipe chunks with chunked encoding.
- **Honest health check drives the no-key UX.** Cursor's AI calls fail silently
  without a key; a truthful `has_key` flag + a clear 401 JSON helps the user debug.
- **Cursor's newer "Models" tab may ignore the legacy base-URL override.** If the
  client's AI calls still fail after wiring settings.json, add the provider as a
  CUSTOM provider in the client's Models settings (Base URL
  `http://127.0.0.1:8787/v1`, any key) — the proxy handles either path.
- **Free tier is best-effort.** OpenRouter `tencent/hy3:free` is rate-limited and
  occasionally shows as unavailable. Retry 3x with backoff, then return a clean
  error so the client doesn't hang. Tell the user this upfront.
- **Nous has no public free inference endpoint** (verified: api.nousresearch.com /
  inference.nousresearch.com `/v1/models` return nothing; portal is a web app only).
  When the user "prefers Nous but free", fall back to OpenRouter — it's the one
  that's actually reachable and free for this model.

## One-step-at-a-time delivery
Build in this order so the user can verify each stage: (1) proxy + auto-start,
test health/models; (2) wire client settings; (3) hand the user the key-insert
step (you can't do it for them); (4) give the live-call sanity curl. Don't claim a
green end-to-end run until THE USER adds their key — you can verify everything up
to the live call but not the live call itself.
