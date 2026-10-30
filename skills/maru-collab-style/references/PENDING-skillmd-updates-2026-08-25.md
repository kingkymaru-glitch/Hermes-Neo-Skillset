# PENDING SKILL.md UPDATES — fold these into maru-collab-style SKILL.md

Captured 2026-08-25 (background review turn). The SKILL.md edit path was blocked
by a read-guard in the curator; these were verified against the live content and
are safe to merge verbatim. A foreground session (or `hermes curator` owner) should
apply them via patch.

## 1. Under "## Voice & format" — append after the "- Terminal context: ..." line:
- When he asks to understand a concept for himself (esp. "explain ... like I'm 15"
  / "so I understand properly" / "elaborate"), use PHYSICAL-WORLD ANALOGIES with
  one concrete actor per system component. Worked archetype that landed well:
  Jetson/Luna-EDGE = a guard watching a screen; R-Tessera/LunaV = the far
  building's big screen; RPi5/MQTT = a mailbox next to the guard that guarantees
  delivery. No jargon inside the analogy; technical terms only AFTER the picture
  is clear. See references/maru-explain-analogy.md for the reusable template.
- He has repeatedly and explicitly said he LIKES when you "highlight the gaps and
  propose our direction." So every design discussion should end with an explicit
  GAPS list + a recommended DIRECTION (your default pick called out). This is not
  optional padding — it is the output he values most.

## 2. Under "## Workflow" — append after the "Only build when he explicitly says
##    build / 'create the project' / 'start'." line:
- HARD GATE — do NOT infer a code go-ahead from adjacent urgency. Phrases like
  "get the demo ready", "we need to prove X", or "make it work" are about
  PREPARING/ARRANGING, NOT authorizing new production code. In the 2026-08-25
  session Neo built a wedge demo after reading "get the demo ready" as a go —
  MARU later re-asserted "no code yet" for the edge code. Lesson: ambiguous
  momentum ≠ explicit "go". When unsure, restate "this is discuss-only, correct?"
  before writing any new production code. Docs / specs / sketches / deploying
  ALREADY-BUILT artifacts are fine under "prepare" — new feature code is not.
- A NARROW go (e.g. "push what's already built to Vercel") does NOT unlock edge
  or feature code. Treat each subsystem's authorization separately; one green
  light does not unlock all.
- When he redirects scope (e.g. "the scream goes to R-Tessera, not LunaV
  Solutions"), update the mental model immediately and flag what you built that
  now needs re-pointing — don't defend the earlier target.

## 3. Under "## Project framing he favors" — append after the
##    "- Offline-first for field demos (no internet at remote sites)." line, as a
##    new "## Deliverables he prefers" section:
## Deliverables he prefers
- Design discussions should be written up as MARKDOWN / OBSIDIAN notes with
  WORKFLOW DIAGRAMS (Mermaid), not left only in chat. He said "i prefer chart and
  workflow" and "write in detail what we discuss on obsidian." When a design is
  aligned, offer to drop a vault note (Projects/<Topic>.md) with wikilinks to
  [[Luna-EDGE]], [[R-Tessera]], [[ROVER-KIT]], [[LUNAV]] and a Mermaid pipeline.
  (Vault path: /Users/kamarulhk/Documents/obsidian_maru_1/Projects/)
- Keep architecture INPUT-SOURCE-OPEN. When building ingest/detection, design the
  source as a pluggable connector (rtsp:// , USB/Insta360, HTML upload, Telegram)
  not a hardcoded one — he approaches DIFFERENT stakeholders, so the same detector
  must swap feeds without downstream changes. Durable design principle for
  Luna-EDGE / ROVER-KIT work, not a one-off.
