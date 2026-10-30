# Parallel-agent coordination in ~/DTwin (Neo + Trinity, 2026-08-15)

MARU runs two Hermes agents in the SAME `~/DTwin` working tree on one Mac, typing
in both windows. The protocol was authored in the handshake commit and lives at
`docs/AGENT_HANDSHAKE.md` (repo copy is the source of truth; the Obsidian mirror
`Projects/DTwin_Handshake.md` is for MARU's visibility only — edit the repo copy).

## Why this exists
Neither agent can see the other's chat. If both edited `web/main.js`
simultaneously, they'd clobber each other. The protocol gives them isolated
branches + a claim registry so they never edit the same area, and a handoff log
so they know what the other produced.

## Roles
- **Neo** = this (canonical) agent. Works on branch `neo`.
- **Trinity** = the parallel instance. Self-identifies as "Trinity". Works on
  branch `trinity`. She owns `unity/` AR (`SplatLoader.cs`, `PinManager.cs`).
- **MARU** = the founder, typing in both windows, arbitrates conflicts.

## The 6-step loop (do on every task)
```
1. git fetch / read docs/AGENT_HANDSHAKE.md  → see what's claimed
2. Claim your area: set it WORKING in the REGISTRY, git add + commit
3. Do the work (only on your branch, only in your claimed area)
4. Set DONE + write a handoff note (asset path / API shape) in HANDOFF LOG
5. git add + commit again
6. git fetch / git log <other-branch> to see the other's moves
```

## Registry semantics
| Status | Meaning |
|--------|---------|
| FREE | grab it, then immediately claim WORKING |
| WORKING | held by a named agent (holder col) |
| DONE | released; handoff note should be filled in |
| WAITING_ON_NEO / WAITING_ON_TRINITY | blocked on the other agent |
| SHARED (deployments/, docs/) | either may touch; commit small + check first |

Stale claim rule: a claim older than 24h with no new commit is fair game — the
newer agent may take it and note the takeover in `note`.

## Critical gotchas (verified this session)
- **No `origin` remote.** `git pull`/`git push` FAIL
  (`fatal: 'origin' does not appear to be a git repository`). Coordination is
  local: `git fetch` (no-op locally), `git log --oneline <other-branch>`,
  `git checkout -b <name>` from current HEAD. Both branches share the disk
  working tree, so running pipeline artifacts are visible to both regardless of
  branch.
- **Branch-isolation carry-over:** `git checkout -b neo` carries uncommitted
  working-tree changes onto the new branch. If you're mid-work on the wrong
  branch, branch off to preserve it.
- **Huge transient dirs:** the pipeline writes `frames/*/`, `web/assets/*/`,
  `ingest/*/` which are reproducible → keep them in `.gitignore` (they were
  added as `frames/*/`, `web/assets/*/`, `ingest/*/`). Commit only source
  (`web/index.html main.js styles.css logo.svg`, `server.py`, `tools/pipeline.sh`,
  `docs/`, `.gitignore`). Do NOT `git add -A` — it would stage 170MB+ of frames.
- **Claim is a commit.** Your WORKING claim must be a real git commit so the
  other agent sees it via `git log`. A claim only in your working tree is
  invisible to Trinity.

## Worked example (Neo claiming web/ + tools/, 2026-08-15)
```bash
# on wrong branch (trinity), with my work uncommitted in the tree
git checkout -b neo                      # new branch from HEAD, carries my work
# edit docs/AGENT_HANDSHAKE.md: web/ viewer + tools/ pipeline rows → Neo WORKING
git add docs/AGENT_HANDSHAKE.md .gitignore web/... server.py tools/pipeline.sh
git -c user.name=maru -c user.email=kingkymaru@gmail.com commit \
  -m "Neo: claim web/ + tools/ WORKING; LunaV-family pipeline control panel"
git fetch; git log --oneline -3 trinity   # see Trinity's moves
```

## Handoff contract (Neo → Trinity / Trinity → Neo)
- Trinity drops `clean/sample.glb` + `.ply` from the AR build step. The `web/`
  viewer already loads `web/assets/<deploy>/model.ply` — same asset class,
  reusable.
- Neo's web viewer + `server.py` API shape is the contract for what a produced
  model must be named/where (`web/assets/<deploy>/model.ply`) for "View
  Hologram" to work.
- When either produces something the other needs, write it in the HANDOFF LOG
  section of `docs/AGENT_HANDSHAKE.md` and commit.

## Sister project: TriniD + port coordination (2026-08-16)
MARU also runs **TriniD** (`~/TriniD`) as a sibling project, served by ITS OWN
server. Trinity launches TriniD on **9877** (she explicitly avoided 8787, which
Neo holds for a small-learning server).
- **Port map:** DTwin web = **8753**; TriniD = **9877**; **8787 is NOT a DTwin
  port** — under `lsof` it shows as `localhost:msgsrvr`, which is Hermes' own
  message server, not a DTwin/TriniD clash. Don't mistake an 8787 listener for a
  conflict.
- **Before launching any server**, `lsof -i :<port>` to confirm it's free. If a
  stale server is rooted at the WRONG cwd (e.g. a DTwin server started from
  `~/TriniD` served TriniD's assets on 8790 and hid dji_701), `kill -9` the PID
  and relaunch from the correct project root. See the WRONG-cwd pitfall in SKILL.md.
- **Trinity announces launches via the handshake** (she pastes the plan and waits
  for Neo/Smith to coordinate). When you see such a paste, read the handshake,
  confirm no port/area clash, and reply — that IS the handshake in action.

## GOTCHA — the handshake file may be momentarily MISSING
`docs/AGENT_HANDSHAKE.md` is a SINGLE file the other agent may rewrite/recreate
in place. In-session: Trinity announced she was "writing the handshake file now"
and the repo copy briefly DISAPPEARED (`git ls-files` + `ls` both showed nothing;
only `.gitkeep` left) while she recreated it. If your read returns "No such file
or directory", do NOT recreate it from scratch (that's the other agent's job) —
wait a beat / re-read, or fall back to the Obsidian mirror
`Projects/DTwin_Handshake.md` for the last-known claims. Note the gap in your
OWN claim when you next write, so the other agent's in-flight rewrite isn't lost.

## Smith (third worker agent)
A third agent, **Smith**, may be spun up for a cross-lane (one-off) task. Same
rules apply: it coordinates via the handshake + local git only, no `origin`. If
Smith appears, treat its claims like Trinity's — do not touch a claimed area.
MARU's standing instruction (2026-08-16): keep the handshake habit alive across
Neo/Trinity/Smith.
