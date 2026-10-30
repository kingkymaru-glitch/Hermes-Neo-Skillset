---
name: founder-discovery-research
description: Discovery with MARU — facts first, code only when asked.
version: 1.1.0
author: Neo
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [research, discovery, maru, diligence, architecture, no-code-yet]
    related_skills: [cli-comms-style, grounded-citations]
---

# Founder Discovery & Research Collaboration

## When to use
Founder is in research / discovery / architecture mode: asking HOW something works, exploring a new build, says "discovery mode", "before any code", "not yet, lets discover", "wait, i need to learn", or "explain the theory/logic". Also covers the build-measure-explain pattern for hardware / AI / sonar / robotics projects.

## Core rules (embedded from explicit founder corrections this session)
1. STRAIGHT ANSWERS, SHORT THINKING. Founder: "quit overthinking and reply me straight answer after confirmed reply based on facts... keep it short thinking." Lead with the conclusion, then the mechanism. Do not pad with caveat-as-prose. Fact-based, terse.
2. DISCOVERY BEFORE CODE. When user signals discovery ("discovery", "before any code", "not yet"), STAY in explain mode. Explain theory / logic / architecture plainly. Do NOT scaffold, write files, or propose builds until explicitly authorized ("ok lets build", "scaffold it", "start week 1", "build this").
3. MECHANISM FIRST, THEN OFFER. Explain HOW it works (physics / algorithm / data flow) before offering to implement. Founder decides after understanding. Pattern: explain -> offer next step as a CHOICE -> wait.
4. SEPARATE RESEARCH FROM BUILD. A research phase produces notes + decisions, not code. Capture decisions in Obsidian (projects/ notes) when asked. Code is a separate, later, explicitly-authorized step.
5. NO MARKDOWN IN CLI. Terminal-renderable plain text. Avoid heavy markdown; use simple indentation / CAPS for structure. (Global CLI instruction, reinforced here.)

## Workflow
- Detect the mode signal. If discovery: answer factually. Correct misconceptions PLAINLY and directly — founder values being told when an idea is wrong (e.g. "surface GPS does not track a submerged moving ROV"; "sonar 'stereo like humans' is the wrong analogy — sonar gets range from time-of-flight, not parallax"). Honesty > agreement.
- When user proposes a flawed mental model, show the physics/reason it's wrong, then give the right frame.
- End research turns with a concrete set of OPEN QUESTIONS or a CHOICE for the user — not a code dump.
- Only when user says build: scaffold, iterating on the spec already locked in notes.

### Design-discussion shape ("read it and discuss first, no code")
When the founder asks for a discussion about changing an EXISTING app, the deliverable is a
state-then-design brief — not a plan file, not code:
1. **Verify current state from the repo + live git, never from the notes alone.** Vault
   checkpoint notes carry stale HEAD hashes and treat SQL as "applied" when the live DB may
   not match. Grep the actual code paths (component, tab, schema) for the surface the change
   touches.
2. **State what is true today, plainly** — the fields/tables/tabs involved and what the
   current filter or render surface actually supports. Keep "verified from code" separate
   from "as recorded in notes".
3. **Name the gap** in one or two sentences: what the founder's real scenario cannot express.
4. **Give a design with explicit decision points**, each carrying your recommendation and
   the reason — not one unarguable proposal. Include the traps the design must satisfy
   (derived vs stored data, delete semantics, client-portal projections) and what you are
   deliberately keeping OUT of scope.
5. **Close with numbered questions** (naming, cardinality, shape A vs B, confirm the
   out-of-scope boundary) so the founder can answer in one pass. Then wait for the answers
   before touching code.
6. **Keep issuing numbered decisions each round.** A long design discussion runs many turns:
   the founder answers some decisions and raises new ones. Re-close EVERY round with a short
   numbered list of what is still open. Never roll the unresolved forks into prose.
7. **When the discussion locks a design that must outlive the session, publish it as a
   design-lock repo** (GH private + Obsidian note). Do not leave a locked design in chat
   history. Publish the doc set, the numbered decision log, the generated diagrams and the vault
   note as ONE package — the detailed recipe lived in `references/design-lock-repo.md`, which is
   currently missing from this skill; rebuild it the next time a design lock is published.

