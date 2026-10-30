# Duplicate Hooks / Patch Fragmentation Traps

Common artifact after multiple targeted patches to sibling feature areas inside one component/file, especially `App.tsx`-style containers.

Symptoms:
- Build succeeds but behavior is nondeterministic.
- Same line appears twice: once from old inline code, once from a partially applied patch.
- React devtools warns about duplicate hook declarations or component state behaving oddly.

Prevention:
- Prefer one focused edit per region; avoid overlapping patches.
- After branching edits to the same file, grep for exact duplicate lines.
- If `patch` fails twice in the same region, rewrite the enclosing function or whole file with `write_file`, then rebuild.

Verification:
- `npm run build` is necessary but not sufficient.
- Manually inspect startup behavior when state initialization changes.
