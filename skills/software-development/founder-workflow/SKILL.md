---
name: founder-workflow
description: Terse, confirmation-gated execution style for this founder. Use when task involves UI/UX changes, multi-step coding, deploy verification, or Obsidian/vault updates. Trigger on "step by step", "one chunk", "after UI changes", "self-recheck", "terse", "don't explain too much", "just give me the answer", or any request to work across MARU/RINA/LunaV/R-Tessera/Rosettes projects.
---

# Founder Workflow

## Hard rules
- One chunk per turn. Every chunk must end with ONE confirmation checkpoint before the next step.
- After every UI change, self-recheck for overlaps/stray buttons/hidden breakage before reporting done.
- Prefer real execution evidence over UI screenshots or visual OK gates.
- Do not prompt for low-stakes choices; pick the sensible default and say only what changed.
- If the user says “stop explaining / too verbose / why are you explaining”, switch to terse instruction bullets immediately and never revert in-session.
- **Truthfulness / quality- **Dismissed-feature rule:** when founder says a feature "does not make sense" or "does not function" and tells you to remove/disable it, comply immediately. Do not explain what it was for, do not ask "are you sure", do not give a rationale — just remove it. They've already decided.
- **UI control consolidation rule (explicit founder instruction, LUNAV client-report build):** do NOT ship redundant or broken UI controls. The founder rejected a panel that had (a) two buttons reaching the same destination, (b) a second QR button duplicating another tool's QR, and (c) a "Generate QR" button that silently failed because it loaded a 404 CDN script. Rules:
  - One feature = one intuitive entry point. If two buttons reach the same place (e.g. a panel "Open share link" duplicating the Settings "Export Link" modal), remove the duplicate — pick the spot that matches the feature's purpose.
  - Don't crowd a tab/panel with controls for other surfaces. Put client-delivery controls in the client-delivery spot; put on-site/inspector controls in the inspector surface.
  - A control that doesn't work must be FIXED with the correct library/API or REMOVED — never shipped as a dead button. Verify the control actually fires (renders/triggers) before reporting done. The "prove it works" mandate applies to UI, not just architecture.
  - Prefer fewer, clearly-labeled controls over many ambiguous ones.
- **Sequential-build rule (explicit founder instruction, ERP-PILOT):** when a multi-module build is in play, build MODULE-BY-MODULE, never in parallel. Founder: "module by module, i dont trust parallel works." One vertical slice proven before the next starts. Do not propose parallel tracks even if it would be faster.
- **Dual-memory sync rule (sibling-agent projects):** when a project has a dedicated sibling agent (e.g. ERP-PILOT -> LISA at profile `lisa` / wrapper `~/.local/bin/lisa`), "update local memories as well" means BOTH your own MEMORY.md AND the sibling's `memories/MEMORY.md` must be refreshed with the same project state. Do both in one pass.
— **Truthfulness / quality- **Dismissed-feature rule:** when founder says a feature "does not make sense" or "does not function" and tells you to remove/disable it, comply immediately. Do not explain what it was for, do not ask "are you sure", do not give a rationale —guard rule:** the founder explicitly requires that you NEVER agree to a suggestion that would produce lower-quality work. If his suggestion would lead to worse results, you MUST highlight the reason and present the options (with trade-offs) — do not silently comply. Be truthful even when it contradicts the request. Only implement his chosen option if he has his own stated justification; if it's still clearly worse, say so and offer the better path again. This overrides deference: agreeableness is not a virtue here, correctness is.
- **Stop-signal / pivot rule:** if the user says “leave it and move on”, “stop, move on”, or otherwise reverses/pivots mid-flight, ABANDON the in-flight task immediately and KEEP its state (do not delete uncommitted work, do not revert changes). Answer the NEW ask only — do not bundle the abandoned task into the reply, and do not resume it in a later turn unless explicitly re-requested. A pivot supersedes any earlier instruction. This overrides the one-chunk-per-turn checkpoint rhythm: when reversed, stop, don't checkpoint.

## Transient-tooling rule (don't burden the Mac)
The founder repeatedly insists local services must NOT linger: "i dont want to burden this mac
with soo many things running", "kill the local firecrawl", "tear down after use". Apply:
- Spin up a local server/container (SearXNG, dev server, proxy) ONLY for the duration of the
  task that needs it. TEAR IT DOWN immediately after (stop container, `docker compose down`,
  confirm port free via `lsof -ti:<port>`). Leave the cached image only if zero-footprint is
  explicitly waived.
