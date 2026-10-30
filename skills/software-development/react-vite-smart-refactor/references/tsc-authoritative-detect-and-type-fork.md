# Authoritative `tsc` detection + TypeScript type-fork root cause (Vite+React)

Use when a Vite + React + TS app shows many cascading `tsc` errors, or when a
build is reported "clean" but you have reason to distrust the tool echo.

## 1. Get the REAL error list (tool echo can be stale)

Terminal dumps / cached `read_file` / snapshot state can look STALE or EMPTY
after edits — a "0 errors" status inferred from tool echo is NOT trustworthy.
Run the compiler inside `execute_code` and parse its stdout:

```python
import subprocess, pathlib
ROOT = pathlib.Path('/abs/path/to/project')  # e.g. /Users/kamarulhk/Documents/RINA
r = subprocess.run(['npx','tsc','--noEmit','--noErrorTruncation'],
                   capture_output=True, text=True, cwd=str(ROOT))
errs = [l for l in (r.stdout or '').splitlines()
        if l[:1].isalnum() and len(l.split(' ')[0].split(':')) >= 3]
print("EXIT", r.returncode, "ERRCOUNT", len(errs))
for l in errs[:60]:
    print(l)
```

Apply edits deterministically (Python `str.replace` with count assertions, or
`sed`) rather than re-reading through a layer that may have cached stale
content. Re-run the SAME block to confirm `EXIT 0` / `ERRCOUNT 0`.

## 2. Type-fork pattern (most common whole-app cascade)

Symptom: dozens of errors in the app entry (`App.tsx`) after a change, while
`types.ts` looks fine.

Root cause: the entry defined its OWN copy of a shared type (`View`,
`AppActions`, event/action union) that DRIFTED from the canonical `types.ts`.
Call-site usage then no longer matches the local copy.

Fix (single source of truth):
- Add the missing member / export the shared interface in `types.ts`.
- Make the entry `import { View, AppActions } from './types'` and delete the
  local duplicates.

## 3. Factory / mock builder widens required fields to optional

Symptom: `Type '...' is missing the following properties from type 'X'`
cascading from a `makeTask` / mock factory.

Root cause: builder returns a type whose required fields (`id`, `status`,
`approvers`, ...) are widened to optional because call sites spread
`...overrides` where `overrides: Partial<Task>`. Also a `.slice()`/transform on
a required field can make it structurally wrong.

Fix:
- Give the builder an explicit return annotation: `function makeTask(overrides: Partial<Task> = {}): Task {`
- Cast the return: `return { ...defaults, ...overrides } as Task;` (call sites
  supply the required fields).
- Remove transforms that mangle a required field (e.g. `id: crypto.randomUUID().slice(0,8)` → `id: crypto.randomUUID()`).

## 4. Two-gate verification

- `npx tsc --noEmit` = TYPE gate (authoritative via the block above).
- `npx vite build` = BUNDLE gate. A type-clean project can STILL fail the
  bundler on a real import/runtime error, so run both before claiming done.
