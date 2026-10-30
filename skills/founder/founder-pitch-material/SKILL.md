---
name: founder-pitch-material
description: Sketch MARU's pitches as markdown or build .pptx decks.
version: 1.0.0
author: Neo (Hermes agent, for MARU)
license: MIT
platforms: [macos, linux, windows]
metadata:
  hermes:
    tags: [pitch-deck, markdown, mermaid, founder, research, powerpoint, vertical-ai, rfi, tender, bid]
    category: founder
    related_skills: [powerpoint, baoyu-infographic, founder-workflow, maru-collab-style]
---

# Founder Pitch Material

Build investor / pitch / positioning material for MARU's products, starting from an
open question or a research prompt and ending in a visual markdown sketch and/or a
real slide deck.

## When to use

- MARU asks to "sketch it in .md", "i prefer chart and workflow" → produce markdown
  with Mermaid diagrams + chart/table art (diagram-first, not prose-first).
- MARU asks to turn research or a concept into a pitch deck / slide deck.
- MARU names a cloud SaaS tool the agent cannot drive (NotebookLM, Gemini Notebook,
  Google Slides) → build the offline equivalent instead of blocking.
- MARU needs a formal RFI / tender technical response, technical proposal, or
  government/enterprise bid document. Produce a structured markdown document that
  mirrors the issuer's section order and uses their terminology.

## Format preferences (MARU, 2026-08 session)

- Markdown sketches: use Mermaid `flowchart`/`graph` for workflows and ASCII bar
  charts or markdown tables for quantitative data. Lead with the diagram.
- Deliver on the Desktop inside a clearly-named folder. Put a `README.md` index at
  the root.
