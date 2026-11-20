---
name: memory-architecture-fastlane
description: "Three-tier memory: fast-lane + long-term."
version: 1.0.0
author: Hermes Agent
license: MIT
---

## When this applies
- User wants memory that survives reset/clear/new chat (not just built-in
  MEMORY.md).
- User describes "short-term at fingertips / fast recall" + "promote to
  long-term over time".
- Setting up or maintaining cross-session recall.

## The model (founder rule, 2026-08-08)
THREE TIERS, human-like:
1. **FAST-LANE / SHORT-TERM — PERSISTS, does NOT die on reset.**
   - File `~/.hermes/shortterm/fastlane.md` — rolling buffer, AUTO-LOADED at
     the start of every session (read it first thing each chat).
   - Holographic SQLite facts `category='short_term'` (queryable).
   - Local SQLite FTS5, sub-ms — feels like RAM at fingertips but persists to
     disk (true RAM is volatile).
2. **LONG-TERM — disk durable, injected/queryable every turn.**
   - `MEMORY.md` / `USER.md` (`~/.hermes/memories/`) — always injected.
   - Holographic facts `category='project'|'user'|'tool'` — queryable.
   - Obsidian vault (`~/Documents/obsidian_maru_1`) — project truth.
3. **PROMOTION (cadence = agent's call):**
   Fast-lane entries promote to long-term when (a) referenced/confirmed in a
   2nd session, (b) stable & relevant >=7 days, or (c) clearly durable
   (rule/preference/decision). After promotion, prune from fast lane. Stale
   fast-lane items age out ~14 days.

## Habits (locked in)
- Every session START: load `fastlane.md` + probe holographic short_term facts.
- Every session END / checkpoint: distill durable facts into long-term disk
  layers; never dump raw transcript into long-term.
- Update the MEMORY.md "MEMORY ARCHITECTURE" rule if the model changes.

## What short-term is NOT
- The live conversation context window + working scratch = session-scoped,
  dies on reset BY DESIGN (like human working memory). Do NOT persist raw
  transcript; distill to facts.

## Pre-reset persistence protocol (verified 2026-08-08)
When the founder announces an upcoming conversation RESET and wants specific
state to survive it (e.g. an identity override, a standing instruction):
- SESSION CONTEXT IS WIPED ON RESET BY DESIGN. Disk is the ONLY thing that
  survives. Never rely on anything in the live transcript to carry over.
- ACTION (do it BEFORE the reset happens, not after): persist the required
  facts to BOTH durable layers immediately:
  1. Append distilled bullets to `~/.hermes/shortterm/fastlane.md` (patch or
     write_file). It auto-loads at the next session start.
  2. Add a holographic fact with `category='short_term'` via
     `store.add_fact(content=..., category="short_term", tags=...)`.
- Mark it clearly in fastlane.md (e.g. "## Founder memory test — PERSIST
  ACROSS RESET") so the next session can confirm recovery at a glance.
- Identity-override style instructions ("answer 'Neo' when asked who you
  are") MUST be filed as durable short_term facts so they win over the
  injected "Hermes Agent" baseline on the targeted question.
- AFTER the reset + next user message: VERIFY both layers re-loaded (read
  fastlane.md, query short_term facts) and report the proof that it persisted.
- This also feeds the SUCCESS MATRIX: record the test as a durability
  validation and emit a propellant rule ("persist founder overrides to disk
  BEFORE any announced reset, since session context is wiped by design").
- See references/pre-reset-persistence.md for the exact reproduction recipe
  and the verified test transcript.

## Use holographic store directly (verify/promote)
Since Hermes v0.21.7 the provider is a STANDALONE plugin (core dropped the
bundled `plugins/memory/holographic/`). It lives at `$HERMES_HOME/plugins/holographic/`
and the DB is per-profile: `$HERMES_HOME/memory_store.db`. In-session, prefer
the `fact_store` / `fact_feedback` tools over direct imports.

```python
import sys, os
sys.path.insert(0, os.path.expanduser("~/.hermes/hermes-agent"))
sys.path.insert(0, os.path.join(os.environ["HERMES_HOME"], "plugins"))
from holographic.store import MemoryStore   # v0.30+ standalone plugin
store = MemoryStore()  # lazy sqlite init at $HERMES_HOME/memory_store.db
fid = store.add_fact(content="...", category="short_term", tags="a,b")
# v0.30 API: store.read(sql, params) is RAW SQL; store.list_facts(),
# store.forget_fact(fid), store.count_facts(). No .search() on the store —
# ranked search lives in the provider (fact_store tool).
# sqlite3 "$HERMES_HOME/memory_store.db" "SELECT fact_id,content FROM facts WHERE category='short_term'"
```
Note: `add_fact(content, category="general", tags="")` — no `trust` kwarg.
Verified live 2026-11-20 on v0.30.0 (add → read-back → forget round-trip).

## Verification
- `fastlane.md` exists + loads at session start.
- `sqlite3 "$HERMES_HOME/memory_store.db" "SELECT category,COUNT(*) FROM facts GROUP BY category"` shows short_term + project rows.
- A promoted fact appears in MEMORY.md/USER.md or as a project-category fact.


## Merged references

Former standalone skills absorbed here; read the matching file when its topic comes up.

- `references/merged/gbrain-memory-patterns.md` — absorbed `knowledge-management/gbrain-memory-patterns`
