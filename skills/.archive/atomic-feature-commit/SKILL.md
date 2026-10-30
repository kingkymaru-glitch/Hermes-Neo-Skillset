---
name: atomic-feature-commit
description: Deliver a feature as ONE atomic, lint-clean git commit when the working tree already holds the user's unrelated uncommitted WIP in the same files you must edit. Covers the stash → build → commit → restore dance, the `git commit --amend` WIP-pollution trap and its fix, and how to smoke-test pure logic modules under Node without a browser.
---

# Atomic Feature Commit (amid uncommitted user WIP)

## When this applies
- User asks you to build/implement/commit a feature and the repo has uncommitted
  changes in files you'll also touch (e.g. you edit `App.jsx`/`App.css` while the
  user's own Settings/Locate/CM WIP lives in those same files).
- Phrases like "single atomic commit", "per-feature commit", "don't fold my WIP in",
  "keep my changes separate".

The user frequently keeps deliberate uncommitted WIP they want to eyeball/commit
themselves (often after a green local build). Your job: ship YOUR feature as one
clean commit WITHOUT absorbing their WIP.

## Core workflow
1. **Stash the user's unrelated WIP** to get a clean base:
   `git stash push -u -m "wip-pre-<feature>" -- <files-with-their-WIP>`
   Confirm `git status --short` is empty (or only untracked leftovers remain).
