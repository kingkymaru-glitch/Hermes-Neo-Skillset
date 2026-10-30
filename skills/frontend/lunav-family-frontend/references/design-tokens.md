# LunaV Family — Design Tokens (reference)

Condensed from `lunavsolution-code/src/app/globals.css` (the source of truth) +
`luna-edge/templates/index.html` (`:root --lv-*` mirror).

## Dark theme tokens (LunaV default for project pages)
--dash-void: #14171c
--dash-panel: #1b1f26
--dash-panel-raised: #232831
--dash-inset: #0f1216
--hairline: rgba(150,175,205,0.14)
--hairline-strong: rgba(150,175,205,0.26)
--glass: rgba(27,31,38,0.82)
--mb-turquoise: #2f9bff        (primary accent, also --lv-turq in EDGE)
--mb-turquoise-dim: rgba(47,155,255,0.14)
--mb-ice: #7db4ff
--mb-amber: #ffb340
--mb-red: #ff4d4d
--txt-primary: #e8eef4
--txt-secondary: #8fa1b3      (BUTTON TEXT at rest + project subtitle)
--txt-tertiary: #55677a
--glow-turquoise: 0 0 18px rgba(47,155,255,0.35)

## Glass theme tokens (globals / iOS frosted)
--glass: rgba(30,38,64,0.55)
--mb-turquoise: #0a84ff
--txt-primary: #f2f5ff
--txt-secondary: #aeb9d6
--txt-tertiary: #6c789b

## EDGE mirror (templates/index.html :root --lv-*) — ⚠ STALE BELOW
The block below records the ORIGINAL EDGE blue theme. EDGE was RE-THEMED to **LunaV LABS gold/navy** on 2026-08-14 — these values are superseded and must NOT be copied:
--lv-void: #14171c          → NOW #030508
--lv-panel: #1b1f26         → NOW #0A1628
--lv-turq: #2f9bff          → NOW #C9A96E (gold)
--lv-amber: #ffb340         → NOW #C9A96E
--lv-txt1: #e8eef4          → NOW #F0EBE3
--lv-radius-sm: 9px         → NOW 10px (header hdr-btn)
Header glass: rgba(20,23,28,0.82) → NOW rgba(3,5,8,0.85) (Labs ink)
--glass: rgba(27,31,38,0.82) → NOW rgba(3,5,8,0.85) for railing/header, rgba(10,14,20,0.6) for panels/launcher
Button primary gradient was `linear-gradient(135deg,var(--lv-turq),#1b6fd0); color:#fff` (BLUE) → NOW `linear-gradient(135deg,#C9A96E,#a8854f); color:#0e1116; border:1px solid rgba(201,169,110,0.4); border-radius:6px` (gold, sharp).
See `references/logo-swap-edge-gold-retheme.md` §2/§8 for the authoritative CURRENT EDGE tokens and the two blue relics (`rgba(27,31,38`, `#1b6fd0`) that the first port missed.
--lv-void: #14171c
--lv-panel: #1b1f26
--lv-panel-raised: #232831
--lv-inset: #0f1216
--lv-hairline: rgba(150,175,205,0.14)
--lv-hairline-strong: rgba(150,175,205,0.26)
--lv-turq: #2f9bff
--lv-ice: #7db4ff
--lv-amber: #ffb340
--lv-red: #ff4d4d
--lv-green: #00c878
--lv-txt1: #e8eef4
--lv-txt2: #8fa1b3
--lv-txt3: #55677a
--lv-radius: 14px
--lv-radius-sm: 9px
--lv-font: 'Inter', -apple-system, 'Helvetica Neue', sans-serif
Header glass: background rgba(20,23,28,0.82); backdrop-filter blur(22px); height 56px.

## .mb-btn (LunaV reference button — the one to mirror elsewhere)
padding: 10px 18px (desktop) / 8px 14px (header); border-radius: 10px;
font-size: 0.78rem; font-weight: 600; letter-spacing: 0.06em;
border: 1px solid var(--hairline);
background: linear-gradient(180deg, rgba(255,255,255,0.05), rgba(255,255,255,0.01));
color: var(--txt-secondary);
hover: color var(--txt-primary), border-color var(--hairline-strong), translateY(-1px);
.mb-btn-primary (active): teal border rgba(0,229,195,0.45), bg rgba(0,229,195,0.16),
  color var(--mb-turquoise), glow.

## .ph-railing (bottom railing — LunaV family)
position: fixed; left:50%; transform:translateX(-50%); bottom:0; z-index:20;
height:46px; padding:0 22px; max-width:70vw;
background: rgba(20,23,28,0.92); backdrop-filter: blur(22px);
border-top: 1px solid var(--hairline); pointer-events:none;
mark: 18px gradient box, "L"; text "LunaV Labs" (Labs in --mb-turquoise).

## .ph-tool-fab (round tool button)
width/height:42px; border-radius:50%;
border:1px solid rgba(0,229,195,0.45);
background: linear-gradient(180deg, rgba(0,229,195,0.16), rgba(0,229,195,0.06));
color: var(--mb-turquoise);
SVG icon 20px.
