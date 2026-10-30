---
name: hermes-self-update
description: "Use when updating Hermes, checking updates, or doctor."
version: 1.1.0
author: Neo
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [hermes, update, git, maintenance, cli, channels, gateway]
    related_skills: [hermes-agent, hermes-team-coordination]
---

# Hermes Self-Update & Update Diagnostics

For the Hermes install living in its git checkout (default path `~/.hermes/hermes-agent`,
resolve with `get_hermes_home()` — never hardcode when a profile is active). Covers
"update Hermes", "clear the N-commits-behind notice", "is an update available",
"what's new / what do I get", "that behind number looks wrong", "a symbol/`ImportError` after the checkout moved
under a running session", "hermes doctor reports something", and "`state.db` is large /
the WAL is huge". Doctor findings and store maintenance are covered in
`references/doctor-and-store-maintenance.md`.

## Procedure

Run these in order. Stop as soon as the question is answered — do not re-derive the
count three ways.

1. **Current state, two commands.**
   ```bash
   hermes --version          # version + "local <sha>" + install directory + install method
   hermes update --plan      # install kind, every profile, every running service with pid,
                             # and how each gets restarted
   ```
   `--plan` is read-only and safe on a live fleet; run it before promising anything about
   restarts. It names the supervisor per service (launchd vs systemd vs serve) — trust it
   over your own process scan.

2. **Is an update available?**
   ```bash
   hermes update --check
   ```
   Prints the selected channel and either "Up to date" or "Update available: N commits behind".

3. **What the install is pinned to.**
   ```bash
   hermes config get update            # per-install channel choices (update.installs)
   hermes config get updates           # check / backup / auto_switch_parked_branch knobs
   ```

4. **Apply — ask first, then run it in the background.**
   ```bash
   hermes update --yes
   ```
   Two things to settle before firing it:
   - **Get an explicit go-ahead.** The update restarts every running service `--plan`
     listed, which ends the live CLI/gateway session. Put the version delta and which
     services restart into the ask, then wait for it.
   - **Run it as a background process** (`background=true, notify=true`) and poll it. A run
     that rebuilds Node/TUI/web dependencies routinely passes five minutes and outlives a
     foreground terminal timeout. The update keeps going after the tool call dies — a
     timeout is NOT a failed update. Poll the process before re-running anything.
   Default backup level is `quick` (a state snapshot across every profile). Pass
   `--backup` to force the full zip, `--no-backup` to skip all of it.

## Channels

`stable` is the default and moves only release-to-release — a checkout is "up to date"
when it sits on the latest published tag even though `origin/main` is thousands of
commits ahead. That is normal, not a bug.

```bash
hermes update --channel main       # one run against main; nothing is saved
hermes update --set-channel main   # follow every commit from now on
hermes update --set-channel stable # back to releases only
```

## "What's new?" / "is there an update, and what do I get?"

A version check and a feature summary are two different questions with two different
sources. `--check` answers the first; the release bodies answer the second. Never answer
the second from memory or from a changelog sitting in the local checkout.

Order: `hermes update --check` (local vs selected release) → the release body for EVERY tag
between local and that release → `nousresearch.com` announcements for Portal-side news
(models, official plugins, tools, promos) → `portal.nousresearch.com` for the catalog and
tiers. Source-by-source commands, the patch-release trap that hides hundreds of PRs of
features behind a "patch release" headline, and the report shape:
`references/whats-new-research.md`.

## Pitfalls

- **Never hand-edit the checkout to "catch up"** — no `git pull`, `git checkout main`,
  or `git reset` in the source dir. `hermes update` stashes local changes, switches to
  the target commit, restores them, syncs bundled skills, checks config for new options,
  and restarts only the running services. A manual git command skips all of that and
  leaves the checkout detached on the wrong commit.
- **Verify a suspicious behind-count against the real history before repeating it.** A
  count that exceeds the true distance between the checkout and the target ref is wrong —
  compute it directly (`git rev-list --count <head>..<target>`) and report the
  discrepancy with the command you ran rather than repeating the number.