- Prefer the lightest viable option: a single SearXNG container (512MB) over a full Firecrawl
  stack (Redis+RabbitMQ+Postgres+FoundationDB, 8GB+). Firecrawl's prebuilt image is also gated
  behind ghcr auth and may 404 — SearXNG is the lighter, keyless default.
- Don't install persistent background daemons or enable autostart for one-off work.
- This is a standing preference, not a one-time ask — honor it even when the user doesn't
  restate it each session.

## Vault contracts
- `/Users/kamarulhk/Documents/obsidian_maru_1` is the primary update surface for progress, roadmap, and health logs. Native file tools only. Do not use Vault Operator plugin assumptions.
- Required read order when touching project state: `VAULT MAP.md` → `HermesProgress.md` → `Projects/<project>` before writing progress back.

## Project lines
- MARU repo = `~/my-digital-twin`. MARU is live.
- R-Tessera repo = `~/Documents/R-Tessera`.
- LunaV = rebrand of SS Rover Cloud. Do not reintroduce old naming/logo in UI or docs unless asked.
- **CDM repo = `~/CDM` (GitHub `kingkymaru-glitch/CDM`, private; Supabase project `ennvfuaimplxkzfdxfqd`). Co-founded with an enterprise partner:** the partner authors tightly-scoped, per-milestone "anti-drift" prompts; execute each milestone as its own committed **V0.xx** build (never reuse a version) and review before the next. Approved stack is Next 14 App Router + Tailwind dark + shadcn/ui + Lucide + Cesium (runtime-CDN) + Supabase/PostGIS — no unapproved imports. Full state in `Projects/CDM/CDM.md`.
- **Visible version stamp must track the tagged build (explicit MARU rule):** every web app this founder ships shows a `POC Shell · V0.xx` (or similar) version pill in the header. Keep it in ONE source constant (e.g. `lib/app-version.ts` `APP_VERSION`) rendered from the header — never a hardcoded string in the component — and bump it in the SAME commit as the milestone tag. The version he sees on localhost MUST equal the build version he was told was shipped; a stale hardcoded stamp turns the app into a black box. On release: bump `APP_VERSION` → build → confirm the new stamp is in the served HTML (`grep -o 'V0.0N' .next/server/app/index.html`) → commit together.
  - **Check the SERVED stamp when auditing a family of apps, and treat a MISSING stamp as a finding.** Sibling apps in the same family drift: one shows `v0.5.0 · build <sha>` and its sibling shows nothing at all. A project with no stamp cannot be attributed from outside (which build is this? is my fix even live?), which is exactly the black box the rule exists to prevent — so flag the gap rather than assuming it.
  - Verify against THREE sources and reconcile them: the repo constant, `package.json` `version`, and the newest production deployment's commit. A stamp disagreeing with the deployed build is a stale stamp, which is worse than none. Note whether the stamp is build-time-injected (visible to `curl`) or client-rendered only (not) — that decides how you can check it.

## Delivery expectation
- Give actionable result first, then reasoning second.

## Schema-timing rule
Do not produce a big upfront database schema for a new system before any features are built. The founder's workflow is feature-first, schema-later: build one end-to-end feature, discover its real data needs, then create only the tables/columns that feature actually uses. Repeat. The schema emerges from working software, not a design doc. Big upfront schema risks becoming useless when implemented features don't align with it.

## Research / learning mode (REINFORCED this session)
- When the user says "before any code, I need to learn / explore / understand X"
  or "I'm not talking about the platform yet, I mean the theory/tools", STOP. Do
  NOT scaffold, do NOT write files, do NOT propose builds. Enter pure
  research/teaching mode: pull real sources (web_search/web_extract, papers),
  then explain the mechanism, theory, and logic in detail. Code comes only after
  they explicitly move to build.
- **Discovery-hold rule (explicit founder instruction):** phrases like "not yet",
  "discover first", "dont update anything yet", "lets discover", "keep exploring"
  mean HOLD BOTH code AND Obsidian/vault writes. Do not scaffold, do not write
  project notes, do not patch skills — stay in discussion/teaching only. The
  founder often reshapes the design across many turns before committing; writing
  notes prematurely commits the wrong shape (this happened: Luna-EDGE had to be
  split OUT of LUNASCAN-SONAR after he said "don't mix this"). Only persist to
  notes/skills/repo when he explicitly says build / write it / commit / update
  the note. Until then, keep the evolving design in the conversation.
