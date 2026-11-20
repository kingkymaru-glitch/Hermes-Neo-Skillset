# Safe build → commit → push (don't let a pipe mask a failed build)

## The trap
`npm run build 2>&1 | tail -6 && echo "EXIT=$?" && git add -A && git commit ... && git push`
- `$?` here is `tail`'s exit code (always 0), NOT the build's.
- `&&` chains on `tail`'s 0, so git runs even when the build crashed.
- The tool call returns `exit_code: 0` → looks green, but broken code shipped.

## Worked example (R-Tessera, 2026-08-12)
A duplicate `drawerOpen` prop/state in ProjectNodes.jsx caused:
```
[PARSE_ERROR] Identifier `drawerOpen` has already been declared
```
The `&&`-chained `git push` still ran; Vercel failed to build on the broken commit.
Caught only by a separate `npm run build 2>&1 | head -30`.

## Correct pattern
Option A — single shell, gate on captured exit:
```bash
npm run build > /tmp/b.log 2>&1; BEXIT=$?; tail -6 /tmp/b.log; echo "BUILD EXIT=$BEXIT"
if [ "$BEXIT" -ne 0 ]; then echo "BUILD FAILED — NOT COMMITTING"; exit 1; fi
git add -A && git -c user.name=maru -c user.email=kingkymaru@gmail.com commit -m "..." && git push origin main
```

Option B — split into two tool calls (preferred for visibility):
1. `npm run build > /tmp/b.log 2>&1; echo "EXIT=$?"; tail -6 /tmp/b.log`  → STOP if non-zero.
2. Only then: `git add -A && git commit ... && git push`.

## Rule
- Never pipe `npm run build` / `vite build` directly into `&& git …`.
- Any `| tail` / `| head` / `| grep` swallows the real exit code — capture it first with `> log 2>&1; EXIT=$?`.
- After a real build failure, FIX then rebuild; do not attempt to "force past" with a fresh commit.
