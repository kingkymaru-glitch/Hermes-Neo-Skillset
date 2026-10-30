# Selective-commit build gate (catch non-buildable commits)

When you commit SELECTIVELY (per-feature: `git add fileA fileB`, NOT `git add -A`),
`git commit` succeeds even if the commit references a file you forgot to stage —
e.g. you add `import MapControlPanel` + mount it in `App.jsx` but never `git add`
`MapControlPanel.jsx`. Lint passes (no syntax error in the staged files), and it
only breaks at BUILD time in CI / for the next dev. `git add -A` would catch it;
selective add does not. (Shipped in this project: commit `fdef1ff` imported
MapControlPanel but omitted the file → non-compiling; had to soft-reset + re-add.)

## Gate: build the COMMITTED tree, not the working tree

After staging a selective commit and before `git commit` (or before `git push`),
verify the committed state compiles by temporarily removing all WIP, building, then
restoring:

```bash
# 1. Stash EVERYTHING not in the index, including untracked (-u). Label it.
git stash push -u -m "pre-push-wip" -- <unrelated files/dirs>

# 2. Build the committed HEAD (real build + lint, not just a syntax sniff)
npm run lint && npm run build 2>&1 | tail -5 && rm -rf dist && echo "DIST_CLEAN"

# 3. Restore all WIP exactly as it was
git stash pop
```

If the build fails, you forgot a file in the index — `git add` it, re-stage, re-run.
Do this for EVERY selective commit before push.

## Surgical commit from an ENTANGLED working tree

`App.jsx` / `App.css` in this project carry several unrelated features at once
(Settings footer, Locate-Me slide, Connection Manager, Layer Orchestrator UI…).
To land ONLY feature X as a clean, buildable commit while leaving Y/Z in the
working tree, do NOT hand-edit the file or rely on interactive `git add -p`.
Reconstruct a HEAD+X-only version and `git apply --cached`:

```bash
# 1. Read the committed base version of the file
git show HEAD:src/App.jsx > /tmp/base.jsx

# 2. Hand-write the HEAD+X-only target into /tmp/feature_x.jsx:
#    = base.jsx + ONLY the X changes (e.g. the one import + one mount line).
#    Keep Y/Z edits OUT.

# 3. Diff base->target, rewrite paths to a/ b/ src/App.jsx, append trailing newline
git diff --no-index --no-color /tmp/base.jsx /tmp/feature_x.jsx \
  | sed -e 's|a/tmp/base.jsx|a/src/App.jsx|' -e 's|b/tmp/feature_x.jsx|b/src/App.jsx|' > /tmp/x.patch
printf '\n' >> /tmp/x.patch

# 4. Validate it applies to the index WITHOUT touching the working tree
git apply --cached --check /tmp/x.patch && echo "PATCH_OK"

# 5. Stage only the patch; the new files for feature X get `git add`ed directly.
#    The working tree still holds Y/Z edits untouched.
git apply --cached /tmp/x.patch && git add src/MapControlPanel.jsx
git commit -q -m "feat(x): ..."

# 6. Verify buildability (gate above) BEFORE push.
```

Key checks: `git apply --cached --check` must pass (else the reconstruction is off);
the committed HEAD must build (stash/unstash gate). After commit, confirm the
referenced file is tracked: `git show --stat HEAD | grep MapControlPanel.jsx` — if
the file is missing from the commit, the commit is BROKEN; soft-reset (`git reset
--soft <prev>`) and re-add, then re-commit. To re-split an already-made multi-feature
commit: `git reset --soft <base>` uncommits the tip but keeps changes staged, then
re-stage per feature and re-commit in order.
