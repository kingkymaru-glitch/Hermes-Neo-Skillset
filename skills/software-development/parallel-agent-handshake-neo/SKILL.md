---
name: parallel-agent-handshake-neo
description: "Editing DTwin? Read AGENT_HANDSHAKE + Trinity's git."
---

# Parallel-Agent Handshake (Neo — DTwin)

MARU runs TWO Hermes agents on ONE Mac against the SAME ~/DTwin folder:
**Neo (me, canonical)** and **Trinity (parallel copy)**. Neither sees the other's
chat. The ONLY coordination channel is `~/DTwin/docs/AGENT_HANDSHAKE.md` + git.

## When to Use
- ANY task, edit, or session that touches `~/DTwin` — always. This is a standing
  founder-mandated habit, not optional.
- When resuming DTwin work after a gap (read the handshake to see what Trinity
  did while you were away).

## TRIGGER — do this BEFORE ANY edit or task, every session
The founder (MARU) explicitly made this a mandatory habit. On every turn that
touches DTwin, run this check FIRST:

1. **Read the handshake** — `~/DTwin/docs/AGENT_HANDSHAKE.md` (repo copy is source
   of truth; Obsidian mirror `Projects/DTwin_Handshake.md` is MARU-visibility only).
2. **Check Trinity's git moves** — I work on branch `neo`, Trinity on `trinity`.
   Run:
   - `git log --oneline -5 trinity` → what she committed
   - `git log --oneline neo..trinity` → commits ONLY she has (must reconcile)
   - `git branch -v` → confirm I'm on `neo`, not `trinity`
3. **Reconcile** — merge/rebase her commits if any, or at least note them. Never
   edit blindly; her claim table is the arbiter.

## CLAIM RULES (never violate)
- **CLAIM before WORK:** write claim in the Registry (`| area | files | holder |
  status | ts | note |`), set status `WORKING`, then `git add + commit`. Only then edit code.
- **Never touch a Trinity-claimed area.** If an area is claimed by Trinity
  (e.g. `unity/ AR`), leave it alone — set `WAITING_ON_TRINITY` and pick a free
  area or idle. Do NOT edit a claimed area.
- **Branch isolation:** code edits live on `neo` (mine) vs `trinity` (hers), so
  they can't collide. The handshake governs SHARED assets (`.ply`/`.glb`,
  `tags.json`, `PROJECT.md`, the handshake file itself) + the merge moment.
- **Stale claim** (>24h, no commit update) = fair game; note the takeover.

## PROTOCOL LOOP (every task)
```
read handshake → git log trinity → claim (WORKING) → git commit →
do work → set DONE + handoff note → git commit → git log trinity (recheck)
```

## RELEASE
When done: set `DONE` + a handoff note (asset path / API shape / schema so Trinity
knows what to reuse), commit. The handoff fields are under `## HANDOFF LOG`.

## COMMIT IDENTITY
Commit as: `git -c user.name=maru -c user.email=kingkymaru@gmail.com commit -m "..."`
(MEMORY.md is authoritative for the email.)

## PITFALLS
- **Wrong branch:** confirm `git branch --show-current` == `neo` before editing;
  a stale checkout on `trinity` would put my commits on HER branch.
- **Silent divergence:** `git log neo..trinity` empty does NOT mean she's idle —
  she may be mid-task with uncommitted work. Check `git status --short` too.
- **No origin remote:** this repo is LOCAL-ONLY (no `origin`). Coordination is
  via local branches + the handshake file on disk, NOT push/pull.
- **Transient dirs:** `frames/*/`, `train/*/`, `web/assets/*/`, `ingest/*/` are
  gitignored (reproducible pipeline output). Don't commit them.

## VERIFY BEFORE REPORTING DONE
- [ ] On branch `neo`
- [ ] Read handshake; no Trinity conflict on my touched files
- [ ] Claim set to WORKING then DONE in Registry, handoff note written
- [ ] Committed as kingkymaru@gmail.com
