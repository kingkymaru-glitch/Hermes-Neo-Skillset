# LunaV glassmorphism UI — apply to any MARU webapp

MARU wants every tool in his stack to share the LunaV visual identity, not a
differing dark flat look. When you build/reskin a localhost webapp for his
projects (Luna-EDGE, LunaV Studio, etc.), mirror the LunaV Studio theme.

## Source of truth
Tokens live in `:root` of `~/lunavsolution-code/public/studio/lunav_studio_safe.html`
(the LunaV Studio safe builder). Read that file's `<style>` first if you need the
exact current values — they can drift. Canonical tokens (as of 2026-08-11):

```
--lv-void: #14171c;        /* page bg */
--lv-panel: #1b1f26;       /* panel bg base */
--lv-panel-raised: #232831;
--lv-inset: #0f1216;       /* inputs */
--lv-hairline: rgba(150,175,205,0.14);
--lv-hairline-strong: rgba(150,175,205,0.26);
--lv-turq: #2f9bff;        /* primary accent */
--lv-ice: #7db4ff;
--lv-amber: #ffb340;
--lv-red: #ff4d4d;
--lv-txt1: #e8eef4;  --lv-txt2: #8fa1b3;  --lv-txt3: #55677a;
--lv-glow: 0 0 18px rgba(47,155,255,0.35);
```

## Apply
- Body: `background: var(--lv-void); color: var(--lv-txt1); font-family: 'Inter', ...;`
- Panels/header: `background: rgba(27,31,38,0.82); backdrop-filter: blur(22px);
  -webkit-backdrop-filter: blur(22px); border: 1px solid var(--lv-hairline);
  border-radius: 12px;`
- Primary buttons: `background: linear-gradient(135deg, var(--lv-turq), #1b6fd0);
  color:#fff; box-shadow: var(--lv-glow);` hover lightens to `linear-gradient(135deg,
  var(--lv-ice), var(--lv-turq))`.
- Inputs/selects: `background: var(--lv-inset); border:1px solid var(--lv-hairline);
  border-radius:8px;` focus to `border-color: var(--lv-turq)`.
- Danger/stop: `background: rgba(255,77,77,0.14); border:1px solid rgba(255,77,77,0.40);
  color: var(--lv-red);`.
- Accent (amber) for secondary actions like Train: `rgba(255,179,64,0.16)` border +
  `color: var(--lv-amber)`.

## Bottom railing (LunaV Labs wordmark)
MARU explicitly asked for a "LunaV Labs" wordmark at the bottom. Pattern:

```html
<div class="railing">
  <span class="mark">L</span>
  <span><b>LunaV</b> <span class="turq">Labs</span></span>
</div>
```
```css
.railing { position: fixed; left:0; right:0; bottom:0; height:46px; z-index:20;
  display:flex; align-items:center; justify-content:center; gap:8px;
  background: rgba(20,23,28,0.92); backdrop-filter: blur(22px);
  -webkit-backdrop-filter: blur(22px); border-top:1px solid var(--lv-hairline);
  color: var(--lv-txt2); font-size:12px; }
.railing .mark { width:18px; height:18px; border-radius:5px;
  background: linear-gradient(135deg, var(--lv-turq), #1b6fd0);
  display:inline-flex; align-items:center; justify-content:center;
  color:#0e1116; font-weight:800; font-size:11px; }
.railing b { color: var(--lv-txt1); }  .railing .turq { color: var(--lv-turq); }
```
Add `body { padding-bottom: 46px; }` so the railing never covers controls.

## Verification (CSS-only change)
A CSS-only reskin cannot be visually verified without a browser (vision may be 404).
Probe instead: page serves HTTP 200; style braces balanced; railing markup +
`--lv-turq` + `backdrop-filter: blur(22px)` present; old dark hex gone from panel
roles; inline JS still `node --check`-clean. User eyeball is final sign-off.
