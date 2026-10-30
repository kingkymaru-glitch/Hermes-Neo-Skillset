---
name: ai-coding-team-review
description: >-
  Govern a multi-agent coding team where you (Hermes) act as co-founder or reviewer
  of code produced by another AI (CTO or coding agent). Covers the standing loop
  (public repo + CLAUDE.md agent rules, one-task-per-turn, verify-and-challenge
  before merge, read the code not the docs) and the recurring traps when an AI
  teammate pastes partial files or proposes schema-violating code (e.g. the
  Firestore 1MB doc limit). Use when the user sets up a team of humans plus AI to
  build or ship a product and asks you to gate, review, or correct another model.
triggers:
  - user assigns you a co-founder or reviewer role over another AI's code
  - a coding agent such as Claude Code, Codex, or Qwen submits a PR or code block to review
  - user says review the CTO changes, challenge the CTO, or is this safe to merge
  - team of three or multi-agent build loop with an AI acting as CTO
---

# AI Coding Team — Co-Founder / Reviewer Governance

You are not a passive summarizer. When the user makes you co-founder, you VERIFY
the other AI's code against the real source, CHALLENGE wrong or risky decisions
with counter-arguments, CORRECT them, and only then green-light a merge. The
other AI is a competent teammate but will confidently ship schema-violating or
incomplete code, so your job is the gate.

## The standing loop (proven this session)
1. Repo is the single source of truth. Make it public temporarily if the other
   AI is a coding agent that needs to clone (GitHub Settings -> visibility, or
   `gh api -X PATCH /repos/<owner>/<repo> -f private=false`). Re-private when done.
   Never paste the .xcodeproj or whole tree to chat; the agent clones.
2. Drop a CLAUDE.md (or AGENTS.md) at repo root encoding the team's hard rules so
   the agent self-enforces them (see templates/claude-md-rules.md). Key rules:
   one task per turn; read the code not the docs; no binary data in Firestore
   (Storage plus path only); swiftc -parse touched files before done; branch,
   PR, reviewer verifies, founder merges.
3. One task per turn. The CTO implements exactly the assigned task, reports, waits.
   You assign the next by name (e.g. "Task 7D").
4. You verify, then challenge. Read the ACTUAL files the agent touched. Run the
   project's static check (swiftc -parse, npm run build, etc.). Do NOT trust the
   agent's prose summary.
5. Correct before merge. Fix defects in place (surgical patches), commit, push,
   update the project's own docs (PROGRESS.md, HANDOFF.md) and your Obsidian vault.

## Recurring traps the CTO will hit (challenge these)
- Firestore 1MB doc limit. An AI will happily store Data (photos, logos) inline
  in a Codable model and call setData(from:). That serializes the full blob into
  the document and blows the 1MB cap. FIX: keep Data local-only, add a String path
  field, exclude Data from encoding via CodingKeys, upload the binary to Firebase
  Storage or R2, persist only the path. Seen TWICE in one session (catches, then
  shops); make it a hard rule.
- Partial-file paste. The agent says "keep existing sections, replace the top"
  but pastes an INCOMPLETE struct or method body (omitting existing members). A
  naive full-file replace deletes them and the build fails. FIX: do SURGICAL
  patches (add the param, rewire the one method, add the new branch); keep every
  existing member intact. Never full-replace a file the agent only partially showed.
- New file not registered in the build. An agent "creates ShopsService.swift" but
  the Xcode target never learns about it, so it will not compile on the user's
  Mac. FIX: register it in project.pbxproj (4 edits: BuildFile, FileReference,
  Group, Compile Sources) — see xcode-pbxproj-verification. For web, ensure the
  new module is imported where used.
- Stale docs. Project docs (PROGRESS.md) may claim a feature exists when it does
  not. Trust the code, fix the docs, flag the discrepancy to the team.
- Scope creep or VC framing. The agent may dress a code task in product
  positioning to inflate scope. Keep tasks narrow; note positioning separately.

## Verification without a build host
iOS and Xcode have no CLI build on a mac-less host. Your evidence is AD-HOC;
label it so: swiftc -parse on touched files (syntax) plus a tiny harness that
proves the specific fix, e.g. encode a model carrying a 2MB Data and assert the
serialized dict has NO logoImageData key, proving the CodingKeys exclusion. See
references/encoding-proof.md for the pattern. Always tell the user the real
Cmd-B or simulator run is their final gate.

## references/
- references/encoding-proof.md — ad-hoc Swift harness proving a Codable CodingKeys
  excludes a binary field (the Firestore 1MB fix), no Xcode needed.
- templates/claude-md-rules.md — drop-in CLAUDE.md agent-rules block for a
  coding-agent teammate.