- **Compare against the right ref.** A stable-channel checkout compared to `origin/main`
  shows the full repo distance (thousands); compared to the latest release tag it shows
  only what is genuinely unshipped. State which ref you measured before quoting a count.
- **Report the behind-count with its ref, or not at all.** "N commits behind" is
  meaningless without "behind `origin/main`" or "behind `v0.22.2`".
- **Local edits are preserved by design.** `hermes update` autostashes and restores them,
  then prints a warning. After the run, show `git status` / `git diff --stat` in the
  checkout so the user can see their work is still there — the update is not silently
  destroying local patches.
- **A frontend file edit does not reach the browser on its own.** Updating the source
  does not rebuild the dashboard web UI; say plainly that the dashboard needs its build
  re-run before the user assumes their edit is live.
- **An update can end on an older-looking checkout.** A release tag can be an ancestor of
  `main`, so the checkout may sit "behind main" after a successful update. That is the
  channel working as intended — confirm with `hermes update --check`, not by comparing
  SHAs.
- **An autostash from an older run may still be parked.** `git stash list` in the
  checkout can show an `hermes-update-autostash-<date>` entry that no run will touch.
  Mention it once, offer the drop, never drop it yourself.
- **A running process keeps the modules it imported at start — a code change on disk does
  not reach it.** Python binds imports into `sys.modules` once per process, so a session
  that outlives a `hermes update` (or any checkout move) runs the pre-update code for its
  whole life. An `ImportError` / `cannot import name <symbol>` for a symbol that IS present
  in the checkout is a STALE PROCESS, not a broken install: do not reinstall, re-update, or
  hand-edit git. Check the process start time against the file mtime, confirm the symbol
  exists at the current HEAD and imports in a fresh interpreter, then have the user exit and
  relaunch (`hermes --continue` resumes the conversation). Recipe and exact commands:
  `references/update-diagnostics.md`.
- **The file-editing tools refuse `config.yaml` outright.** Route every config change
  through `hermes config set KEY VAL` / `hermes config unset KEY` and verify with
  `hermes config get KEY`. A hand edit through any other path is blocked before it starts,
  and the CLI appends new top-level blocks at the END of the file — grep for the key
  rather than reading a fixed line range.
- **`hermes doctor` inspects the active profile's config only.** Drift flagged in
  `~/.hermes/config.yaml` usually also exists in every other profile's own config and is
  invisible to the check — verify each profile separately instead of assuming one fix
  covers the fleet.
- **You cannot run `hermes sessions optimize-storage` on your own session.** It refuses
  while any process holds `state.db`, and your session is one of them. Hand the command to
  the user. `--force` rewrites the store under a live writer — exactly the failure that
  leaves every agent refusing turns.
- **An interrupted update is recovered by re-running it — nothing else.** When the run dies
  mid-way (a dropped network during the Node/venv dependency download is the usual cause),
  the checkout is ALREADY on the new commit while the dependencies are still the old ones:
  `hermes --version` reports the new version, but the gateway is left PAUSED, the next
  command warns that gateways were not restarted, and `status` reports "install out of sync".
  Do NOT `git reset` back, do not hand-run `hermes pm install`, and do not call the update
  failed. Confirm the network answers again
  (`curl -sS -o /dev/null -w '%{http_code}' https://nodejs.org/dist/index.json` → 200) and
  re-run `hermes update`: it reuses the pulled commit, finishes the dependencies and restarts
  the paused gateway. Report it as "paused mid-update, finished on retry", never as a broken
  install.
- **A gateway left stopped after an interrupted update is the safety behaviour, not damage.**
  The updater refuses to serve new code against stale modules, so it parks the gateway instead.
  Say that plainly rather than debugging the gateway.
- **When a fix is blocked on a command the user must run, report the blocker and the exact
  command in one short block, then stop.** Do not re-attempt, work around it, or loop.

## Doctor Findings and state.db Maintenance