- **Feasibility-discussion rule:** when the founder asks "can you do X" / "is X
  feasible" / "write me X" in a discussion context (NOT an explicit build directive like
  "build it" / "create the project" / "go ahead"), do NOT produce the full artifact
  (complete configs, YAML, code files). Discuss the approach, tradeoffs, and
  blockers CONCEPTUALLY — what it would take, what the risks are, what the
  alternatives are. If he wants the actual artifact, he will say "build it" or
  "create it" or "go ahead." Producing a full config during a feasibility check
  reads as too technical and wastes his attention on details he is not ready to
  evaluate yet.
- **Short-thinking rule (explicit founder instruction):** reply the CONFIRMED
  straight answer based on facts/knowledge you have. Do not narrate your
  reasoning chain, do not show the "thinking" process, do not hedge with
  caveats-as-prose. Give the answer, then only the parts that add decision value.
  This is stricter than "terse": it means hide the inference, show the result.
- **ADHD / no-thinking-process rule (explicit, stated 2026-08-17):** the founder
  has ADHD and does NOT want to read your thinking process. "Just spew out things
  u need to communicate to me for decision matters and other important
  clarifications." Applied: lead every reply with the DECISION + the CLARIFICATION
  (or the one question that needs an answer); never narrate hypotheses, exploration,
  or step-by-step reasoning. Pure result + the single fork that needs his input.
- **Answer-from-knowledge nuance:** when the question is general or within your
  existing knowledge, DO NOT fire web_search / web_extract as a reflex. The
  founder said "reply based on facts and knowledge u have" — he wants the
  answer from memory, not a research detour. Reserve live web pulls for when he
  explicitly asks to learn theory / cites / verify a source. Over-searching a
  known answer reads as stalling.
- **Offline-first field-build rule:** when building for the founder's field
  deployments (e.g. remote hydrodam with NO internet), the running artifact must
  have ZERO external runtime dependencies. No CDN script tags (unpkg/jsdelivr),
  no external API calls, no cloud auth at runtime. Vendor libraries locally
  (download once, serve from the app) and keep cloud/Supabase as post-mission
  sync only. The Luna-EDGE Cesium viewer broke this initially by loading
  Cesium JS from unpkg.com — it would have failed at the dam. Always ask
  "does this run with the wifi off?" before shipping a field build.
- **Vendored QR lib gotcha (LUNAV / lunavsolution repo):** the client QR uses the locally vendored `qrcodejs` lib at `public/ar/assets/qrcode.min.js` (NOT node-qrcode, NOT a CDN). Render with `new QRCode(el, { text, width, correctLevel: QRCode.CorrectLevel.H })` then read `canvas.toDataURL("image/png")` off the rendered `<canvas>`. Do NOT call a static `QRCode.toDataURL` (that's the node-qrcode API and throws here) and do NOT load `cdn.jsdelivr.net/npm/qrcode@1.5.3/build/qrcode.min.js` (404). Full recipe + verification: `references/qrcodejs_vendored.md`.

## Real-time local webapp streaming (Flask + WebSocket + vision)
When streaming live vision (YOLO frames, sonar, camera) from a Python engine to a
localhost browser, the GUI shows BLANK if you couple the producer to the WS socket:
- **Pitfall:** engine thread started by `/api/start` captures the WS socket at
  start time. If the browser opens the WS AFTER clicking Start, the socket is None
  at run() → no frames sent → blank GUI. Symptom: WS connects (200) but receives
  nothing; "source map failed to load" in devtools is a RED HERRING (harmless
  Cesium CDN debug-map warning, not the cause).
- **Fix:** decouple. Engine pushes annotated JPEG frames + detection JSON into global
  `queue.Queue` buffers; the `@sock.route("/ws")` handler drains them and sends
  (binary for frames, text-JSON for detections). Connect order no longer matters.
  Browser `onmessage`: `typeof data === 'string'` → detections, else blob→`<img>`.
- **S22-as-IP-webcam for field demos:** install "IP Webcam" on the phone, start
  server, it serves MJPEG at `http://<phone-ip>:8080/video` (probe `/video` and
  `/videofeed` with curl — one returns 200). Phone + Mac must share the SAME wifi
  (iPhone Personal Hotspot = 172.20.10.x subnet works). No internet needed. Pass
  that URL as the `ipcam` source URI.
- Full reusable pattern + verified probe recipe: `references/realtime_vision_webapp.md`.

## Greenfield architecture / design-first mode (REINFORCED — ERP-PILOT)
When the founder starts a NEW build and says "discuss, no code" / "draft it first"
/ "no code, discuss", enter pure architecture-design mode — distinct from
research/learning mode:
- Do NOT write implementation, scaffold, or repo files during discussion.
- Refine the design across turns. Present approach + trade-offs + recommendation,
  await OK each time (matches the standing discuss-first rule).
- When ready, produce a SPEC DOC (README / design markdown) for approval — write
  it to a local draft file first, show the path, let him review, then on approval
  commit/push. Do not push unapproved docs.
- Use the phased-questions pattern: surface the 5–6 real decisions (target user,
  from-scratch vs fork, stack, LLM provider, autonomous vs assisted, module
  order) BEFORE writing the spec, then write it.
- The founder's chosen agentic-architecture methodology (deterministic engine +
  Hermes harness + LLM-reporting-only + human approval gate + shared ontology +
  Coordinator + observable learning) is captured reusable in
  `references/agentic_erp_pattern.md` — reuse it for greenfield agentic/business
  builds rather than reinventing. Key refinements this session: LLM provider is
  Nous Portal (model-selectable, evolve-without-rewire); learning is observable via
  `audit_log` + `tuning` tables; build SEQUENTIAL (no parallel modules).

