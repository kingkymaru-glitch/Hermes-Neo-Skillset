# LunaV Theme Sync — token crosswalk & header reference

## Token name crosswalk (CRITICAL: same color, different names per repo)

| Concept            | LunaV (Next, globals.css)        | LunaV EDGE (templates/index.html) | R-Tessera (App.css, inline)        |
|--------------------|----------------------------------|-----------------------------------|------------------------------------|
| Accent turquoise   | `--mb-turquoise` (#0a84ff / dark #2f9bff) | `--lv-turq` (#2f9bff)         | `#2f9bff` (hardcoded, no var)      |
| Accent glow        | `--glow-turquoise`               | `--lv-glow`                       | `0 0 18px rgba(47,155,255,0.35)` (hardcoded) |
| Hairline border    | `--hairline`                     | `--lv-hairline`                   | `rgba(150,175,205,0.14)`           |
| Primary text       | `--txt-primary`                  | `--lv-txt1`                       | `#e8eef4`                          |
| Secondary text     | `--txt-secondary`                | `--lv-txt2`                       | `#8fa1b3`                          |
| Glass surface      | `--glass`                        | `rgba(27,31,38,0.82)` (panel)     | `rgba(20,23,28,0.82)` (header)     |
| Void / bg          | `--dash-void`                    | `--lv-void` (#14171c)             | `#05070d` (error bg)               |

Porting rule: `--mb-turquoise` → `#2f9bff`, `--hairline` → `rgba(150,175,205,0.14)`,
`--txt-primary` → `#e8eef4`, `--txt-secondary` → `#8fa1b3`.

## Header implementations (side by side)

### LunaV — ProjectWorkspace.tsx (reference)
```tsx
<nav className="z-30 flex h-auto min-h-16 flex-wrap items-center justify-between gap-y-2 border-b px-4 py-2 ..."
     style={{ borderColor: "var(--hairline)", background: "var(--glass)", backdropFilter: "blur(22px)" }}>
  <div className="flex items-center gap-3">
    <img src="/logo.png" className="h-9 w-9 object-contain" />
    <div>
      <div className="text-sm font-bold tracking-widest uppercase" style={{color:"var(--txt-primary)"}}>
        {branding.companyName || "LunaV Studio"}
      </div>
      <div className="... truncate text-[0.65rem] font-semibold tracking-wider" style={{color:"var(--mb-turquoise)"}}>
        {initial.projectName}
      </div>
    </div>
    <button className="mb-btn" ...>← Back</button>
    <button className="mb-btn" ...>Home</button>
    <button className="mb-btn" ...>Project Home</button>
  </div>
  <div className="flex gap-2 overflow-x-auto">
    {["3d","report","analytics","docs"].map(([t,label]) => (
      <button key={t} className={`mb-btn ${tab===t?"mb-btn-primary":""}`}>{label}</button>
    ))}
  </div>
  <div className="flex items-center gap-3">
    <button className={`mb-btn ${settingsOpen?"mb-btn-primary":""}`} ...>Settings</button>
  </div>
</nav>
```
Buttons (.mb-btn) in globals.css:
```css
.mb-btn { display:inline-flex; align-items:center; justify-content:center; gap:8px;
  padding:10px 18px; border-radius:10px; font-size:0.78rem; font-weight:600; letter-spacing:0.06em;
  border:1px solid var(--hairline);
  background:linear-gradient(180deg, rgba(255,255,255,0.05), rgba(255,255,255,0.01));
  color:var(--txt-secondary); cursor:pointer; transition:all .18s cubic-bezier(.2,.8,.3,1); }
.mb-btn:hover { color:var(--txt-primary); border-color:var(--hairline-strong); transform:translateY(-1px); }
.mb-btn-primary { border-color:rgba(0,229,195,0.45);
  background:linear-gradient(180deg, rgba(0,229,195,0.16), rgba(0,229,195,0.06)); color:var(--mb-turquoise); }
.mb-btn-primary:hover { box-shadow:var(--glow-turquoise); color:var(--mb-turquoise); }
```

### R-Tessera — App.jsx (synced)
```jsx
<header className="rt-header">
  <div className="rt-brand">
    <span className="rt-mark">L</span>
    <div className="rt-name"><b>LunaV</b> <span>R-TESSERA</span></div>
  </div>
  <div className="rt-spacer" />
  <div className="rt-header-btns">
    <button className={`rt-hdr-btn ${showProjects?"is-active":""}`} onClick={()=>setShowProjects(v=>!v)}>Projects</button>
    <button className={`rt-hdr-btn ${anyLayer?"is-active":""}`} onClick={()=>setMcpOpen(v=>!v)}>Data Layers</button>
    <a className="rt-hdr-btn rt-hdr-link" href="https://lunavsolution.vercel.app" target="_blank" rel="noopener noreferrer">LunaV Studio</a>
  </div>
</header>
```
CSS (.rt-header / .rt-hdr-btn) in App.css — mirrors LunaV .mb-btn with hardcoded hex:
glass `rgba(20,23,28,0.82)` + `blur(22px)`; brand mark gradient `#2f9bff→#1b6fd0`;
idle text `#8fa1b3`; active tint `rgba(0,229,195,...)`; link tint `rgba(47,155,255,...)`.
Header z-index 35 (above Cesium chrome ~8).

### LunaV EDGE — templates/index.html (synced)
```html
<header>
  <div class="brand">
    <span class="mark">L</span>
    <div class="name"><b>LunaV</b> <span>EDGE</span><span class="tag">: OFFLINE DETECTION</span></div>
  </div>
  <button id="learnBtn" class="hdr-btn">AI Learning</button>
  <button id="aiDetBtn" class="hdr-btn active" style="display:none">AI Detection</button>
  <div class="spacer"></div>
  <div class="status s-idle" id="statusPill">...</div>
</header>
```
Header CSS uses `--lv-*` tokens (mirror of LunaV Studio globals.css). `.hdr-btn` class MUST
override the global `button { margin-top:12px }` with `margin-top:0; box-shadow:none`.

## Brand wordmark rule (EDGE-style)
- "LunaV" = primary color, normal weight-ish; PROJECT NAME = caps + accent color.
- R-Tessera: `R-TESSERA` (#2f9bff). LunaV EDGE: `EDGE`. LunaV self: `STUDIO` (turquoise).
- White-label (LunaV `branding.companyName` set) overrides all of the above with the client name.

## Fixed-header offset audit (after adding a fixed top bar)
Re-check every `position: fixed` element's `top`:
- R-Tessera `.mcp-trigger`: `top:14px` → `top:70px`
- R-Tessera `.mcp-drawer`: `top:64px` → `top:120px`
- LunaV EDGE launcher pill already at `top:72px` (below 56px bar) — correct.
