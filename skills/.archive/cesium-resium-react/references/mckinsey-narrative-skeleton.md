# McKinsey-grade narrative skeleton (the "structure is also superb" bar)

MARU explicitly said the CONTENT STRUCTURE of mckinsey_fusion_hero.html is as
important as the theme. This is the reusable scrollytelling skeleton, applied to
LUNAV Labs and reusable for any premium product page. Pair with the
`elegant-web-design-language` skill for the visual language; pair with G45/G46/G47
in cesium-resium-react for the scroll-globe stage behind it.

## The skeleton (7-beat narrative arc, NOT a flat product list)
01 — HERO: eyebrow (mono, gold, rule line) + serif tagline (poetic, not a feature
    list) + dim subhead + dual CTA (gold primary + ghost secondary) + scroll cue.
02 — THE OPPORTUNITY (the stakes): numbered eyebrow, a big serif STATEMENT with an
    EMBEDDED stat ("lose $1.4 trillion"), then count-up stat blocks each with a thin
    gold fill bar + a small source citation.
03 — THE RETURN (proof): "What a living twin returns." → 4 cited ROI figures as
    count-up stats.
04 — THE FAMILY (capabilities): the products AS "layers" — horizontal cards, each =
    number + serif name + status badge + dim blurb + a LIVE mini-visual
    (wireframe globe / scan grid / node net / sonar).
05 — INSIGHT (philosophy): italic serif QUOTE on one side, a LIVING visual (node
    lattice with traveling packets) on the other.
06 — CASE STUDY: "reduced inspection time by 73%" → image (overlay tag) + body
    paragraphs + a 4-metric grid (73% / $4.2M / 0 / 24/7). Label illustrative
    figures as modeled from cited ranges.
07 — CTA FOOTER: huge serif close ("See your assets as they truly are.") + gold
    button + legal row.

## Devices that make it feel premium
- Numbered sections ("01 —", "02 —") as a rhythm device.
- eyebrow → serif headline → dim body → gold CTA, repeated per section.
- Stats woven INTO prose AND as count-up blocks with gold bar fills.
- Mini LIVE visuals per capability card (CSS/SVG, no heavy libs).
- ONE case study with hard metrics + a modeled-savings callout.
- Confident single closing CTA.

## Sourced ROI figures (verified, cited on-page) — for digital-twin / inspection pages
These are REAL, researched numbers used on LUNAV Labs. Cite each as small mono text.
- $1.4T unplanned downtime, Fortune 500 mfg/yr (11% revenue) — Siemens 2024.
- 800 downtime hrs / manufacturer / yr — Deloitte.
- 30% of offshore-wind lifecycle = O&M — ScienceDirect 2026.
- 50–70% downtime cut via digital-twin predictive maintenance — van Dinter / oxmaint.
- 15–25% offshore O&M cost cut via digital twin ($35–50/MWh → lower) — Dataintelo.
- up to 70% inspection cost cut (rope-access → drones) — ScienceDirect LCoE.
- up to 80% faster inspections vs manual — MacroFab / industry studies.
- Modeled callout: 500 MW offshore farm @ ~$40/MWh O&M ≈ $20M/yr; 20% twin cut ≈ $4M/yr.

## LUNAV Labs build anatomy (reproducible)
- Vite + React 19 + Cesium (vite-plugin-cesium) SPA, private repo `lunav-labs`,
  deploys to lunav-labs.vercel.app.
- Fixed Cesium globe stage (right 56%, behind content) with bundled cables +
  live USGS quakes + local LunaV pins, scroll dolly-out camera (G45/G46/G47).
- Foreground doc = the 7 sections; content in `src/content.js` (every stat carries
  a `src` field rendered as a citation).
- Theme = gold #C9A96E / ink #030508 / navy / warm ivory, Cormorant Garamond +
  Inter 300 + JetBrains Mono, grain overlay, hairline dividers.
- Floating up/down navigator (sectionsRef per section; DON'T forget the last
  section's ref or the final down-click is a silent no-op).