2. **Build the feature.** Keep changes minimal/isolated; don't touch their regions.
3. **Verify**: `npm run lint` (0/0) + `npm run build` green, then `rm -rf dist`.
   For pure logic (gate/registry/service), also run a real Node smoke-test —
   see `references/pure-module-node-smoke-test.md`. lint+build only prove it
   compiles; a real run catches logic bugs (e.g. an OFF mode that doesn't block).
4. **Stage ONLY your feature files.** Commit atomically (one feature, one commit).
5. **Restore WIP**: `git stash pop`. Expect conflicts if you + user touched the
   same regions. **Resolve by KEEPING BOTH sides** (your feature + their WIP) —
   non-overlapping regions auto-merge; for overlapping regions splice both in.
6. **Re-verify** lint+build on the merged tree. Drop the stash ONLY after
   confirming their WIP survived intact (`grep` for their markers in the file).

## PITFALL — the amend-pollution trap (high value)
After a `git stash pop` conflict, the tempting "just amend the message/commit" is
a trap:
`git commit --amend --no-edit` re-stages the INDEX, which — post-conflict —
contains the USER'S WIP too. The amend folds their uncommitted, unreviewed WIP
into YOUR feature commit. This breaks atomicity and commits work they wanted to
review separately. **Never `git commit --amend` after a stash-pop that touched
shared files.**

### Fix recipe (rebuild a clean atomic commit)
1. `git reset --soft <base-sha>` then `git restore --staged .`
   (HEAD → base, index reset to base, worktree stays merged).
2. Extract the clean feature-only tree from the **pre-amend SHA** (still reachable
   right after amend — capture it before any further reset):
   `git show <pre-amend-sha> -- <feature-files> > /tmp/feature.patch`
3. `git apply --cached /tmp/feature.patch`
   (stages ONLY feature hunks into the index; worktree untouched = merged).
4. `git add <any-feature-file-you-tweaked-after>` (e.g. a fix in the worktree).
5. **Verify the index is feature-only**, no WIP leaked in:
   `git diff --cached <shared-file> | grep -c "<their-wip-marker>"` → expect `0`.
6. `git commit -m "..."`. Their WIP markers remain uncommitted in the worktree.

## PITFALL — splitting YOUR OWN multi-feature edits across commits (hunk-order drift)
A different hazard from the amend trap: a single file (e.g. `App.css`) holds hunks
for THREE features. You `git add -p` to split it into 3 per-feature commits, but the
hunk prompts are independent of feature grouping, so answering `y/n` per-hunk in
prompt order is easy to get wrong. A crossed selection silently produces an
**intermediate commit that is internally broken** — e.g. commit A adds a JS handler
that toggles `.is-open`, but the `.mcp-card.is-open` CSS rule was answered `n` and
landed in commit C three commits later. Each commit compiles (lint+build green) yet
commit A is broken at runtime. Worse: `git add -p` answers don't survive a `git reset`,
so re-running the split starts fresh and the repeated attempt may mis-select again.

### Detection (cheap, do it before each `git commit`)
After staging a partial file, inspect what actually got staged:
`git diff --cached <file>` — read it. Confirm every identifier the staged code
references ALSO exists in the staged set. If the staged JS toggles a class/var whose
definition is in an unstaged hunk, that commit is broken — move that defining hunk in.

### Fix recipe (already mid-split, commit came out broken)
1. `git reset HEAD~<n>` (undo the bad commits; worktree edits are preserved, so no
   work is lost — this is why reset is safe here, unlike after a stash-pop).
2. Re-run the split with the hunk→feature map written down first:
   - Number the hunks as `git add -p` shows them (`(1/4)`, `(2/4)`, …).
   - Decide each hunk's owner feature, THEN pipe a precise answer string, e.g.
     `printf 'n\ny\ny\nn\n' | git add -p <file>` (1-indexed, one char per hunk in
     prompt order). Reuse the exact same ordering when re-running.
   - After staging, `git diff --cached <file>` to confirm the set is self-consistent
     before committing.
3. Commit per feature in CHUNK order; re-verify `git diff --cached` on the LAST
   feature (its staged set should be whatever hunks remain).
4. Final `git status --short` clean + lint+build + `rm -rf dist`.

### Hard rule
Never `git add -p` a multi-feature file on hunches. Map hunk → feature, drive the
prompts with an explicit `printf` answer string, and `git diff --cached` the result
before every commit. A commit that references an undefined symbol/class is broken
even when lint+build pass.

## Technique — deterministic multi-feature split via HEAD-reset + selective re-apply
When YOUR OWN edits span N features in the SAME file(s) (no user WIP involved)
and you must land them as N atomic commits, `git add -p` hunk-guessing (see
hunk-order drift above) is error-prone and the stash dance (Core workflow) is
overkill. **Deterministic recipe** — used this session to split a 3-feature
`App.jsx` into 2 atomic commits while keeping the 3rd feature uncommitted:

1. Save the full working file out-of-tree: `cp src/App.jsx /tmp/App.full.jsx`.
2. `git checkout -- src/App.jsx src/App.css` → file reverts to HEAD (clean base).
3. Re-apply ONLY feature A's edits (via targeted `patch`/edit) to the HEAD file.
4. `git add <files> && git commit -m "feat(...): A"` — committed tree == HEAD +
   feature A only (verifiably atomic; no WIP leaked in).
5. Restore the full tree: `cp /tmp/App.full.jsx src/App.jsx`. Working tree now
   has B+C uncommitted again.
6. Repeat 2–5 for feature B.
7. Final: A and B committed atomically; C remains uncommitted for the user.
   `git diff --stat` should show only C's files.

Why it beats `git add -p`: no per-hunk prompt answers to mis-guess (each commit
is a whole-file re-application you control), no stash-pop conflict resolution,
and no amend-pollution risk (you never amend). Cost: you re-type/port the feature
hunks — cheap for small focused edits; use `search_files` + `patch` to re-apply
precisely. Use when the features are cleanly separable in the file and you have
the full version saved. SESSION: this landed `feat(map): initialize camera view
centered on Malaysia...` and `feat(ui): add professional 26px Status Rail...` as
two clean commits, leaving the Map Control rewrite uncommitted.

## Verify before declaring done
- `git show --stat HEAD` lists ONLY feature files (no `EdgeDataContext`,
  `vite.config`, untracked `ConnectionSettings`, etc. that are their WIP).
- `git status --short` still shows their files as uncommitted.
- lint 0/0, build green, `dist/` removed.
- **Do NOT push** unless the user asked. Many users commit/push themselves after a
  green local or Xcode build.

## Adjacent skills
- `vite-build-verification` — proves the Vite build ships; this skill adds the
  local-commit-hygiene + WIP-preservation layer on top.
- `github/github-pr-workflow` — PR lifecycle (branch/commit/open/CI/merge); the
  amend-pollution fix here is a local-commit detail that complements it.
