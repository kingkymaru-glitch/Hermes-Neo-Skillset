---
name: elegant-web-design-language
description: Use for elegant/premium or "not AI-generated" design asks.
---

# Elegant Web Design Language (MARU's "awesome" bar)

Learned from ~/Desktop/mckinsey_fusion_hero.html — the founder's explicit reference for
premium feel. Internalize and apply by default whenever he says "awesome / classy /
elegant / McKinsey-grade" or a redesign where polish matters.

## PALETTE (dark, editorial, restrained — NOT techy-neon)
- Base ink: #030508 (near-black, not pure black)
- Layered navy: #0A1628 / #111E2E / #1E2D3F (backgrounds, not flat fills)
- Warm ivory text: #F0EBE3 (warm off-white, never clinical #fff)
- Ivory dim (body): rgba(240,235,227,0.6)
- GOLD accent (the ONE hero accent): #C9A96E, gold-dim rgba(201,169,110,0.4)
- Cyan only SUBORDINATE tech accent: #5BA4B4 / #7DD3E8
RULE: warm metallic gold as primary accent. Cool cyan subordinate. AVOID neon
#00e5c3 / #2f9bff as primary — too cheap/techy for this bar.

## TYPOGRAPHY (serif/sans contrast = editorial luxury)
- Display/headlines: Cormorant Garamond, weight 300/400, clamp(2rem,5vw,4.5rem),
  line-height 1.05-1.15, slight negative letter-spacing. Italic serif <em> in GOLD for emphasis.
- Body/labels: Inter, weight 300-400, line-height 1.7-1.8, ivory-dim.
- Eyebrows/labels: JetBrains Mono, 0.6-0.65rem, letter-spacing 0.2-0.25em, UPPERCASE, gold.
  Often prefixed with a rule line or "01 —".
- Load: Google Fonts Cormorant Garamond + Inter + JetBrains Mono.

## MOTION (the soul of "elegant")
- Reveals: opacity 0→1 + translateY(20-40px)→0, ease power3.out / cubic-bezier(0.25,0.46,0.45,0.94),
  duration 0.8-1.2s, staggered.
- Headlines: line-mask reveal — text starts translateY(110%) inside overflow:hidden line,
  slides up. Feels like type rising into frame.
- Scroll: GSAP ScrollTrigger, toggleActions 'play none none none', start 'top 75-85%'.
  Cards stagger; counters animate 0→target with a thin gold bar filling.
- Ambient: slow rotations (time*0.05), breathing scale (1+sin*0.05), mouse parallax (lerp 0.03).
  Subtle, never distracting.
- Hover: gold underline width 0→100%; buttons lift translateY(-2px).

## COMPOSITION / DETAIL
- Generous whitespace, max-width ~1200px, 8vw side padding.
- Thin hairline rules (1px ivory-faint rgba(...,0.15)) as dividers + top accents.
- Grain overlay (fixed, opacity 0.03, SVG fractalNoise) for filmic texture.
- Rhythm: eyebrow + serif headline + dim body + gold CTA, repeated per section.
- Stats: huge serif gold number + suffix, thin gold fill bar.

## CONTENT DELIVERY FOR EXECUTIVE / OFFICE AUDIENCES (35-40 senior execs)

When the brief is a guide, playbook, or onboarding doc for non-technical office workers
or senior execs, apply these on top of the instrument register:

- NO long text walls. A single scrolling page of dense text loses them in 5 minutes.
- Tabbed navigation: front page shows a table of contents; each chapter is its own tab/view.
  Click a tab → that chapter only. One concept per view.
- Short sections. Bullets over paragraphs. One fact per line.
- Modern, tech, minimalist visual: dark or clean light base, one accent, thin hairlines,
  no childish emoji overload, no clutter.
- Psychological hook per section: open each chapter with a punchy headline that speaks to
  what the exec cares about — time saved, looking competent, control, predictability,
  quality, speed, expected output. Avoid generic "Step 1" openers.
- 2 quick-check quiz questions per chapter with reveal-answer, so the reader verifies
  understanding before moving on.
- Malaysian/office context when relevant: use local analogies (kopi, nasi lemak, mesyuarat)
  only if the audience is Malaysian; otherwise keep universal.

