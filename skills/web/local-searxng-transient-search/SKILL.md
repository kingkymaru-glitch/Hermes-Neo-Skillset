---
name: local-searxng-transient-search
description: "Firecrawl down? Self-host SearXNG, use, tear down."
version: 1.0.0
author: Hermes Agent
license: MIT
---

## When this applies
- `web_search`/`web_extract` error "Web tools are not configured / Firecrawl
  credits".
- You need to fetch a GitHub repo, search the web, or safety-review a plugin
  with no managed web backend.
- ONE-OFF task: spin up, use, destroy. Never leave the container running.

## Why SearXNG (not Firecrawl)
Firecrawl's image is gated behind `ghcr.io` auth (pull = "manifest unknown").
SearXNG pulls publicly, keyless, returns result links+snippets. Pair with
`curl` to GitHub API to read actual source.

## Steps
1. Minimal compose (SearXNG only — NOT the full firecrawl stack):
   ```yaml
   services:
     searxng:
       image: searxng/searxng:latest
       ports: ["127.0.0.1:8080:8080"]
       volumes: ["./searxng-settings.yml:/etc/searxng/settings.yml:ro"]
       cpus: 1.0
       mem_limit: 512M
   ```
2. `searxng-settings.yml` (strict schema):
   ```yaml
   use_default_settings: true
   search:
     formats: [html, json]
   server:
     bind_address: "0.0.0.0"
     port: 8080
     method: "POST"
     secret_key: "<32+ char random, NOT 'ultrasecretkey'>"
   ```
   `secret_key` must differ from default or SearXNG exits. `method: POST`
   required for JSON search.
3. `docker compose -f searxng-compose.yml up -d`; wait ~20s.
4. Test: `curl -s -m 20 -X POST http://127.0.0.1:8080/search -H
   "Content-Type: application/x-www-form-urlencoded" -d "q=<q>&format=json"`.
5. For repo review: `curl https://api.github.com/repos/<o>/<r>/contents/<p>`,
   decode base64. Do NOT `curl | python3` (scanner blocks pipe-to-interpreter);
   save, decode with `execute_code` (sandbox).
6. TEAR DOWN: `docker compose -f searxng-compose.yml down`. Confirm
   `lsof -ti:8080` free. Optional `docker rmi searxng/searxng` (zero footprint).

## Pitfalls
- Full firecrawl compose (Redis+RabbitMQ+Postgres+FDB+Playwright, 8GB) is
  overkill and fails to build locally. SearXNG-only only.
- Engine rate-limits (startpage captcha, ddg parse errors) are non-fatal.
- `curl | python3`/`jq` blocked by scanner — save then `execute_code`.
- wikidata 403 at startup is non-fatal.

## Verification
- `curl http://127.0.0.1:8080/` → HTTP 200.
- JSON search returns `results` with `title`/`url`.
- After teardown: no searxng container; port 8080 free.

## Notes
web-search-plus plugin wires to local SearXNG via `SEARXNG_INSTANCE_URL` +
`SEARXNG_ALLOW_PRIVATE=1` (blocks private IPs by default). See
`hermes-plugin-install`.
