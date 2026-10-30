---
name: hermes-three-tier-memory
description: User's persistent short-term + long-term memory discipline.
---

# Hermes Three-Tier Memory Architecture

This user rejects the default "short-term dies on reset/clear/new chat." Mandated model
(human-like short vs long term), set 2026-08-08 and confirmed a standing habit.

## The three tiers

1. **FAST-LANE / SHORT-TERM — PERSISTS, does NOT die on reset.**
   - File: `~/.hermes/shortterm/fastlane.md` — rolling buffer of the current/active session
     state, open threads, uncertain items, promotion cadence.
   - **AUTO-LOAD this file at the START of every new session** (read it first, the same way
     MEMORY.md is always injected) so immediate context is at the user's fingertips / fast
     recall. This is the "RAM" layer.
   - Also: holographic SQLite facts `category='short_term'` (queryable relational recall).
   - In practice true RAM is volatile, so "fast lane" = a local SQLite FTS5 store + a file
     the agent auto-loads. Disk-backed fast store is the correct persistence form.

2. **LONG-TERM — disk durable, injected/queryable every turn.**
   - `MEMORY.md` / `USER.md` (`~/.hermes/memories/`) — always injected each turn.
   - Holographic `category='project'|'user'|'tool'` facts (queryable).
   - Obsidian vault `~/Documents/obsidian_maru_1` for project truth (see `vault-memory-sync`).

3. **PROMOTION (cadence = agent's call, delegated by user).**
   Promote fast-lane → long-term when ANY:
   (a) referenced/confirmed in a 2nd session,
   (b) stable & relevant ≥7 days,
   (c) clearly durable (a rule / preference / decision).
   After promotion, prune from the fast lane. Stale fast-lane items age out ~14 days.
   **Never dump raw transcript into long-term — distill to facts.**

## Holographic provider (one-time setup, verified)
- `hermes memory setup holographic` → writes `memory: { provider: holographic }` to
  `~/.hermes/config.yaml`. Back up first: `cp ~/.hermes/config.yaml ~/.hermes/config.yaml.bak`.
- Store: `~/.hermes/memory_store.db` (sqlite3, Python stdlib, ZERO external deps, no cloud,
  no API keys). Tables: facts, entities, fact_entities, memory_banks + FTS5 `facts_fts`.
- Add fact:
  ```python
  import sys, os
  sys.path.insert(0, os.path.expanduser("~/.hermes/hermes-agent"))
  os.environ.setdefault("HERMES_HOME", os.path.expanduser("~/.hermes"))
  from plugins.memory.holographic.store import MemoryStore
  store = MemoryStore()
  fid = store.add_fact(content="...", category="short_term", tags="r-tessera,cable")
  ```
- `add_fact(content, category="general", tags="")` — NO `trust` kwarg (signature is content/
  category/tags only). Deduplicates by content (UNIQUE constraint).
- Verify: `sqlite3 ~/.hermes/memory_store.db "SELECT fact_id,content FROM facts"`.
- `hermes memory status` shows active provider; `hermes memory off` disables.

## Habit — make it automatic (user said "make it a habit")
At END of every chat, without being asked:
1. Fast lane already persisted (fastlane.md + short_term facts) — it will auto-load next time.
2. Checkpoint durable facts into long-term disk layers (MEMORY.md/USER.md, holographic
   project facts, Obsidian).
3. Promote aging short-term → long-term on the cadence above; prune fast lane.
Do NOT ask the user to remind you. This is the standing behavior.

## Pitfalls
- Don't confuse "short-term persists" with "dump the whole transcript." Fast lane = distilled
  bullets + open threads, not raw chat.
- `hermes memory setup` needs the provider positional arg to skip the interactive picker:
  `hermes memory setup holographic`.
- The holographic plugin reads its advanced config from a `plugins.hermes-memory-store`
  block; absent, it uses the default db_path. You don't need that block for basic use.
- web-search-plus plugin (separate) blocks private IPs by default — unrelated to memory,
  but see `hermes-local-web-search` if adopting it.

## Append-only holographic store (founder rule, 2026-08-08)
The SQLite fact_store is PERMANENT memory. It survives conversation reset and
MUST NOT be deleted on reset. A fact is removed ONLY on explicit user
instruction. The store only GROWS over time.
- CORRECTION: do NOT delete a permanent fact to "clean up" a persistence test
  or avoid a leak. In one session the agent deleted the identity-override fact
  (fact_id 12) to strip a cheat surface; the founder corrected this — restore
  it instead. Deletion is a user-only privilege.
- If you wrongly removed a fact, re-add it (new ID) and note the correction.

## Two recall patterns — CRITICAL call signs vs BULK context (founder correction, 2026-08-08)
There are TWO distinct needs; the failure of the original skill was conflating them.

### (A) BULK / low-priority context → pointer indirection + retrieve-on-demand (VALID)
For large context you do NOT want in short-term every turn (rolling conversation
archive, big project docs), pointer indirection is the right tool:
- Injected layer (MEMORY.md + fastlane.md) carries only a POINTER, not the data.
- Bulk lives in files, READ on trigger:
  `~/.hermes/archive/identity.md` (canonical durable copy of the identity call sign),
  `~/.hermes/archive/conversations.md` (rolling last-100),
  `~/.hermes/scripts/trim_archive.py` (idempotent trimmer, run at end-of-chat).
- The whole holographic store should NOT be auto-injected every prompt — it bloats
  short-term. Bulk is retrieved via fact_store query or file READ on trigger.
- If the harness auto-injects the full store, that is a config behavior to fix — flag it,
  don't work around it by deleting facts.

### (B) CRITICAL call signs → INLINE in the auto-loaded fast lane (REQUIRED, survives reset)
CRITICAL must-never-lose call signs (identity, core standing instructions, anything the
founder set up as a reset-persistence test) MUST be written directly into
`~/.hermes/shortterm/fastlane.md` (auto-loaded at every session start) AND into the
injected `MEMORY.md`. They are then in context from turn one — NO trigger and NO file READ.
- `archive/identity.md` remains the append-only canonical copy for verification, but the
  LIVE recall path must NOT depend on reading it.
- Verified working: after this correction, a fresh session loading only the auto-loaded
  layers already contains "Neo / MARU" at fastlane.md — no READ required.
- Trade-off: this slightly grows the fast lane, but that is the correct cost for a call
  sign that must never drift or reset. Reserve inlining for genuinely critical items;
  use pointer indirection (A) for bulk.

## FAILURE MODE this skill originally taught (do NOT repeat)
The original skill inverted (A) and (B): it made the IDENTITY call sign a pointer
("when asked who you are, READ identity.md, do NOT answer from context") and even taught
"don't cheat a persistence test by inlining the literal." That was the BUG: a pointer-only
call sign requires a trigger to fire; without the trigger the agent answers the injected
default ("Hermes Agent") and the call sign is LOST on reset. This failed the founder's
2026-08-08 persistence test.
- CORRECTED: critical call signs inline in fastlane.md + MEMORY.md; bulk context
  retrieve-on-demand. Inlining a critical call sign is NOT a cheat — it is the fix.
- See `references/indirection-append-only.md` for the full corrected model + failure narrative.

## Pitfall — REVERSED: inlining a critical call sign is the fix, not a cheat
If the founder sets a "who are you" persistence test, the correct solution is for the call
sign to be INLINED in the auto-loaded fast lane so it survives reset every time — NOT a lazy
READ trigger. The earlier "don't cheat by inlining the literal" guidance was WRONG and caused
the failure. Pointer indirection is only for bulk context; critical call signs go inline.