- Obsidian / VS Code / GitHub render Mermaid, so it's fine to ship `.md` with
  fenced ```mermaid blocks.

## A4 print brochure / one-pager (2-page PDF) — 2026-09-28
When MARU asks for a **brochure, one-pager, or 2-page A4 PDF** (not a deck), build it
with **reportlab**, in a venv, in a Desktop working folder. Full recipe +
verification loop: `references/a4-brochure-reportlab.md`.

Toolchain decisions that matter on MARU's Mac:
- **Never headless Chrome** (orphaned procs block his Chrome) and there is no
  weasyprint / wkhtmltopdf / soffice / pandoc installed. reportlab + svglib in a venv
  is the working path: `python3 -m venv .venv && ./.venv/bin/pip install reportlab svglib pypdf`.
- **Brand mark:** do NOT redraw it. Convert the canonical `favicon.svg` with
  `svglib.svg2rlg()` and place it with `deepcopy(drawing).scale(f, f)` — vector, correct
  colours, clean on dark backgrounds. `qlmanage -t` on an SVG pads it onto a white
  canvas, so it is useless for a dark page.
- **Verification loop:** `pypdf` for page count + exact A4 size + text extraction,
  a numeric overflow audit (every wrapped text block and chip row vs its available
  width/height), then `sips -s format png -Z 1500 page.pdf` → `vision_analyze` to look
  at the render. `qlmanage` on a PDF hangs — use `sips`.

Pitfalls hit while building the LunaV brochure (all real):
- A card accent bar anchored at `y + 97.5` with height 100 drew a stray line across the
  page. Anchor decorative bars at the card's own `y`.
- Diagram content in an inset panel must be bounded by the PANEL, not by its inner
  dashed box: compute each element's right edge against the panel's inner width.
- A label wider than its own box silently overflows (`"BACK IN COVERAGE"` = 50.8pt in a
  49pt box) — check `stringWidth` against the box, not against the page.
- The vision model is ~half reliable: it caught the stray accent bar and the label
  overflow (real), but repeatedly reported "text truncated at the panel edge" that the
  PDF's own text layer and the measured geometry disproved. **Verify every visual claim
  numerically** before "fixing" it — and believe the text layer over the description.

Content discipline for anything client-facing:
- Every claim traced to shipped code or a vault note; anything aspirational goes in an
  "in development" column, never mixed into the product bullets.
- Don't print a domain you haven't curl'd: `luna-v.io` returns `000` (dead) while
  `lunavsolution.vercel.app`, `r-tessera.vercel.app` and `lunav-labs.vercel.app` are 200.

## Entity-naming discipline (SS Rover / LunaV / project names)

- When a response represents the company, use the legal entity FIRST: SS Rover Sdn
  Bhd. Do not lead with project/product names in headers or signatures.
- A product/platform/project name is a subsidiary capability, not a co-equal entity.
  Acceptable phrasing: "SS Rover Sdn Bhd, through its LunaV spatial-inspection
  platform..." or "SS Rover Sdn Bhd — LunaV".
- Unacceptable phrasing: "SS Rover Sdn Bhd / LunaV Solutions", "LunaV Solutions and
  SS Rover", or any structure that implies two separate submitting entities.
- In RFI/proposal headers and signatures, present ONE entity only.

## Workflow — research → markdown sketch → deck

1. **Research.** `web_search` for current trends / market data; cite the source
   inline in the markdown. Keep a condensed copy in `references/` for reuse.
2. **Sketch.** Create a Desktop folder; write a `README.md` plus one `.md` per topic,
   each with a Mermaid workflow + a chart/table. See `references/2026_market_trends.md`
   and `references/maru_products_map.md` from the Vertical-AI session.
3. **Deck (if wanted).** Build a REAL `.pptx` — do not depend on cloud tools.
   Use the bundled `powerpoint` skill: write a JSON spec (see `templates/pitch_deck_spec.json`),
   run `pptx_create.py`, verify with `pptx_read.py --outline`.
4. **Cloud-tool fallback.** If MARU names NotebookLM / Gemini / Google Slides, state
   plainly you can't drive the Google login, then build the offline `.pptx` (or `.md`)
   equivalent and explain. This is the accepted approach — never block on the missing
   cloud tool.

## Building the .pptx (concrete)

- Requires `python-pptx`; if absent `pip3 install python-pptx`.
- Spec supports: `layout`, `title`, `subtitle`, `bullets` (level/bold/italic/color),
  `charts` (bar/bar_h/line/pie with categories+series), `shapes` (rectangle,
  rounded_rectangle, oval, diamond, right_arrow, chevron — fill hex + text),
  `tables`, `notes`.
- Verify with `pptx_read.py deck.pptx --outline` (checks slide count, texts, chart
  values, shape texts).
- PNG rendering needs LibreOffice (`soffice`) + poppler (`pdftoppm`). If absent on the
  host, skip the PNG render and rely on the JSON outline — and tell MARU you verified
  content via outline, not visually. Do NOT claim visual verification you didn't do.

## RFI/proposal document structure

- Mirror the issuer's section order. Do not invent a new outline.
- Include: Executive Summary, Company Profile, Technical Proposal, System Architecture,
  Equipment Datasheets, Preliminary Cost Estimation, Project Timeline, Case Studies,
  Commercial Information, Deliverables Checklist.
- Use tables for requirement-to-solution mapping.
- Leave clear `[tbd]` placeholders for pricing/specs rather than inventing numbers.
- If prior domain POC/report exists, include it as a standalone case-study section
  with lessons applied.

## Pitfalls

- **Duplicate JSON keys** in the spec (e.g. a stray `\"left:\"`) break the build silently
  or misplace shapes — review the spec before running.
- On MARU's Mac the interpreter is `python3` (not `python`); the bundled `powerpoint`
  skill's examples assume `python`. Adapt the command.
- **Never attempt to drive Google-login tools** (NotebookLM, Slides). Build offline.
- **Entity confusion:** do not present a company and one of its platforms/products as
  two separate submitting entities in headers, signatures, or body text.
- Don't harden transient env failures into rules — capture the workflow, not a missing
  binary. (The `powerpoint` skill is bundled/protected; if you want the python3 /
  LibreOffice notes baked in, recommend `hermes curator adopt powerpoint`.)

## Verification

After building, run `pptx_read.py --outline` and confirm slide count, chart values,
and shape texts match intent BEFORE reporting done.

## References

- `references/2026_market_trends.md` — condensed 2026 trend/funding research bank
  (reusable across pitches; dated, refresh when stale).
- `references/maru_products_map.md` — how ROVER-KIT & LunaV map to the vertical-AI
  thesis (the defensible-moat argument).

## Templates

- `templates/pitch_deck_spec.json` — starter 9-slide JSON spec mirroring the
  Vertical-AI deck built 2026-08-25.