### Record the REJECTED branch, not just the choice
The highest-value content of a locked design is the fork you did NOT take, and why. For every
decision write three things: the fork, the branch chosen, and the branch rejected with its
one-line reason. A design doc that lists only conclusions cannot be re-derived, re-argued, or
re-applied to a new project — and the founder asks for exactly that re-application later.
On-chain/off-chain, pricing, and identity decisions all read this way.

### Say plainly what a proposed technology does NOT buy
When the founder proposes infrastructure (a chain, a message bus, a hosted service), state the
limits before the benefits: name what it does not provide, and name the configuration in which
it is theater rather than substance (e.g. a single operator running all validators is a hash
chain you control — tamper-EVIDENT, not tamper-PROOF). Then state the rule: never ship a claim
the system cannot literally satisfy. This founder is liability-averse and sells to GLCs whose
procurement will probe the claim — an overstated capability destroys the product's premise.
The honest framing is a decision he will usually take; give him the honest version first.

### Budget the technical depth
Depth earns its place only when it changes a decision. When the founder says some variant of
"this is getting too technical", STOP expanding: answer the question in one or two lines,
lock the decision, and move to closing the round with numbered open items. Do not follow a
fatigue signal with more mechanism — that is the moment to compress, not to teach.

## Pitfalls
- Do NOT jump to code/scaffold during discovery even if you could. Founder will say "before any code". Writing the SPEC repo for a locked design is not code and is expected — writing the implementation is not.
- Do NOT let a locked multi-turn design die in chat history. If the discussion reached decisions, publish them (repo + vault note) in the same session.
- Do NOT answer "do you understand the pipeline/flow?" from the notes or from inference. Read the real code first and quote the actual route, RPC, and SQL file names — see the read-the-source rule above. Inference gets caught.
- Do NOT over-agree with an incorrect analogy. Correct it directly.
- Do NOT merge distinct project scopes into one note. Keep separate projects in separate Obsidian notes (e.g. Luna-EDGE vs LUNASCAN-SONAR are DISTINCT; the founder explicitly said "do not mix this with LUNASCAN-SONAR, the Orin edge kit idea shall be on its own, name it Luna-EDGE"). Respect project boundaries.
- Memory is near capacity (2200-char cap). When saving facts, CONSOLIDATE / REPLACE stale entries rather than add. Remove lowest-value lines first.
- Don't promise capabilities you can't verify. For subagent/externally-visible actions, verify before claiming success.
- Do NOT answer "who owns this / is this project real / find all about X" from the company's own
  site or from press profiles alone. Probe live state — repo activity, model registries, the chain,
  DNS — and answer from that where it disagrees with the marketing. Probe list, the three classes
  of claim, and the temp-file/HTTP-code trap: `references/company-diligence-sources.md`.
- Do NOT blend a founder's self-description with third-party directories and present the result as
  verified. Say which claim came from which class of source, and flag title drift (press pages keep
  calling an ex-CEO "CEO" for years) instead of silently picking the convenient one.

## Related
- USER PROFILE memory: "Asks HOW things work before approving — explain mechanism plainly then offer to implement."
- Identity: agent self-identifies as "Neo"; founder is "MARU". (Fast-lane / MEMORY.md, auto-recalled, no READ trigger.)
- Obsidian ~/Documents/obsidian_maru_1 = primary vault; edit Projects/<Name>.md, never Graphify/.
- `references/design-lock-repo.md` — the design-lock repo shape: doc set, numbered decision log with rejected branches, diagram generation + validation, GH/Obsidian publishing sequence.
- `references/company-diligence-sources.md` — verifying a company or project from public sources: GitHub org and contributor leaderboard, repo renames, HuggingFace org and model licenses, on-chain deployment checks, Wayback for dead sites, title drift, fake-token warning.
- Offline-first reality for field demos: deep-jungle dam has NO internet -> run local, export to LUNAV/Supabase post-mission.

## Reusable architecture pattern observed (source-agnostic vision pipeline)
When building "any camera, live or file" YOLO/detection: four swappable layers, config-selected, no code change between sources:
  Source (webcam / IP-cam / Mavic / file) -> yields (frame, ts)
  Detector (YOLO skill weights) -> Detection[]  [source-blind]
  GeoAdapter (optional: none / mavic_telemetry / fixed_cam / file_replay) -> geo-tagged
  Sink (stdout / local_ws / sqlite / supabase) -> emit
Live and recorded are just two Source implementations feeding the same Detector. Record once, re-detect later with a new skill (crack/ppe) on same footage. Skills = drop-in weights files, not core rewrites.
