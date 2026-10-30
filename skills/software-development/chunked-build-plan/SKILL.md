---
name: chunked-build-plan
description: Build spans many chunks or founder may jump tasks mid-build.
category: software-development
---

# Chunked Resumable Build Plan

Founder (MARU) builds in long stretches and may pivot to another project mid-way.
When a feature is large (many files, a state machine, multi-chunk), do NOT keep the
plan only in chat — it degrades and is lost on context reset or task-jump. Write a
single living `.md` plan to the Obsidian vault as the resumable vertical.

## When to use
- Build has >3 discrete chunks (e.g. data model → UI → wiring → analytics).
- "no code yet, create an action plan, parse into chunks you can deliver one at a time
  to avoid degradation, write it on Obsidian so when I jump to other task we have the
  same verticals."

## Plan structure (this exact shape worked and was accepted)
Write to `/Users/kamarulhk/Documents/obsidian_maru_1/Projects/<Project> — Action Plan.md`
(keep the existing `<Project>.md` current-state note untouched; this is the build companion).
Include:

1. **§0 LOCKED LOGIC** — every settled rule/decision as the AUTHORITY. If a later
   chunk's text drifts from §0, §0 wins. This prevents re-litigating already-decided
   design in a fresh session.
2. **§1 CHUNK MAP** — table: # | Chunk | Depends-on | Verify-condition. One chunk at
   a time, verify before moving on. Keeps each turn's scope small (anti-degradation).
3. **§2 CHUNK DETAILS** — per chunk: files touched, exact logic, acceptance test.
   Type sketches (TS interfaces, SQL DDL) go inline so the next session codes from them.
4. **§3 RESUME PROTOCOL** — "read top-to-bottom; next un-ticked chunk = active work;
   §0 is authoritative over chunk text." Plus the commit/push author incantation that
   fires the deploy webhook (for RINA/Vercel: `git -c user.name=maru -c user.email=kingkymaru@gmail.com`).
5. **§4 OPEN ITEMS** — decisions resolved this session, recorded so they're never re-asked.
6. **Progress** — checkbox list of chunks; tick as each is delivered+verified.

## Workflow
- Get the logic settled VERBALLY first ("no code yet" is a standing founder mode).
  Only write the plan + code after explicit "GO".
- **Probe the founder's answers for a data-model consequence before writing §0.** Ask the
  few questions that decide the shape (naming, cardinality, which UI surfaces the feature
  touches, what stays out of scope) in ONE clarify call, recommended option first — and
  when an answer implies a consequence he has not seen, spell it out before planning.
  Example: "a repeated model may appear in two groups" sounds like many-to-many, but child
  records (findings, readings) hang off the model row, so a shared row would show the same
  children in both groups and double-count them in every roll-up. Name that, recommend
  "one file, many placements" (a second row sharing the file reference), and get the pick
  recorded. Cheap here; a rewrite if it surfaces mid-build.
- Restate the answers back as a numbered §0 before writing anything — the founder confirms
  or corrects a list far faster than he re-reads prose.
- Deliver ONE chunk, verify (build green / real evidence), tick it, stop. Wait for "GO C[n]".
- DDL/RPC the agent can't run: write clean `.sql` to `~/Desktop/` for the founder
  to paste into Supabase; never claim "applied".
- **Keep the project's own skill in sync as you go.** After each chunk, strike the chunk's
  "still open" line in the skill/references that describe the feature and record what
  actually shipped — a stale "chunks 4–5 open" note makes the next session re-plan or
  re-ask work that is already done.

## Pitfalls
- Don't duplicate the project's existing current-state note — write a separate
  "— Action Plan.md" and backlink it.
- Don't put the whole build in one giant code dump; the chunk map is the point.
- §0 must be copy-pasteable decisions, not prose — future sessions trust it over chat.

## Related
- [[founder-workflow]] (one-chunk-per-turn, discovery-before-build)
- [[maru-collab-style]] (terse, ADHD no-thinking-process)
- rina-task-saas-dev (RINA specifics — recommend `hermes curator adopt` to patch it)
