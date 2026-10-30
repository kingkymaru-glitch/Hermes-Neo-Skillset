# Layer 1 M.A.R.U. Diagnostics + Exact API-Spec Matching

## When this applies
Any time you add or debug a network/egress driver, a data-fetch service, or a
"wire up the live API" task for the MARU / my-digital-twin dashboard (and the
user's ops/monitoring tools generally). Two durable disciplines emerged from the
maritime VesselAPI work (commits `fcd55b9` production routing, `af82fc8` diag).

## Layer 1 M.A.R.U. diagnostic philosophy (user-stated, strict)
When the user asks for a "diagnostic trace" or debugging instrumentation, respect:
- **Light** — one or two `console.*` lines, not a logging framework.
- **Modular** — changes live inside the single module under test.
- **Side-effect-free** — logging only; never mutate state, never throw.
- **Contained** — no global state, no heavy/new packages, no new debugging
  components, no UI changes outside the service layer.
- **Return structure unchanged** — the function's contract (`{ vessels, error }`)
  must be byte-identical before/after. Diagnostics NEVER alter the output shape.

Canonical lightweight trace (drop into the egress driver, both lines):
```js
// 0 · before the fetch — confirm key presence ONLY (never log the key itself)
console.log('[egress][vesselapi] Auth initialization state:',
  !!import.meta.env.VITE_VESSEL_API_KEY)
// inside catch(error) — raw error trace
console.error('[egress][vesselapi] Connection error:', error.message || error)
```
Never print the secret — `!!` boolean presence is the max you log.

## Exact-spec-matching discipline
When the user pastes an "official endpoint / query / header / field spec":
1. **Wire it verbatim.** Use the exact route, exact query-param NAMES and casing,
   exact header keys, exact field names. Do NOT infer or "modernize" param names.
2. For VesselAPI specifically (from the user's pasted production spec):
   - Method + path: **POST** to `https://api.vesselapi.com/v1/location/vessels/bounding-box`
     (dev uses the relative `/api-vessel/...` proxy path — see pitfalls).
   - **RequestBody (FLAT JSON — the live server rejects both GET and a nested
     `filter` wrapper):** `{ latBottom: 2.0, lonLeft: 100.0, latTop: 7.0, lonRight: 105.0 }`
     at the root. GET query-params → `HTTP 400`; `{ filter: {...} }` →
     `invalid_request_error`. Full arc in `references/vesselapi-request-shape.md`.
   - Header: `Authorization: Bearer ${import.meta.env.VITE_VESSEL_API_KEY}`
     (+ `Content-Type: application/json`). **Env var is `VITE_VESSEL_API_KEY`**
     (double-L) — a typo to `VITE_VESSELAPI_KEY` silently empties the Bearer.
   - Envelope: `res.data` → `res.vessels` → bare array.
   - Fields: `latitude`/`longitude`/`vessel_name` (fallback `name`)/
     `speed` (fallback `sog`)/`course` (fallback `cog`).
3. **Tolerant field mapping is fine for FIELD NAMES** (the user's spec is a config
   spec, not sample JSON — `??` fallbacks future-proof renames). But the
   URL/params/headers are NOT tolerant — match the spec exactly.
4. If the spec arrives in fragments across turns, ASK for the missing parts
   rather than guessing (e.g. "what are the exact bbox param names?"). Don't
   fabricate a plausible-looking query string.

## Commit-message convention for this work
- Routing/spec alignment: `feat(egress): align <provider> driver with official <x> routing`
- Diagnostic trace: `diag(egress): add lightweight <provider> <x> trace + auth-state check`
- Sim removal: `refactor(egress): remove simulation fallback, report <provider> connection failure`
Keep scope tiny (1 file, single concern) so each commit is reviewable.

## Pitfalls
- Don't "improve" a diagnostic into a side-effecting logger or a new panel.
- Don't log the API key — boolean presence only.
- Don't convert tolerant field fallbacks into an excuse to guess URL/param names.
- Don't alter the return contract for observability — surface via the existing
  `error` discriminator, never by changing the shape.
- Don't reintroduce a simulated fallback for "demo resilience" — this user
  revoked that pattern (see `references/telemetry-integrity-no-fake-data.md`).
- **Env-var name trap:** VesselAPI key is `VITE_VESSEL_API_KEY` (double-L).
  A self-typed `VITE_VESSELAPI_KEY` compiles fine but reads `undefined`, silently
  empties the Bearer header, and yields a 401/denial. After any rename, grep the
  driver AND the diagnostic `!!import.meta.env.*` log line for the SAME name.
