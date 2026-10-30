# Extract a sub-view into a standalone LunaV landing page (Option B)

Verified recipe from the 2026-08-12 session: LunaV Labs as a `?view=labs` toggle inside
R-Tessera → promoted to its own private repo `github.com/kingkymaru-glitch/lunav-labs`,
own Vercel project, zero Cesium.

## Why extract instead of toggle
- Cesium globe + non-globe view toggled by React state → `viewer.destroy()` runs in the
  same commit as the new view's mount → `TypeError: t.remove is not a function` → blank page.
  Separate repo/page eliminates the race (globe tears down before the page mounts).
- Standalone bundle ~198 kB (63 kB gzip), ZERO Cesium, vs 228 kB + 306 kB in-tree.
- "Open Labs" becomes `<a href>` not a state switch — no WebGL-unmount hazard.

## File tree produced (minimal Vite + React 19, no Cesium)
```
lunav-labs/
├── package.json        # only react, react-dom, @vitejs/plugin-react, vite
├── vite.config.js      # plugins: [react()]  — NO cesium()
├── index.html          # <div id="root"> + /src/main.jsx
├── .gitignore          # node_modules, dist
├── README.md
├── public/favicon.svg  # inline LunaV "L" mark
└── src/
    ├── main.jsx        # createRoot(...).render(<App/>)
    ├── App.jsx         # just returns <LabsPage />
    ├── index.css       # minimal reset (the globe repo had this import)
    ├── App.css         # copied .rt-header/.rt-brand/.rt-railing + .labs-* rules
    └── labs/
        ├── LabsPage.jsx   # lifted verbatim; onClose → <a href> to globe
        └── projects.js    # lifted verbatim — single source of truth for cards
```

## Lift rules (what to copy, what to drop)
- `LabsPage.jsx` / `projects.js`: copy verbatim. They only import `react` + each other.
- CSS: copy the *base* shared classes the page actually uses (`.rt-header`, `.rt-brand`,
  `.rt-mark`, `.rt-name`, `.rt-spacer`, `.rt-push-right`, `.rt-hdr-btn`, `.rt-railing*`)
  + the page `.labs-*` block. Drop `.rt-globe-loading` and anything Cesium-only.
- `main.jsx` imports `./index.css` — if you don't copy it, the build fails with
  `[UNRESOLVED_IMPORT] Could not resolve './index.css'`. Add a minimal reset.
- Replace the Labs "Back" button (was `onClick={onClose}`) with a real link:
  `<a className="rt-hdr-btn rt-push-right" href="https://r-tessera.vercel.app">← LunaV R-Tessera</a>`.

## Build / verify
```
cd ~/lunav-labs && npm install && npm run build
# expect: index-*.js ~198 kB (63 kB gzip), no GlobeView/Cesium chunk
```
Verify in browser (port 4191 preview): header + hero + 5 cards + floating nav; click ↓ →
counter advances 1/5 → 2/5 AND `main.scrollTop` > 0. (Scroll-spy + nav must work — see
`vite-build-verification` Pitfall 15: put `data-idx`/`id` on the observed `.labs-project`.)

## Push (gh does NOT auto-add origin)
```
git init -q
git add -A
git -c user.name=maru -c user.email=kingkymaru@gmail.com commit -q -m "..."
gh repo create lunav-labs --private --description "..."
git remote add origin https://github.com/kingkymaru-glitch/lunav-labs.git
git push -u origin main
```
## Deploy
Vercel dashboard → Add New → Project → import `lunav-labs` → Vite preset, no env vars.
`vercel` CLI may be absent locally; dashboard path needs none.