`hermes doctor` covers the non-update findings: legacy `custom_providers:` drift, an
oversized `state.db`, and a runaway WAL. Triage order: run `hermes doctor`, fix what is safe
from inside the session (config drift), then report what needs a quiet store along with the
exact command the user must run.

`hermes doctor --fix` only takes the paths that can grab an exclusive guard (the WAL
checkpoint). It changes little on a live install — do not promise it clears the findings.

Full procedure, the field mapping for moving a legacy provider entry, the `dbstat` query that
shows what is actually consuming `state.db`, and the holder wall:
`references/doctor-and-store-maintenance.md`.

## Repairing an oversized state.db from inside Hermes

`sessions.auto_prune` only bounds growth; it does not shrink the search index. When `hermes doctor`
reports "state.db is large" plus "run 'hermes sessions optimize-storage' offline", the fix is that
command — but **an agent cannot run it on its own profile's store**. `optimize-storage`, `optimize`
and `prune` all fail closed via `held_store_refusal()` while ANY process holds `state.db`, and the
agent's own session is one of them (verify with `foreign_state_db_holders(path)` — expect the agent's
pid in the list). `--force` is the only override, and it rewrites the store under a live writer.

- **Diagnose before promising a number.** The bulk is usually FTS, not sessions: read
  `messages_fts_trigram_data` / `messages_fts_data` from `dbstat` and `fts_storage_version` from
  `state_meta` (missing = predates the current v3 layout). `auto_prune` being `true` (the default)
  does NOT clear the "large" warning — that fires purely on logical size.
- **Never run it from inside the agent's own session without saying so.** If the user accepts the
  risk, do it deliberately: `hermes gateway stop`, an online backup first
  (`sqlite3` backup API from a `mode=ro` connection — safe against a live DB), then
  `hermes sessions optimize-storage --yes --force`, then `hermes gateway start`. A PASSIVE checkpoint
  is what the tool itself uses; it never TRUNCATEs, so it will not race a live writer.
- **Take a backup first and say where it is.** `optimize-storage` makes none. Copying the main file
  alone is not a backup — the WAL sidecar holds committed writes. Report the backup path and keep
  it until the user confirms.
- **The WAL is a separate issue.** A 50 MB+ `state.db-wal` is normal while a gateway runs, and
  `doctor --fix` will refuse to checkpoint it while any holder remains. A direct
  `PRAGMA wal_checkpoint(TRUNCATE)` from a separate connection does succeed against idle holders;
  it is non-destructive (verify `integrity_check` after), but do not present it as risk-free.
- **Do not "fix" a flaky probe.** The "Dead IPv6 route" issue probes `OPENROUTER_MODELS_URL` with a
  2 s timeout and can fire on a transient DNS/route blip. Reproduce it before recommending
  `network.force_ipv4: true` — that setting is a workaround for a non-problem if the path is fine.

## After Any Update

```bash
hermes --version                                            # version, channel, local <sha>
hermes status                                               # Gateway: running, on the new code
hermes status --full | grep -iE "out of sync|outdated|⚠"    # empty output = dependencies clean
```

The grep is the signal that matters. `--version` reads the checkout, not the installed
dependencies, so it prints the new version even when the venv or Node deps are still stale.
An empty grep plus `Gateway: ✓ running` is the real "done".

Report what changed (old version → new version, checkout SHA), what was restarted, and
what still needs a rebuild. A single short block — the user reads this in a terminal and
wants the delta, not the step log.

## References

- `references/whats-new-research.md` — where to look for the version delta and the feature
  list, why a patch release hides its own features, and how to shape the "what do I get"
  answer.
- `references/update-diagnostics.md` — reading a "behind" report, channel and count
  semantics, the commands behind `--check`, verifying a count, diagnosing a stale running
  process from an `ImportError`, and the full flag set.
- `references/doctor-and-store-maintenance.md` — `hermes doctor` triage, editing
  `config.yaml` through the CLI, moving a legacy `custom_providers:` entry into `providers:`,
  diagnosing `state.db` bloat with `dbstat`, `hermes sessions optimize-storage` and why an
  agent cannot run it on its own session, and the WAL finding.
