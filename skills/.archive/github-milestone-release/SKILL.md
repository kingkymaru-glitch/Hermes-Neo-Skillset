---
name: github-milestone-release
description: "Prepare a project milestone for release: decide the version bump, commit work in feature-sized chunks, rewrite the README/CHANGELOG, tag, and sync an Obsidian vault as long-term memory. Covers the auth-blocked-push handoff (gh unauthenticated / empty GITHUB_TOKEN) so deliverables are never blocked on credentials."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [macos, linux, windows]
metadata:
  hermes:
    tags: [github, release, versioning, changelog, obsidian, commit-strategy, handoff]
    related_skills: [github-repo-management, github-pr-workflow, note-taking/obsidian]
---

# Milestone Release & Sync

Use this when the user says "wrap up / summarize / release / bump version / update
README + Obsidian / capture every step of development". It is the recurring
end-of-milestone workflow for the M.A.R.U `my-digital-twin` project (and ports to
any repo with the same discipline).

## The milestone-wrapup sequence (in order)
1. **Gather state** — `git status --short`, `git log --oneline -12`, `git branch
   -vv`, `git remote -v`, `grep '"version"' package.json`, `git tag`. Read the
   README and `ARCHITECTURE.md` to see what's already documented.
2. **Decide the version** (see Version Policy). Bump `package.json`, then
   `git tag -a vX.Y.Z -m '...'`.
3. **Commit in feature-sized chunks** (per-feature discipline — never one giant
   "wip" commit). Stage related files only per commit.
4. **Rewrite README / CHANGELOG** to reflect what actually shipped (old READMEs
   routinely predate recent work — verify before trusting them).
5. **Sync Obsidian** (long-term memory) — see Obsidian Sync.
6. **Verify green**: `npm run lint && npm run build` then `rm -rf dist`.
7. **Push handoff** — see Auth-Blocked Push.

## Version Policy
- SemVer `0.MINOR.PATCH` pre-1.0 while major boxes are planned / no prod deploy.
- Treat an implicit Milestone 1 (core feature set landed) as `0.1.0`; a polish /
  UX / consolidation milestone as `0.2.0`, `0.3.0`, etc. Patch bumps for docs-only
  or trivial fixes.
- The tag message and the README "what's new" block must agree.
- Example that shipped: `my-digital-twin` 0.0.0 → 0.2.0 ("professional
  mission-control milestone") after Connection Manager + UI consolidation.

## Commit discipline
- One commit per logical feature, message `type(scope): summary` (feat/fix/docs/
  chore). Keep unrelated WIP in separate commits so history reads as parts.
- Before committing, confirm a new module doesn't break others: grep its imports
  and the files that consume it for removed/renamed exports.

## Auth-Blocked Push (the common blocker)
`gh` CLI is frequently **not authenticated** on this machine, and `~/.hermes/.env`
`GITHUB_TOKEN` is often commented/empty. Public `git ls-remote` still succeeds
(anonymous read on public repos) — so DON'T conclude "no network"; writes MAY be
auth-walled. Procedure:
0. **TRY `git push` FIRST — do NOT assume it's blocked.** On macOS the git
   credential helper (`osxkeychain`) often holds a working HTTPS credential even
   when the `gh` CLI is completely unauthed and `GITHUB_TOKEN` is empty. This was
   verified: with `gh auth status` = "not logged into any GitHub hosts" and
   `GITHUB_TOKEN` empty, `git push origin main --tags` STILL succeeded via the
   keychain. So the real order is: attempt the push, and only fall back to the
   handoff if it actually fails. Use a non-interactive push so a missing
   credential fails fast instead of hanging on a prompt:
   ```bash
   GIT_TERMINAL_PROMPT=0 GIT_ASKPASS=/usr/bin/false git push origin <branch> --tags
   ```
   Then VERIFY it really landed: `git fetch origin -q && git status -sb | head -1`
   (expect `## main...origin/main` with no "ahead") and
   `git rev-parse origin/main` == local HEAD; `git ls-remote --tags origin | grep vX.Y.Z`.
   Note: `gh`-specific commands (`gh release create`, `gh api`) still need
   `gh auth login` even when `git push` works via keychain — they are separate.
   (Also: the `timeout` binary is absent on stock macOS; don't wrap the push in it.)
1. **Only if the push fails**, probe for a usable token before declaring failure:
   - env `GITHUB_TOKEN`; `~/.hermes/.env` `GITHUB_TOKEN=`; `~/.git-credentials`;
     `git config --global credential.helper`; `command -v gh` + `gh auth status`.
2. If none usable: do everything that needs no network — commits, tag, README
   rewrite, Obsidian sync, green build. Do NOT block the deliverable.
3. Hand the user exact run-after-auth commands:
   ```bash
   git push origin <branch> --tags
   gh release create vX.Y.Z --title "vX.Y.Z — <name>" --notes "See README changelog."
   ```
4. State the blocker plainly in your reply; don't pretend a push happened.
Full probe + handoff script → `references/auth-handoff.md`.

## Obsidian Sync (primary long-term memory for M.A.R.U)
Vault root: `~/Documents/obsidian_maru_1`. Resume order: `VAULT MAP.md` →
`HermesProgress.md` → `Projects/` → `DT Inspection *`. Write-back policy:
- Append an entry to `HermesProgress.md` (Date / Task / What shipped / Version
  decision / Verification / Blocker / Notes).
- Create `Projects/<Milestone> Dev Log.md` capturing the commit-by-commit dev
  steps + the push blocker.
- Link the new log from `VAULT MAP.md`.
- Native file tools only — no "Vault Operator" plugin (only `copilot` is
  installed); never fake-install one.

## Verification
- `npm run lint` (oxlint) must be 0/0; `npm run build` (vite) must be green.
- After build, `rm -rf dist` so build output never lands in a commit.
- Visual/UI changes are a visual-approval gate — hold lint nags until the user
  eyeballs the running app, but still confirm the build compiles.

## Pitfalls
- **Stale README trap**: the committed README predates recent features (e.g.
  Governance + UI work). Rewrite from the actual git log, don't just append.
- **Token-absent ≠ push-blocked**: anonymous read works on public repos; and on
  macOS `git push` often works via the `osxkeychain` credential helper even when
  `gh` is unauthed + `GITHUB_TOKEN` is empty. ALWAYS attempt the push first
  (non-interactively) and verify with `git fetch` before claiming it's blocked.
- **Don't fake a push**: if you can't authenticate, say so and hand off commands.
- **Stale branch**: a long-lived `feat/*` branch may sit behind `main`; note it
  for fast-forward when that line resumes — don't silently merge.
- **Shell eats backticks/$() in commit messages**: `git commit -m "… \`shifted\`
  …"` had its backticked word stripped by shell command-substitution, landing a
  blank commit body that needed `git commit --amend -m`. RULE: single-quote the
  message (`git commit -m 'feat: … via the shifted class …'`) or use a quoted
  heredoc; never put unescaped backticks/$() inside a double-quoted `-m`. Re-read
  the final message with `git log -1 --pretty=%B` before pushing.
