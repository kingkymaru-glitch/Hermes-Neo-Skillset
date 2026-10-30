# Weather/data-provider overlay pattern in MARU
Condensed from MARU Layer 2 wiring: OpenWeather + reconnaissance links.
Use when restoring or adding a weather/data provider row to MARU's Layer Manager.

## Endpoint channels to update for each provider
1. `src/layers/layerRegistry.js` — add `requiresKey`/`url`/`alpha`/`cache` layer rows.
2. `src/MapControlPanel.jsx` — add toggle row in the overlay group + update `disabledReason()` if the new key needs a different env var.
3. Code comments/docs near toggle rows — keep them in sync with the active provider list; stale comments mislead the next cleanup.

## Key-gated disabled-with-tooltip pattern (verified green)
- In `layerRegistry.js`, set `requiresKey` to the env prefix used by `API_KEYS` (e.g. `'openweather'`).
- In `MapControlPanel.jsx`, keep `disabledReason()` minimal and aligned with that same prefix; do NOT hardcode absolute URLs into UI status text.
- Readme/env docs should list the new `VITE_<PROVIDER>_API_KEY` line so the user knows how to enable the row.

## Missing-endpoint scaffold
If a user wants to add a source but the exact URL is unknown:
- Add the registry + UI row now, but mark the endpoint URL as a single dotted-line field (one place in `layerRegistry.js`), with a clear TODO comment naming what the user must paste in.
- Do NOT wire a guessed URL; it will look correct in UI but fail silently in the leaf tile fetch.

## Local-only sourcing recovery
When user mandates Obsidian/Git-only provenance for removed endpoints:
1. Exhaust local search: grep across `~/Documents/obsidian_maru_1` and the whole `my-digital-twin` tree.
2. Exhaust Git history: `git log -p -S "<fragment>" -- files...` and `git log --all -- <path>` to inspect deleted files.
3. If nothing is found, offer two choices: scaffold placeholder, or skip restoring that specific provider.
