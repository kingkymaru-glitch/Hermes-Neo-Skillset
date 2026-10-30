---
name: ai-assisted-team
description: >-
  Operate as a teammate on a project run by a human Founder + one or more AI
  agents acting as CTO/co-developers. Covers the "team of 3" loop: onboarding an
  AI CTO onto a PRIVATE repo WITHOUT pasting the project, the handoff-doc
  pattern, the agent-file (CLAUDE.md/AGENTS.md) convention, token discipline,
  and the Hermes "Co-founder #3" quality-gate role. Trigger on: "bring Qwen/ChatGPT/
  Claude/Codex into the loop", "give the AI access to the repo", "team of 3",
  "how do we collaborate with an AI CTO", "stop pasting the whole project", or
  any multi-agent coding-team setup.
---

# AI-Assisted Team (Founder + AI CTO + Hermes as Co-founder)

Class-level playbook for running a coding project where the user is the Founder
and one or more AIs are teammates (e.g. Qwen/Claude/Codex as "CTO" run as a coding
agent). The recurring trap: dumping the entire codebase / `.xcodeproj` / bulk
source files into chat to "get the AI up to speed" — that wastes tokens and
context, and the AI still can't act on it. The fix is repo-as-source-of-truth +
tight just-in-time context.

## The 3 roles (set expectations first)
- **Founder (user):** product decisions, owns the GitHub remote, approves/merges PRs.
- **AI CTO (e.g. Qwen):** implements from the punch-list; branches + opens PRs.
  Runs as a CODING AGENT (Claude Code / Codex / hosted agent) pointed at a clone —
  NOT a chat window you paste to. (If it MUST be chat-only, see Token-discipline.)
- **Hermes (you, Co-founder #3):** keep PROGRESS.md + punch-lists current, run
  static checks (`swiftc -parse` for Swift, `npm run build` for web), gate quality
  before the Founder reviews/merges. Be the integrator.

## Onboarding an AI CTO onto a PRIVATE repo (no project pasting)
1. **Repo must be clone-ready:** `git status` clean, local == remote
   (`git rev-list --left-right --count main...origin/main` => `0 0`). Push first.
2. **Give repo access**, in order of preference:
   - **Collaborator** (best): create/use a GitHub account for the AI, invite at
     repo Settings → Collaborators. The agent clones with that account's token.
   - **Fine-grained PAT**: generate a PAT (read/write on THAT repo only) and hand
     it to the agent's environment. Never a full-account token.
   - **Chat-only fallback** (no git access): you become the bridge (see below).
3. **Write a handoff doc** committed to the repo so the agent reads it on clone —
   never paste the tree. Name it `ANGlerGO_HANDOFF.md` / `AGENTS.md` /
   `CLAUDE.md`. It MUST contain: what the app is, the stack, the 3 roles, the
   open KNOWN GAPS as a production-readiness checklist, and the "resume rule".
   Ground every claim in existing docs (PROGRESS.md, punch-lists) — invent nothing.
4. **Agent-file convention:** add `CLAUDE.md` (Claude Code) and/or `AGENTS.md`
   (Codex/generic) at repo root encoding the process so the agent follows it
   automatically:
   - "Read ANGlerGO_HANDOFF.md + PROGRESS.md first."
   - "Implement ONE task per turn. Touch only the files named in that task."
   - "Run `<static-check>` on changed files before declaring done."
   - "Never edit files outside the named task. Never commit secrets."
   - "Open a PR; do not merge. Founder/Hermes review."

## Token discipline (the whole point)
- The `.xcodeproj` is small (AnglerGO's was 236KB) — the token-wasters are pasting
  whole `.swift`/source files, `.DS_Store`, and `DerivedData`. Keep them out of chat.
- Send the AI **only** the handoff doc + the 2–3 specific files for the current task.
  The agent reads the rest from its own clone.
- Chat-only fallback loop: you paste handoff + targeted files → AI returns a diff →
  you apply → Hermes static-verifies (`swiftc -parse` / build) → update PROGRESS.md.

## Production-readiness checklist pattern
Convert "KNOWN GAPS" into a checked list in the handoff doc so "production ready"
is defined, not vibes. For AnglerGO the blockers were: (a) `loadCatchesFromCloud`
must persist new model fields or catches vanish on restart [CRITICAL]; (b) Firestore
schema for shops/owners/calendars; (c) real EXIF extraction; (d) decide Google
Calendar approach; (e) shop-owner auth + security rules. Tick as done; review gates
on it.

## Static verification when there's no IDE on the CLI host
- **Swift/iOS:** Xcode isn't on the CLI host. Use `swiftc -parse <file>` as a syntax
  check (NOT a full compile). Flag clearly that ⌘B + simulator run is the Founder's
  final verify. Never claim "it builds" from `swiftc -parse` alone.
- **Web:** `npm run build` / `next build` is real — use it.
- **Supabase:** apply DDL via `supabase db push --linked` (see supabase-backend P14/
  P15/P21). Verify RLS/approval *state* with a SQL Editor `select` (runs as postgres,
  bypasses RLS), NOT by hammering live signups (supabase-backend P23).

## Growth/health tracking for the team
Add read-only `SECURITY DEFINER` count-only functions (grant to `anon`) and poll
them from a `healthcheck.mjs` that appends a dated row to an Obsidian `HEALTH_LOG.md`
table. Pattern + SQL in supabase-backend `references/metrics-growth.md` (P24). This
gives the team a tracked time-series without exposing PII.

## Red flags to fix early
- Agent editing files outside its task → tighten the agent-file rules.
- "I flipped confirmation off but still stuck" → wrong dashboard screen
  (supabase-backend P2/P9/P10).
- Pending user invisible to admin ("0 pending" but row exists) → `profiles_select`
  over-restricted (supabase-backend P22).
- Adding a gating column locks out the owner → backfill (supabase-backend P20).
