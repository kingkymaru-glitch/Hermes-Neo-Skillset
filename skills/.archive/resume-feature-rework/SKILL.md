---
name: resume-feature-rework
description: >-
  Workflow for "continue / finish / rework the X screen" requests on a feature
  that already has code. Review-first, punch-list, one-step-at-a-time —
  confirm direction before editing.
triggers:
  - user says "continue", "finish", "rework", "work on", or "update the X screen/view/feature"
  - a feature already has a partial/working implementation and the next step is ambiguous
  - asked "what should the rework focus on first?"
  - the previous turn produced empty assistant output after tool calls, and the user
    replies with "continue" / "process the results above" / "you returned an empty response"
  - resuming an existing web/React prototype with placeholder or identity data that
    needs to be replaced with seeded or real sources
---

# resume-feature-rework

Use this whenever the user asks to continue, finish, or rework a feature that
ALREADY has code — whether that’s a SwiftUI screen, a React module, or a larger
prototype view that is partly mock/hardcoded and partly real. The key move is:
do NOT dive into editing. Review first, publish a punch-list, confirm the axis,
then implement one item per turn.

## Why this exists
When the user was offered "what should the rework focus on first?" for the AnglerGO
Calendar screen (Task 7), they explicitly chose "Just review it and give me a concrete
rework plan/punch-list first" over jumping into an implementation axis (real weather
API, backend sync, UI polish). That is a confirmed preference: on ambiguous rework,
review + ordered task list BEFORE any code change.

This skill applies beyond SwiftUI. A similar outcome appeared in the RIINA prototype
when choosing between exact org-chart identities and generic logins: the better choice
was the seeded-data path, but only because the review step exposed the downstream cost
in owner filtering, delegation, and per-position analytics.

## The "continue the truncated work" recovery workflow (cross-repo)
When the user says "continue what got truncated / cut off" with no specific repo or
task named, the first job is DISCOVERY, not editing. This user runs many parallel
projects (LunaV family, RINA, my-digital-twin/MARU, LUNASCAN, DTwin, crypto_bot),
and an interrupted turn usually left UNCOMMITTED work in one of them.

1. **Find the dirty trees.** Loop `git status --porcelain` over the known repos
   (~/my-digital-twin, ~/riina, ~/lunavsolution-code, ~/Documents/{LUNASCAN,
   R-Tessera, ss-rover-cloud}, ~/luna-edge, ~/DTwin, ~/TriniD). The repo with a
   large uncommitted diff (hundreds of insertions/deletions, deleted files, new
   untracked dirs) is the interrupted one — not a repo with a 2-line nav tweak.
2. **Classify the diff.** `git diff --stat` + read the key hunks. A big deletion
   that removed symbols while OTHER files still reference them = "refactor in
   progress, NOT done" (half-applied). Confirm with `npm run build` — a green
   build here is misleading (see `vite-build-verification` undefined-destructure
   trap); the real test is grepping for the removed identifiers and finding
   remaining references.
3. **Check for a progress note the prior turn left** (e.g. `MARU_FUNCTION_MAP.md`,
   `PROJECT.md`, `PHASE_REPORT.md`, a `.maru_check.mjs`) — it often states the
   intended end state vs. what's actually wired.
4. **Do NOT auto-commit or auto-continue blindly.** Publish a diagnosis
   (which repo, what was in flight, what's broken/unfinished) and the 2 coherent
   finish paths, then ask the user to confirm direction before editing their tree.
   For a "strip demo data" class of refactor (see `local-storage-mock-removal`
   R-Tessera section) the two paths are usually: (A) FINISH the strip — delete the
   orphaned consumers of removed symbols; (B) RESTORE the removed symbols. Pick A
   unless the user says otherwise, and resolve every dangling reference before
   committing.

## Pitfalls

- Do not treat "continue" as automatic permission to edit. Review first unless the axis is already explicit.
- For a bare "continue the truncated work" with no repo named: discovery first (git status across all known repos), then diagnose, then confirm direction. A 2-line nav tweak in one repo is noise next to a 1400-deletion refactor in another — only the large coherent diff is the interrupted task.
- A green `vite build` after a symbol deletion is NOT proof of safety — the removed symbol becomes `undefined` at the consumer and only throws at runtime. Grep for every removed identifier before declaring done.
- Avoid batch edits when the user wants one small polished chunk.
- Do not claim visual polish without mapping each change to actual file paths.
- When consolidating helpers in a file, removing a helper and still referencing it in JSX causes reference errors. Search for remaining references before finalizing.
- For multi-step projects, prefer deriving continuation intent from a durable project note/status file rather than inferring from "continue" alone. Long projects often leave intentional todos; jumping into an unrelated next step wastes a chunk.

## Optional / derived UI fields

If the task is “add a place for members to write/see X” after a type/model change, use a parent-level change handler prop (`onFieldChange?: (value: string) => void`) and update the object via spread/merge. That keeps derived UI state consistent across re-renders and protects against stale local copies.