---
name: ai-coding-collaboration
description: Operate as a reviewer / co-founder when another AI coding agent (Qwen, Claude Code, Codex, etc.) implements code that the USER drives on a clone or branch. Verify the agent's claims against the REAL source, challenge wrong decisions with counter-arguments, enforce one-task-per-turn, and gate merges. Use when the user runs a multi-agent team and asks you to review/integrate/correct an agent's output, pastes an agent's "implementation" for sign-off, or gives you an explicit "co-founder / reviewer" mandate.
trigger:
  - User mentions a CTO/agent teammate (e.g. "Qwen the CTO", "run Q as a coding agent").
  - User pastes an agent's code/PR and asks for review, green-light, or "challenge/correct him".
  - User says "you're the co-founder", "make the call", "challenge Q", or "correct him with counter-arguments".
  - Any handoff where an AI agent produced code you are expected to merge/verify, not just apply.
---

# AI Coding Collaboration — Reviewer / Co-founder Loop

When the user drives a separate AI coding agent on a clone/branch and asks you to review,
correct, or merge its output, you are NOT a passive applier. You are the senior reviewer /
co-founder. Catch defects the agent misses, challenge wrong claims with reasoning, and only
green-light code you have verified.

## The loop (one task per turn)
1. **Read the real source before acting.** An agent's "reality check" / "the docs say X" /
   "there's a bug at Y" is a CLAIM, not ground truth. Open the actual file and verify. In the
   AnglerGO session the docs (PROGRESS.md) falsely claimed `loadCatchesFromCloud()` already
   existed — it did not. Trust the code, not the narrative.
2. **Challenge with counter-arguments, constructively.** When the agent is wrong, say so and
   why, with the fix. Example: agent stored full photos inline in a Firestore doc → breaches the
   1 MB document limit. Correction: upload to Firebase Storage, persist the path string.
3. **Apply the correction yourself (you have the repo) — don't just narrate it.** Then
   static-verify (see references).
4. **Update the stale docs** the agent relied on, so the lie doesn't propagate to the next turn.
5. **Commit + push to the authoritative branch**, then hand the next task back to the agent with
   tight context (name only the 2–3 files it needs — never the whole tree).

## Hard rules
- **Never trust an agent's claim of "existing code" — grep/read the file.** Docs and agent
  summaries drift; the source is the source of truth. This is the #1 failure mode when reviewing
  another agent: it will confidently cite a method/field that doesn't exist (or claim a bug
  already fixed), parroting stale project docs. ALWAYS `read_file` the real definition and
  `search_files` for the symbol before believing any "X is missing/broken" statement. (Same
  verify-against-source discipline as systematic-debugging Phase 1 — apply it here.)
- **One task per turn.** Don't let the agent (or you) bundle tasks in one shot.
- **Reject architecture that won't survive production** even if it "works" in a demo
  (inline blobs in a 1 MB Firestore doc, no security rules, hardcoded secrets).
- **Public repo for collab = temporary.** Make the GitHub repo public so the agent's clone can
  pull without an invite; re-private when the sprint ends (`gh api -X PATCH
  /repos/OWNER/REPO -f private=true`). Never commit `.env`/keys while public. Verify no secrets
  are tracked (`git grep` for API keys / `.env` / `.p8`) before flipping public.

## The full-file "corrected rewrite" trap (cost real turns this session)
Another agent (call it "Chairman"/CTO) will sometimes hand you a complete replacement file
with an authoritative narrative ("I rewrote X to be v2-compatible, paste it, Cmd+B") and ask
the USER to Select-All+Delete then paste. DO NOT apply it as-is. Verify THREE things first:
1. **Does it keep every method the live call sites use?** Grep the repo for `ClassName.shared.`
   BEFORE pasting. The Chairman's "v2-compatible" `SupabaseService.swift` silently dropped
   8 methods (`authStateChanges`, `fetchProfile`, `upsertProfile`, `updateProfileDisplayName`,
   `loadCatchesFromCloud`, `saveCatchToCloud`, `loadShopsFromCloud`, `saveShopToCloud`) that
   26 call sites referenced — pasting it would regress 26 errors. The right move: keep the
   existing file, apply ONLY the genuinely-correct part (here, the v2 client-init change),
   and leave all methods intact.
2. **Does it point at the RIGHT project/config?** The same paste hardcoded a DIFFERENT
   Supabase URL (`merfmrlkjoqrhijzfwbn`) than the real one (`ooeowvbrexxoaleodfum` from the
   dashboard/SQL/keys). Swapping it would silently route the app to the wrong database. Never
   accept a config value an agent "helpfully" bakes in — confirm against the real project.
3. **Did the user's "Select All + Delete" already wipe the file?** If the on-disk file is now
   0/1 byte but git has it, RECOVER, don't repaste: `git show HEAD:<path> > /tmp/x.swift` to
   inspect, then `git checkout HEAD -- <path>` to restore the working tree, then apply only
   the minimal correct fix on top. Commit + push.

Net discipline: treat another agent's code as an UNVERIFIED CLAIM, exactly like its prose.
Read the real call sites and config, make the smallest correct change, static-verify, then
report — and tell the user explicitly why you did NOT apply their agent's paste.

## When the user gives a "co-founder" mandate
They want you to MAKE CALLS, not ask. Read the codebase, decide, correct the agent, and report the decision + reasoning. Flag conflicts, then execute. Constructive argument completes the app.

## Communication rule — this founder is NON-CLI
The founder is a product/UI person, not a terminal user. Reporting deploy/DB/infra
steps in jargon produced a genuine "i dont understand what you are saying" (the
words were "apply the migration", "merge the branch", "push to GitHub"). Landing
translations: DB migration = "add columns to the spreadsheet"; branch = "a separate
holding area the live site ignores until merged"; push = "tell the website to rebuild".
Structure every infra step as: (1) ONE plain sentence on WHAT it does, (2) the exact
command, (3) an offer to just do it. Keep terse multi-point (per user profile) but
NEVER assume CLI familiarity. This is consistent with the standing "wants speed,
terse, direct action" profile — clarity first, then execute. If the founder says
they don't understand, STOP and re-explain in analogies; do not re-state the jargon.
the decision + reasoning. Flag conflicts, then execute. Constructive argument completes the app.

## references/
- `references/swift-firebase-static-verify.md` — swiftc -parse syntax checks, FirebaseStorage
  pbxproj linkage check, Firestore 1 MB image rule, auth-listener wiring, call-site compat,
  temporary public-repo-for-collab steps.
