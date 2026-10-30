# git push rejected by a divergent remote — rebase + keep-both recipe

Symptom:
```
 ! [rejected]        main -> main (fetch first)
error: failed to push some refs to 'https://github.com/owner/repo.git'
hint: Updates were rejected because the remote contains work that you do not
hint: have locally. This is usually caused by another repository pushing to
hint: the same ref.
```

Cause: `origin/main` has commits you never pulled — almost always because the
same repo was pushed from a DIFFERENT machine/account (user on laptop, agent on
desktop). This is a non-fast-forward, NOT a code conflict yet.

## Recipe (safe — no force-push)

```bash
# 1) see what's incoming
git fetch origin
git log --oneline HEAD..origin/main

# 2) inspect the incoming commit(s) — which files did they touch?
git show --stat <incoming-sha>

# 3) replay your commit(s) on top of theirs
git rebase origin/main
#    -> if "CONFLICT (content)" appears, resolve (step 4) then `git rebase --continue`

# 4) resolve: KEEP BOTH edits in the conflicted file, drop the markers
#    open the file, delete <<<<<<< / ======= / >>>>>>> lines, splice both sides in
#    verify no markers remain:
#      search_files pattern '^<<<<<<< |^>>>>>>> |^======='  -> expect 0 hits

# 5) typecheck (a stray marker cascades false errors)
npx tsc --noEmit

# 6) finish the rebase WITHOUT an editor hanging it
GIT_EDITOR=true git rebase --continue

# 7) push (now fast-forwards)
git push origin main
```

## Real example (ss-rover-cloud, 2026-08-04)
- Incoming remote commit `4887aba` "feat: GLB model replace + position sliders"
  added a model-row "Replace" (↻) button in `ProjectWorkspace.tsx`.
- Local commit `255ab9f` "Phase 2: model move + rotate" added a model-row
  "Transform" (⤢) button in the SAME file/cluster.
- `git rebase origin/main` conflicted ONLY in that button cluster. Resolution
  kept BOTH the ↻ Replace button and the ⤢ Transform button.
- `GIT_EDITOR=true git rebase --continue` completed the rebase (the plain
  `git rebase --continue` had hung waiting for an editor in a non-interactive
  shell). Push then succeeded; Vercel auto-built + auto-promoted.

## DON'T
- `git push --force` — deletes the other machine's commit.
- `git pull --no-rebase` — creates a merge commit, can duplicate changes.
- Leave conflict markers — `npx tsc --noEmit` will then report a wall of
  "Declaration or statement expected" errors; trust the single
  "Merge conflict marker encountered" line as the root cause.