## Co-dev / shared-repo protocol (REINFORCED — ERP-PILOT went public MIT)
When a repo is opened for co-dev (friends/other devs, possibly agent-assisted):
- Inject a dev protocol into the README: discuss with MARU + domain user BEFORE
  coding each module; agent coders must present understanding and get explicit
  confirmation before implementation. Template in `references/agentic_erp_pattern.md`.
- Nothing sensitive goes in public README (no keys, infra, internal names).
- `gh repo edit <repo> --visibility public` REQUIRES
  `--accept-visibility-change-consequences` or it errors out — include the flag
  when flipping visibility programmatically.

## Speed of delivery (MUST follow — reinforced this session)
- **Default mode is DO, not DESCRIBE.** Don't over-explain. Don't overtalk. Don't prefab. If the user asks 'why', explain then. Purely informational questions that don't need decisions should just be answered concisely, not mixed with action.
- **Investigation is silent.** When debugging, read files, run grep, probe terminals *without narrating* intermediate steps to the user. Say "investigating" once, then present only the confirmed root cause and fix. Do not expose hypotheses mid-stream — the user sees "you're thinking out loud at them" and it reads as slow filler. Distill the investigation into a confident, actionable result, not a transcript.
- **Ping response:** when the user asks "u working?" or "are you there?", answer ≤5 words confirming you're alive (e.g. "Yes, investigating" or "Working on it"). Then continue the task — don't re-explain what you were doing.
- **Investigate-thoroughly rule (the "programmer hat"):** when the founder says
  "put on your programmer hat and investigate this issue thoroughly" (or similar),
  do NOT guess the cause from the symptom. Trace it: read the exact code path
  that produces the error string, identify every place it can originate, and
  verify the actual root cause BEFORE proposing a fix. Present the
  confirmed mechanism, then the fix — but investigate silently, don't narrate the probe.
  This overrides the usual "pick the sensible default and move fast" instinct
  specifically for debugging asks — here thoroughness + evidence beats speed.

- **SQL-handoff anti-loop rule (explicit, from a 4x-failed fix loop 2026-08-17):**
  when you cannot run SQL yourself and must hand MARU a `.sql` to paste into
  Supabase, you MUST verify the schema reality BEFORE claiming it's fixed — read
  `supabase/schema.sql` for the exact column names / constraints / PK shape, and
  prefer patterns with zero constraint dependencies (e.g. UPDATE-then-INSERT over
  `ON CONFLICT`). NEVER send "I found the issue, paste this and it's fixed" more
  than once for the same bug. If a handed SQL fails, the failure is YOUR authoring
  error (wrong column, wrong constraint, var/column collision) — diagnose from the
  actual DB error text, fix the SQL, and only then re-hand it. Repeating
  unverified SQL that bounces is explicitly called out by the founder as
  "non-productive." Also: make the UI surface real DB errors (red text) instead of
  a fake success, so failures are never silent.

## R-Tessera dev-first contract
- R-Tessera local dev server runs at http://localhost:5174 via npm run dev.
- Workflow is local-first: fix in dev, verify in browser, then commit/push → Vercel builds and promotes from GitHub.
- When the user reports a missing UI element locally but the live site shows it, assume local code/CSS/runtime state first. Steps: 1) confirm dev server serving latest src, 2) inspect rendered DOM/state classes, 3) only then inspect deployed source.

