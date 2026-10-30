# MARU Design Tokens — exact CSS used across the 3 frontends

## Glass header bar (R-Tessera header, Luna-EDGE header, LunaV nav all share this)
```css
backdrop-filter: blur(22px);
-webkit-backdrop-filter: blur(22px);
background: rgba(20,23,28,0.82);
border-bottom: 1px solid rgba(150,175,205,0.14);
height: 56px;
```
LunaV exposes it as `var(--glass)` + `var(--hairline)` in globals.css (data-theme="glass").

## EDGE-style brand mark (the "L" gradient tile)
Two variants — the mark color is NOT uniform across the family:

LunaV + Luna-EDGE (BLUE):
```css
.mark {
  width: 34px; height: 34px; border-radius: 9px;
  background: linear-gradient(135deg, #2f9bff, #1b6fd0);
  display: inline-flex; align-items: center; justify-content: center;
  color: #0e1116; font-weight: 800; font-size: 17px;
  box-shadow: 0 0 18px rgba(47,155,255,0.35);
}
```

R-Tessera (GREEN — matches LunaV STUDIO turquoise, changed 2026-08-12):
```css
.rt-mark {
  width: 34px; height: 34px; border-radius: 9px;
  background: linear-gradient(135deg, #00e5c3, #00a884);
  display: inline-flex; align-items: center; justify-content: center;
  color: #04110e; font-weight: 800; font-size: 17px;
  box-shadow: 0 0 18px rgba(0,229,195,0.4);
}
```
Do NOT copy the blue mark into R-Tessera.
Wordmark: `LunaV` (white, `.name b`) + project name (turquoise). e.g.
`<div class="lv-brand-name"><b>LunaV</b> <span>STUDIO</span></div>`
`.lv-brand-name span { color: var(--mb-turquoise); font-weight: 700; letter-spacing: 0.06em; }`

LunaV accent tokens (globals.css `:root` / data-theme="glass"):
- `--mb-turquoise: #0a84ff;`  (note: R-Tessera/Edge use `#2f9bff` — pick one; they read close)
- `--txt-secondary: #aeb9d6;`  (grey used for button text AND the project-name subtitle)
- `--txt-primary: #f2f5ff;`
- `--hairline: rgba(180,200,255,0.18);`

## LunaV `.mb-btn` glass pill (reuse on ALL three headers)
```css
.mb-btn {
  display: inline-flex; align-items: center; justify-content: center; gap: 8px;
  padding: 10px 18px; border-radius: 10px;
  font-size: 0.78rem; font-weight: 600; letter-spacing: 0.06em;
  border: 1px solid var(--hairline);
  background: linear-gradient(180deg, rgba(255,255,255,0.05), rgba(255,255,255,0.01));
  color: var(--txt-secondary); cursor: pointer;
  transition: all 0.18s cubic-bezier(0.2,0.8,0.3,1); user-select: none;
}
.mb-btn:hover { color: var(--txt-primary); border-color: var(--hairline-strong); transform: translateY(-1px); }
.mb-btn-primary { border-color: rgba(0,229,195,0.45);
  background: linear-gradient(180deg, rgba(0,229,195,0.16), rgba(0,229,195,0.06));
  color: var(--mb-turquoise); }
```

## Layout rules applied
- One `<header>` / `<nav>` bar, 56px, glass.
- Brand block uses `flex items-end` so the project-name subtitle baseline sits level with
  the button bottoms.
- Tab/action buttons: left-aligned, equal `gap-2` (8px). Settings alone gets `ml-auto` to pin right.
- Luna-EDGE header buttons use class `.hdr-btn` (mirror of `.mb-btn`); sidebar action buttons
  keep the solid turquoise `.btn` style — do NOT let `.hdr-btn` inherit `margin-top:12px` from
  the base `button` rule (set `margin-top: 0` on `.hdr-btn`).

## Project button sets (sync STYLE, not CONTENTS)
- LunaV tabs: 3D Digital Twin · Audit Report · Analytics · Documents (+ Settings right).
- R-Tessera header: Projects (toggles Projects layer) · Data Layers (opens MCP drawer) · LunaV Studio (external link).
- Luna-EDGE header: AI Learning · AI Detection (toggle each other). Its own functions only.
