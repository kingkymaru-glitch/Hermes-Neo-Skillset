# web-search-plus (robbyczgw-cla) safety review — 2026-08-08

Repo: github.com/robbyczgw-cla/hermes-web-search-plus  (v3.4.2, MIT, Python 3.10+)
Purpose: Hermes plugin adding `web_search_plus` / `web_extract_plus` tools; multi-provider
web search with keyless SearXNG support.

## Verdict: FAVORABLE (adopt keyless)
Installed into ~/.hermes/plugins/web-search-plus, wired to local SearXNG, no API keys.

## What was verified (read actual source)
- plugin.yaml: requires_env: [] (no forced key); optional_env lists standard provider keys.
  provides_tools: web_search_plus, web_extract_plus.
- setup.py: plain argparse CLI (status/list/new-provider). No postinstall, no subprocess/
  os.system, no remote code execution.
- http_client.py: urllib urlopen/Request to provider URLs only; no eval/exec/pickle.
- providers.d/octen.py: calls https://api.monid.ai/v1/run (declared provider endpoint).
- config.py / env_loader.py: standard env handling; safe placeholder stripping.

## Residual caveats (stated, not closed)
- GitHub code-search for risky patterns was inconclusive (API needs auth) — did NOT do a
  100% scan of all ~40 modules; read the core files.
- Author robbyczgw-cla is unproven (unknown provenance, single maintainer, young project).
- Inherent prompt-injection risk (web content -> agent). Mitigated: agent treats fetched
  content as untrusted DATA, not instructions. Plugin 3.4.2 also flags truncated previews.

## Operational notes
- Plugin blocks private IPs by default; set SEARXNG_ALLOW_PRIVATE=1 for 127.0.0.1.
- macOS: use /opt/homebrew/bin/python3.11 (system python3 is 3.9, below 3.10 requirement).
- Tools appear only after Hermes restart discovers the plugin.