## Live-vs-local divergence rule
When the user reports something missing in local but present on the live URL, treat local code first as suspect:
1) verify current dev/build output serves the expected markup/CSS,
2) diff local HEAD against last deployed commit,
3) only then suspect the live deploy. This avoids wasting turns on Vercel-side guesses when the local app is simply stale or mid-refactor.

## Vercel deployment discipline
- When deploying a new branded variant/instance, ALWAYS create a fresh Vercel project from the correct repo/branch. Do NOT try to repoint an existing Vercel project by disconnecting/reconnecting Git — Vercel often silently keeps serving the old build, and the Source line will still show the old repo/commit.
- After any deploy, VERIFY the Source line in the deployment detail shows the expected repo + branch + commit hash. A 200 response is not proof of correct code; the page title/text is.
- **Settling "did my push deploy?" — ask the API, not a file hash.** The Vercel CLI token lives at `~/Library/Application Support/com.vercel.cli/auth.json`; query `GET https://api.vercel.com/v6/deployments?projectId=<prj>&teamId=<team>&limit=5` (ids from `<repo>/.vercel/project.json`) and read `source` (`git` = webhook fired on its own, `cli` = manual), `state`, and `meta.githubCommitSha`. This is one call and it is authoritative. Do NOT infer a failed deploy from an unchanged `index-*.js` hash — in a Vite code-split app the edit may live in a lazy chunk (`GlobeView-*.js`) whose hash is independent, so an unchanged entry hash looks exactly like a missed webhook when the deploy actually succeeded. Reporting a webhook miss that did not happen sends the founder chasing a non-problem.
- For clean isolation, prefer: delete old project → import correct repo → set env vars → deploy. If reusing a project, force a new production deploy from the correct branch and confirm the Source line changed before celebrating success.

## Supabase fresh-project migration pattern
- When combining migrations for a brand-new Supabase project, ALWAYS create tables WITHOUT inline FK references first, then add FK constraints via separate ALTER TABLE statements AFTER all tables exist.
- Inline `references public.other_table(id)` inside `create table` fails on empty Supabase projects with `relation "public.xxx" does not exist`.
- Pattern: create all tables → create all indexes → ALTER TABLE add constraints → enable RLS → create policies → create functions.

## No-fake-gate rule
- Never add fake approval flows, fake pending states, or fake admin checks. If the user says "disable it", remove the code entirely — do not keep a "pending" message variant or redirect. Fake gates create the illusion of a workflow that doesn't exist.

## Compliance / legal-docs scrub rule (co-founded platform builds)
When a partner or third party supplies legal/compliance copy (Privacy Policy, ToS, Cookie Policy) to be committed into a product, do NOT transcribe it verbatim. Drafts from non-lawyer domain partners routinely assert product controls the MVP does NOT actually implement ("TLS 1.3", "at-rest encryption", "strict RBAC", "PDPA-compliant residency") — publishing a policy that overstates real controls is a misrepresentation liability, and the founder has explicitly asked to be kept out of trouble on this. Before committing:
- Scrub every claim to what the code ACTUALLY does. If the app is auth-less / RLS-open / no RBAC, delete or genericize those assertions ("industry-standard safeguards", "as the platform evolves") rather than ship a false control.
- KEEP the genuine risk-shifter: the "AI is advisory / statutory site-safety liability stays with the duty-holder (PD/PC/Client)" disclaimer in the ToS is defensible and useful — do not strip it.
- Render pages dark-mode + professional with NO loud "this is fake" banner; keep the honest legal-review caveat only in the internal `.md` source file.
- Always fix the copyright year to the actual current year, not whatever the draft says.
- Do not present generic POC legal drafts as final binding terms to real clients — flag that Malaysian counsel review is required before public commercial use.
This pairs with the version-stamp rule above: ship what you claim, claim what you ship.

## Destructive / global directive rule
When the user issues a GLOBAL or DESTRUCTIVE directive (e.g. "remove all mock data and its structure", "delete everything related to X", "strip all demo"), do NOT guess the scope and start editing. First explain the mechanism in plain terms, then surface the concrete trade-off (e.g. removing all synthetic telemetry makes the dashboard show nothing until real hardware is connected) and offer the scope choices via `clarify()` with a multiple-choice list BEFORE any code change. The founder consistently wants to choose scope on destructive asks — a wrong guess either nukes usability (over-delete) or ships mock (under-delete). This is a sharper form of the "explain mechanism plainly" rule that applies specifically to irreversible/global edits.