Hook examples that land with 35-40 senior execs:
  "Your time is the asset. Protect it."
  "Stop being the bottleneck."
  "Teach it once. Reuse forever."
  "Verify before you trust."
  "Five minutes. Compounding advantage."

Pitfall: do NOT mix the editorial gold/serif register into a tech playbook — it reads as
marketing, not software. Pick the register by brief and stay in it.
Existing page uses cyan/blue + Inter only + plain reveals. To hit this bar:
1. Re-theme CSS vars → ink/navy/gold/ivory. Keep Cesium globe; tint its labels gold, warm the veil.
2. Headlines → Cormorant Garamond (light); body Inter 300; eyebrows JetBrains Mono.
3. Ghost project names → serif, gold stroke/fill (not cyan stroke).
4. Add grain overlay + hairline dividers + gold nav/links.
5. KEEP the scroll dolly-out globe (signature interaction) — just warm it.
6. Reveals → line-mask headlines, staggered cards, gold bar fills.
7. CTAs → gold solid (ink text), hover lift.
Elegance = restraint + perfect easing, NOT more effects. Do not over-animate.

---

# TWO REGISTERS — pick by brief, never mix

The gold/serif language above is the **editorial register**: marketing pages, landing
sections, anything prestige-facing.

The **instrument register** is the other one: product UI, dashboards, operators' consoles,
the 3D twin. Dark technical, mono + grotesk, cyan used only for state. Use it when the
brief is "professional software", "Iron Man", "game-dev HUD", "futuristic but not
overdone" — not editorial.

## The "AI-generated" tell — MARU's brief, verbatim intent
"I know this is soo AI generated. I want to cast that feeling away — professional and
sleek software built by Iron Man, or by the game developer who put effort into making it
look futuristic without overdoing it."

Diagnose before redesigning. What actually produces the generated look, in the order it
matters:

1. **Placeholder content.** Real density — units, asset tags, revisions, timestamps,
   real counts — is the single biggest signal. Rows of lookalike filler read as generated
   no matter how good the CSS is.
2. **Glow on everything.** An accent that appears on every border, heading and button
   emphasises nothing. One accent, used for STATE (selected / live / critical) and nothing
   else. If the current build glows blue everywhere, that IS the tell.
3. **Uniform rounding.** Rounded translucent glass cards in every slot is a template
   shape. Structure comes from hairlines, corner brackets and chamfers; reserve soft radii
   for ambient chrome only.
4. **One typographic voice.** Two is the fix: monospace for data, labels and readouts;
   a tight grotesk for words and headings.
5. **No hierarchy.** If every label is the same size, weight and colour the eye has
   nowhere to land. Set the few numbers large and light; set the many labels small,
   uppercase, wide tracking.
6. **Symmetrical everything.** Precision reads as deliberate alignment and asymmetry,
   not as even spacing between identical boxes.

## What reads as engineered instead

- Tabular numerals (`font-variant-numeric: tabular-nums`) so figures align in a column.
- A hairline system at ~8–12% opacity, plus one stronger hairline for the active edge.
- Uppercase micro-labels at 0.15–0.22em tracking against normal-case values.
- Status colour reserved for status. Danger red on a delete button is fine; red as a
  decorative accent is not.
- Telemetry that a real operator would want: scale, node count, last-scan date, FPS.
- Restraint in motion: state transitions only. No ambient floating, no bounce.

## Explore as 2–3 STANCES, not 2–3 colourways

When the direction is open, build 2–3 standalone HTML variants that take genuinely
different positions on ONE axis (usually density vs. model-focus), then let him pick:

- **HUD overlay** — the canvas is the screen; chrome is thin overlay strips.
- **Dual console** — fixed left/right rails, dense tabular data, the canvas in the middle.
- **Cinematic stage** — near-zero chrome, the model is the hero, four big light numerals.

Two variants that differ only in accent colour are wasted effort. Give each a README-style
note on what it is strong and weak at, and state your own recommendation plainly.

HTML mockups live OUTSIDE the app repo and are served over localhost; see
`desktop-preview` for the path/TCC pitfalls, and `lunav-family-ui` for the 3D twin
application of this register.
