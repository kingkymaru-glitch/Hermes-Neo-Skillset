# Scripted bulk replacement — many known strings, one atomic pass

Use when a single change touches many known strings in one or more files: a wording/copy pass, a
version bump through a doc, a status/stats sync, renaming a concept across prose.

## Why not N `patch` calls
- N calls are N chances to silently miss a target that has drifted, and each is a separate round trip.
- A `patch` that finds no match reports a miss you have to notice; a script asserting exact-once
  counts cannot proceed past a stale target at all.
- The `patch` JSON serializer's escape-drift behaviour never applies to a script reading real bytes.

## Recipe

```python
from pathlib import Path

P = Path.home() / "<repo>" / "README.md"
src = P.read_text(encoding="utf-8")

OLD_A = """**Version:** `V0.2.0-phase1`
**Status:** Phase 1 — offline pipeline. Harness built on the Mac."""
NEW_A = """**Version:** `V0.5.0-controls`
**Status:** Phase 1 — active. Console shipped; the pipeline choice rests on real-footage measurement."""

for old, new in ((OLD_A, NEW_A),):
    n = src.count(old)
    if n != 1:
        raise SystemExit(f"ABORT: expected 1 occurrence, found {n} for:\n{old[:140]}...")
    src = src.replace(old, new, 1)

P.write_text(src, encoding="utf-8")
print("blocks updated:", 1, "| file is now", len(src.splitlines()), "lines")
```

## Rules that make it work
- **Anchor on the smallest span that is unique and stable**, not a whole section. Include the
  heading line only when the heading itself is what you are replacing.
- **Never `replace_all`.** Exact-once is the whole safety property; a count of 2 means your anchor is
  ambiguous and you must widen it.
- **Abort, never warn-and-continue.** Skipping a stale target is the failure mode this technique
  exists to prevent.
- **One file per script invocation** is fine and often clearer than trying to batch several files,
  especially when each needs different anchors.
- **A single replacement spanning many lines must match whitespace exactly.** Read the region with
  `read_file` immediately before writing the script; do not reconstruct it from memory.

## Verify after running
Do not trust the exit code. Confirm on disk:

```bash
head -6 README.md                 # the header you just replaced
grep -n '^## ' README.md          # section order / no duplicated heading
wc -l README.md                   # the line count the script printed
```

## When the target is prose in many files
Same script, loop the files, keep a per-file list of `(old, new)` pairs, and let the exact-once
assertion fail the run on the first file whose text has drifted. Fix the pair, re-run — the script is
idempotent only if you re-read each file at the top, so re-read rather than reusing an in-memory copy.
