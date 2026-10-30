# Update Diagnostics

## Why an install reports a behind-count at all

`hermes update --check` resolves a *compare branch* for the selected channel and counts
local ancestry against it. Its own code comments warn about two failure shapes: shallow
installer checkouts (a plain fetch unshallows the repo and `rev-list` then reports a huge
bogus count) and Docker. Both are already handled inside the command — they are not
reasons to distrust a `--check` result on a normal source checkout.

## Channel semantics

- `stable` → the compare branch is the latest published release tag.
- `main` → the compare branch is `origin/main`.
- The choice is stored per install under `update.installs` in `config.yaml`; read it with
  `hermes config get update`. An install that never chose a channel only moves forward: a
  checkout already newer than the latest release stays where it is until a newer release
  ships.
- The docs page for this is `/docs/getting-started/updating` (index at
  `https://hermes-agent.nousresearch.com/docs/llms.txt`).

## Verifying a count yourself

In the install directory (`~/.hermes/hermes-agent`, or `$HERMES_HOME/hermes-agent`):

```bash
# Is the checkout detached? What commit is it on?
git rev-parse --is-shallow-repository
git log --oneline -1

# True distance to each ref you care about
git rev-list --count HEAD..origin/main
git rev-list --count HEAD..<latest-release-tag>

# Is the release an ancestor of main? (YES = normal)
git merge-base --is-ancestor <release-tag> origin/main && echo YES || echo NO

# Detached vs branch: a detached HEAD at a release commit is the normal stable state
git branch -a
```

The `for-each-ref` output is a useful sanity check: if `origin/HEAD` and `origin/main`
point at the same SHA and the checkout sits on a release tag, the install is exactly
where `stable` wants it.

## Flags

| Flag | Effect |
|---|---|
| `--check` | Report availability without changing anything |
| `--plan` | Read-only: install kind, profiles, running services, restart method per service |
| `--yes` | Non-interactive run |
| `--backup` | Force the full pre-update backup (state snapshot + full zip) |
| `--no-backup` | Skip all pre-update backups for this run |
| `--keep-stash` | Never re-apply the autostash (the Desktop updater's mode) |
| `--branch NAME` | Run against a named branch |
| `--channel NAME` | One run against a channel; nothing saved |
| `--set-channel NAME` | Persist the channel choice |
| `--list-venv-holders` | Windows only; which processes hold the venv |

## "cannot import name <symbol> from <module>" in a running session

The checkout moved (an update, a channel switch, a parked-branch restore) while a session,
gateway, or Desktop process was already running. That process imported the old modules at
start and never re-reads them — so a slash command or feature that late-imports a symbol
added by the new code fails, while `hermes --version` reports "Up to date" and the file on
disk is fine.

Confirm the diagnosis before touching anything (all read-only):

```bash
cd "$(hermes --version | sed -n 's/^Install directory: //p')"

# 1. What the running session was started from, and how long it has been alive.
ps -eo pid,lstart,command | grep '[h]ermes' | head

# 2. Does the symbol exist at the current checkout, and does a FRESH interpreter import it?
#    Use the venv python — bare `python` may not be on PATH.
grep -rn "def <symbol>" *.py | head
./venv/bin/python -c "from <module> import <symbol>; print('fresh import OK')"

# 3. When did the checkout move relative to that process start?
git reflog --date=iso -10
stat -f '%Sm %N' <file-containing-symbol>      # GNU stat: stat -c '%y %n'

# 4. Did the commit the process actually loaded carry the symbol? 0 = it did not.
for sha in $(git reflog --date=iso -10 | awk '{print $1}'); do
  echo "$sha $(git log -1 --format=%ad --date=iso $sha) symbol=$(git show $sha:<file> 2>/dev/null | grep -c 'def <symbol>')"
done
```

Fix: exit and relaunch the process. `hermes --continue` resumes the most recent session,
`hermes --resume <id>` a specific one. Same rule for every surface — gateway, Desktop, and
CLI each hold their own imported copy of the code.

This is also why `hermes update` reports which running services it restarted: a service it
did not restart is still serving pre-update code and will show exactly this symptom.

## After the run

`hermes update` reports a fleet version check at the end — each running service's pid and
whether its code matches. If a profile shows a mismatched SHA, its service was not
restarted and needs its own restart.

The receipt for the run lands in the checkout's `logs/update_receipts/`.
