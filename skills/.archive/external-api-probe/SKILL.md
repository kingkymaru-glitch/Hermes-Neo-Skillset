---
name: external-api-probe
description: Verify an app's external API integration by replaying its exact outbound request from the terminal. Use when the user disputes data the app shows ("impossible there are no ships"), reports empty/odd results, or suspects the API is broken/junk. Covers the timestamp-format 400 trap, envelope handling, historical-vs-live category mismatch, and dirty-tree probe mismatches where uncommitted changes mean committed code is not the live code path.
---

# external-api-probe

## When to use
- The user disputes what the app renders from an external API ("its impossible that there are no ships", "the API is junk", "why is X empty").
- You need to separate an APP bug (wrong request construction) from an API/coverage reality (sparse data, historical-only feed).
- Re-verifying a feed after a code change (tiling, time window, param edits, proxy path).

## Core discipline: replay the APP's exact request
Do NOT guess the request shape. Read the app's fetch code and reproduce it byte-for-byte
from the terminal (Python `urllib` / `curl`), because a wrong probe yields a misleading
result that can make you falsely agree the API is broken. Mirror:
1. The same path + query param names — including dotted keys (`filter.latBottom`, `time.from`).
2. The same timestamp format. **THIS IS THE #1 TRAP** (see Pitfalls).
3. The same auth header (Bearer token read from `.env` — never print it to stdout).
4. The same response envelope parsing (read the field the app reads first).

## Steps
1. Locate the app's fetch function; copy its URL construction + headers + response parse verbatim.
2. Write a throwaway script under `/tmp` that mirrors it. Pull the key from `.env` via regex (no echo).
3. Run it; record HTTP status + raw record count + **distinct-id count** (dedupe exactly like the app does).
4. If 400: read the error BODY — it usually names the bad param. Do NOT conclude "API broken."
5. Compare to the user's reference (e.g. MarineTraffic). Confirm the two answer the SAME
   question (live positions vs historical pings) before declaring a mismatch a defect.

## Pitfalls
- **Timestamp format → silent HTTP 400.** Python `datetime.isoformat()` (tz-aware) emits
  `2026-07-18T12:58:33.968689+00:00` (microsecond precision + `+00:00`). Many APIs (incl.
  VesselAPI) only accept the `…Z` form `2026-07-18T12:58:33.123Z` (3-digit ms + `Z` suffix) —
  what JS `new Date().toISOString()` produces. A mismatch returns 400 with
  `cannot parse " 00:00" as "Z07:00"`. ALWAYS emit the `Z` form when replaying a JS app's request:
  `dt.strftime('%Y-%m-%dT%H:%M:%S.') + f"{dt.microsecond//1000:03d}Z"`.
- **"Empty" (200 + 0 records) ≠ API broken.** It can be genuine sparsity (no entity pinged that
  box in the window). Re-probe at other times / tiles before concluding.
- **Historical-ping API vs live tracker = category mismatch.** An API returning pings "within the
  last 4h" answers a DIFFERENT question than a live map (MarineTraffic = positions NOW). Don't tell
  the user the API is "junk" for showing fewer dots; explain the semantics gap. Probe for a
  `/current` or `include=current` endpoint — if 404/400, it's historical-only by design.
- **Probe bug masquerading as app bug.** A buggy probe (wrong timestamp, wrong param name) can return
  400/empty on every tile and lead you to wrongly report "the API/tiles are empty." My first VesselAPI
  re-probe did exactly this; the app was sending valid `…Z` and getting 200s. Re-check your probe
  before reporting a negative result to the user.
- **Dirty working tree → stale code-path trap.** When the repo has uncommitted changes, DON'T probe
  from `HEAD`/committed code alone. Inspect the LIVE working tree first and mirror the ACTUAL
  current fetch/URL/query construction on disk. A dirty tree can contain newer or older logic than
  HEAD; replaying the wrong version yields a misleading probe result.

## Verification
- A correct probe returns the same status the app would (200 with real records on populated tiles).
- Distinct-id count (dedupe by the app's id key) = the number of markers the app renders.
  Raw record count ≠ marker count when one entity emits many pings in the window.

## References
- `references/vesselapi-maritime.md` — concrete VesselAPI facts from the MARU maritime feed
  (endpoint, 4°-span cap, envelope, historical-only nature, known-good Python probe snippet).
