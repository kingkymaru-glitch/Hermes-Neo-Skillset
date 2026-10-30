# Compaction-handoff write hazard (`...[truncated]` token corruption)

## When this bites
Long sessions get context-compacted; the summary rewrites tool outputs with
`...[truncated]` markers to fit. If you copy a snippet still containing that
marker into a `write_file`/`patch` `new_string`, the literal token lands in the
real file. Silent until a build/lint pass.

## What broke this session
Carrying `...[truncated]` + hand-collapsed JSX into App.jsx produced literal
`\n` text, half-written component blocks (ReconPanel inner cards truncated
away), and a ShortcutsHelpModal.jsx from a truncated skeleton (missing export).

## Mitigations (before claiming green)
1. After any file written from a truncated summary, RUN `npm run lint` +
   `npm run build` in the repo root. A green build is the only proof it isn't
   corrupt.
2. For large files seen only via pagination (App.jsx >1800 lines), RE-READ the
   exact region with `read_file` (no offset/limit) before overwriting.
3. Verify every helper referenced in new code EXISTS in the target module
   (this session called `toNum(...)` in egressDrivers.js without confirming it
   was defined → would be a hard ReferenceError). Grep the module first.
4. Never trust a `...[truncated]`-sourced snippet as complete. Re-derive the
   full text or read it back.

## Rule of thumb
A compaction handoff is a SUMMARY, not source. Paste nothing marked
`...[truncated]` into a file.
