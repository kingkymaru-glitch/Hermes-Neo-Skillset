---
name: r-tessera-dev
description: R-Tessera CesiumJS globe. Build, link to LunaV, verify.
---

# R-Tessera — Dev Playbook

Ongoing product: **R-Tessera** = master CesiumJS globe holding geo-tagged
project nodes. It LINKS (does not embed) into **LunaV Studio** (the 3D
inspection workspace at lunavsolution.vercel.app). Treat them as two separate
deployments sharing one Supabase backend (LunaV's `okzmblyboudjffaixa`).

## Repo + deploy facts (STANDING)
- Repo: `~/Documents/R-Tessera`, GitHub `kingkymaru-glitch/R-Tessera`,
  Vercel `r-tessera.vercel.app`.
- **Version stamp — SHIPPED V0.3.0 (2026-10-20).** The earlier state (no version/build
  number anywhere in the served HTML, a real gap against the founder's standing
  version-stamp rule) is FIXED. `src/lib/version.js` exports `APP_VERSION = 'V0.3.0'`
  as the single source of truth; it is rendered in BOTH footers — the globe railing
  (`GlobeView.jsx`, after the Contact link) and the LunaV Labs railing
  (`LabsPage.jsx`, before `LUNAV LABS — ROVER-R`) — in gold `#C9A96E`,
  `letterSpacing: 0.18em`, with `title="R-Tessera build ${APP_VERSION}"`. Tag `V0.3.0`
  created and pushed.
  **Bump rule:** to release, change `APP_VERSION` in `src/lib/version.js` (never reuse a
  number — R-Tessera's own series runs v0.2.0-rebrand → V0.3.0 → …), bump `package.json`
  `version` to match, tag `V<that>`, commit as `maru <kingkymaru@gmail.com>`, push.
  **Verify the stamp is RENDERED, not just built:** the constant is hoisted into the
  entry chunk (`index-*.js`) while the globe footer lives in the lazy `GlobeView-*.js`
  chunk, which references the binding — so grepping the GlobeView chunk for the literal
  version returns 0. Grep the ENTRY chunk for the literal (that is the curl-checkable
  proof), and confirm in a browser that `.rt-railing` innerText contains the version on
  both `/` and `/?view=labs`.
- **Commit authorship is load-bearing:** Vercel auto-deploy only fires if the
  commit author is **`maru <kingkymaru@gmail.com>`**. Commit with
  `git -c user.name=maru -c user.email=kingkymaru@gmail.com`. (LunaV uses a
  DIFFERENT author — `MaruTheBlackCat <innovatedmaru@gmail.com>`. Don't mix them.)
- Stack: Vite + React (CJS-style `.jsx`), CesiumJS viewer, Leaflet-free.
  `npm run build` is the verify gate (Vite client build, ~290ms).
- **`package.json` scripts are clean as of V0.3.0:** only `dev` / `build` / `lint` /
  `preview`. The old `bridge`, `dev:all` and `start` entries referenced a `server/`
  directory that was deleted in the fresh-start rebuild and never restored — they were
  dead config and were removed. Do NOT re-add a `server/` script unless the file exists.
- Build with `npm run build`; verify green before pushing.

## Supabase access (NO local DB)
- The **anon** Supabase client is hardcoded in `src/lib/supabaseClient.js`
  (URL + anon key). The anon key is PUBLIC by design and was ROTATED once;
  if the globe stops showing nodes, the key may need re-sync with LunaV's
  `.env.local` anon key.
- `project_nodes` (LunaV's table, readable anon via `nodes_select_all` policy)
  carries the geo-pins: `lon`, `lat`, `visibility`, `lunav_project_id`,
  `lunav_share_token`.

## Public-node → LunaV link contract (CRITICAL)
R-Tessera shows project nodes with two buttons. Both must carry the token so
LunaV can resolve the viewer without a 404:

- **"View Homepage"** → LunaV Project Homepage (read-only for public):
  `${LUNO_URL}/project/${n.lunav_project_id}/home?share=${n.lunav_share_token}`
  (LUNO_URL = `https://lunavsolution.vercel.app`). For a PUBLIC node WITH a
  token only; otherwise fall back to `/login?project=...`.
- **"Go to Project"** → LunaV client share portal:
  `${LUNO_URL}/share/${n.lunav_share_token}` (public+token) else
  `/login?project=...`.

Symptom → cause: "clicked View Homepage, got 404" when logged out = the URL
lacked `?share=<token>`, so LunaV's `notFound()` fired (anon has no
`canEdit` and no share bundle). Always append the share token for public nodes.

### Node detail panel (node click) — CRITICAL UX RULE
Clicking a project node (on the globe OR a row in the left Projects list) must
open an **in-app detail panel**, NOT a new browser tab. Founder originally said
"open new tab" but meant an in-app panel showing the same Project Details as
LunaV STUDIO's Project Homepage — correct this interpretation by default for
this project.

- **Right-dock the panel** (`position: fixed; right: 14px; top: 70px`) so it
  NEVER overlaps the left-docked Projects list (`proj-drawer`, `top:70px
  left:0`). The original bug was the detail card using the same `left:14px
  top:70px` as the list → overlap. Rule: list = left, detail = right.
- **Data source = LunaV's shared Supabase via `get_shared_project` RPC** (anon,
  SECURITY DEFINER). R-Tessera's `project_nodes` only carries
  `name/description/lon/lat/visibility` — the rich "Project Details" table
  (Project name, Date, Coordinate, Client, Inspector + Additional notes from
  `extra_fields`) lives in LunaV's `project_sites.remarks` and is reachable
  ONLY through that RPC for anon. Add a `fetchProjectSite(lunavProjectId,
  shareToken)` helper to `src/services/useProjectNodes.js`:
  ```js
  const { data, error } = await supabase
    .rpc('get_shared_project', { share_token: shareToken || lunavProjectId })
  const site = data?.site ?? null
  ```
  Prefer the `lunav_share_token` (anon-readable); fall back to `lunav_project_id`.
- **Panel contents**: header (name + close), optional description, a "PROJECT
  DETAILS" section mirroring LunaV's `RemarksView` rows (name/date/coordinate/
  client/inspector + `extra_fields`), then the two action buttons (see link
  contract above) styled with `.proj-actions .mb-btn`.
- **Loading/error states**: show "Loading details…" while the RPC runs; if it
  errors, show the message. Private nodes without a token may return an empty
  `site` → rows render "—" (that's the DB's public-exposure boundary, not a bug).
- Keep `drawerOpen` state in App.jsx and PASS it as a prop to `ProjectNodes`;
  do NOT also declare `const [drawerOpen, setDrawerOpen] = useState(...)` inside
  `ProjectNodes` — that duplicate prop+state declaration is a PARSE_ERROR that
  the build will not catch via the `&&` chain (see vite-build-verification
  Pitfall 13).

## Chrome / theme (LunaV-Studio-matched, STANDING since 2026-08-12)
Founder standardized R-Tessera's chrome to MIRROR LunaV Studio's look, with the
product name swapped Studio→R-Tessera. Current architecture (do NOT revert to
the old top-left banner + bottom-center pill — that was replaced on purpose):

**Top header bar** (`<header className="rt-header">` in `src/App.jsx`):
- Brand block: `.rt-mark` (green "L" gradient square — `linear-gradient(135deg,#00e5c3,#00a884)` + turquoise glow, matches LunaV STUDIO's green mark) + "LunaV <span>R-TESSERA</span>".
- Left-aligned button group `.rt-header-btns`: `Projects` (toggles `showProjects`)
  and `Data Layers` (opens the MCP drawer). Both use `.rt-hdr-btn`.
- The external link is pinned FAR RIGHT via `className="rt-hdr-btn rt-hdr-link rt-push-right"`
  (`.rt-push-right { margin-left: auto; }`) and reads **"LunaV Studio"** (links to
  lunavsolution.vercel.app). NOTE: the text says "LunaV Studio" (not R-Tessera) by
  founder choice; the FOOTER carries the R-Tessera brand.

**Bottom railing** (`<footer className="rt-railing">`, full-width, LunaV-family style):
- `position: fixed; left: 0; right: 0; bottom: 0; z-index: 20;` height 46px,
  glass `blur(22px)`, `border-top`.
- Left: teal pulse dot + "LunaV R-Tessera — 3D Engine Online".
- Right: "LunaV R-Tessera - ROVER-R" (founder mandate 2026-08-12; this REPLACED
  the earlier "LUNAV R-TESSERA" uppercase form — use the hyphenated mixed-case
  string now).
- Classes: `.rt-railing-status`, `.rt-rail-dot` (teal `#00e5c3` glow), `.rt-railing-right`.
- This mirrors LunaV's workspace footer (teal dot + "LunaV Studio — 3D Engine Online"
  · "LUNAV STUDIO — ROVER-R"). Keep the SAME wording pattern when editing.

**Projects drawer tab must match the Map Control tab.** `.proj-drawer-tab` is
restyled to equal `.mcp-trigger` (the top-right glyph button): 42×42 square,
`border-radius: 11px`, same `rgba(12,17,28,0.72)` fill, same `rgba(120,160,220,0.18)`
border, same `#9fb3c8` text, same `blur(12px)` + drop shadow, same hover
(text→`#e2e8f0`, border→`rgba(34,211,238,0.4)`). Only diff: left corners squared
(`0 11px 11px 0`) so it reads as a left-dock tab. Tab content = the same
stacked-layers SVG glyph (no text label), matching the control panel icon.

### DEFAULT LANDING VIEW (founder mandate 2026-08-12)
On first load the globe must show the **3D globe draped in Esri satellite** — no
clicks. Set in `src/App.jsx`:
```js
const [raster, setRaster] = useState('satellite') // Esri World Imagery (baseLayers.js)
const [scene, setScene] = useState('3d')           // SCENE3D globe
```
Do NOT default to `map` (OSM) or `2d` — founder rejected the flat OSM default.

### PITFALL — bottom railing invisible above the Cesium globe
A static `<footer>` inside the flex column got CLIPPED (off-screen) because the
map container (`.app-shell` / Cesium viewer) ate the full height. Symptoms: build
passes, DOM has the footer, but nothing shows. **Fix that WORKED:** make the
railing `position: fixed; left:0; right:0; bottom:0` (z-index above the map). A
centered `left:50%; transform:translateX(-50%)` pill ALSO rendered but the
founder wanted the full-width LunaV-family bar, so prefer the full-width form.
- The bottom-LEFT `.base-selector` sits at `bottom:14px` and would be hidden under
  the 46px bar → lift it to `bottom:60px` whenever you add/keep the full-width rail.
- Keep the rail above the map (z-index 20); drawers are z-index 26–30 so they still
  open above it.

## Bathymetry / 3D seabed layer (NEW direction — founder goal)
Founder wants to PROVE 3D bathymetry can be built cheap and wire it under the
R-Tessera globe / LunaV Studio as a seabed terrain layer. Two paths, both feed
the same Cesium pipeline:

**Path A — public grid (zero cash, wide-area context):**
- Data: GEBCO_2024 grid (15 arc-sec, free) or ETOPO1 (NOAA, 1 arc-min, free).
- Convert GeoTIFF → Cesium quantized-mesh terrain tiles with
  cesium-terrain-builder / pyentive / terrainpipeline. Self-host (no paid
  Cesium ion). Load as a terrain layer under existing 3D tiles. Bathymetry =
  elevation with negative values; same pipeline, flipped sign.

**Path B — own USV capture (site-specific, DIY-provable):**
- Sensor: single-beam echosounder (SBES) is the cheap proof. Open Echo
  (github.com/neumi/open_echo) = fully open-source Arduino-compatible
  echosounder, transducer ~25€ (200kHz, >30m range). Pair with RTK-GNSS +
  small USV hull → real depth + position for near-zero cash.
- MBES (multibeam) is the industry standard (swath, real 3D carpet) but
  $10k–200k — that was the "expensive" blocker; Path B removes it.
- Full SBES theory, algorithm pipeline, sensor families, accuracy budget:
  see `references/bathymetry_sbes.md`.

**Common post-processing (both paths):**
USV: (depth+GPS) → XYZ point cloud → grid/TIN mesh → Cesium quantized-mesh
terrain → loads under LUNAV/R-Tessera 3D tiles. Public grid: GeoTIFF → tiles
direct. Output DEM uses negative elevations for underwater.

### PITFALL — clicking a header button resets the camera (CameraRig bug)
The `<Viewer>` is wrapped in a `CameraRig` component that runs
`viewer.camera.setView(INITIAL_CAMERA)` in `useEffect([viewer])`. resium's
`useCesium()` can hand `CameraRig` a *new* viewer-proxy object on every App
re-render — and clicking any header button (Projects / Data Layers / LunaV Studio)
changes App state → re-render → new proxy → effect re-fires → camera snaps back to
the opening zoom-out. Symptom founder reported: "I zoomed into a node, then clicked
a button and it zoomed out, forcing me to zoom back in." FIX: guard with a `didInit`
ref so `setView` runs EXACTLY ONCE:
```js
const didInit = useRef(false)
useEffect(() => {
  if (!viewer || didInit.current) return
  didInit.current = true
  viewer.camera.setView(INITIAL_CAMERA)
}, [viewer])
```

### PITFALL — node click → detail panel: immediate pick, never LEFT_DOUBLE_CLICK
Three iterations broke differently; the WORKING pattern is the third:
1. **Deferred `selectedEntity` (LEFT_CLICK):** Cesium only populates
   `viewer.selectedEntity` AFTER the first click, so the handler read a stale/null
   entity on click #1 and only opened on click #2. Symptom: "single click does
   nothing, second click navigates."
2. **`LEFT_DOUBLE_CLICK` (action 8):** did not fire reliably in resium's input
   pipeline here → "double-click does nothing, panel never opens."
3. **WORKING:** single-click via immediate `scene.pick(click.position)`. No
   dependency on Cesium selection. Resolve the entity id defensively:
   ```js
   const onClick = (click) => {
     if (!show || !click?.position) return
     const picked = viewer.scene.pick(click.position)
     const candidate = picked?.id?.id ?? picked?.id ?? picked?.primitive?.id
     let str = candidate
     if (typeof str !== 'string' && str?.id) str = str.id
     if (typeof str === 'string' && str.startsWith('node-')) { /* open panel */ }
   }
   handler.setInputAction(onClick, 1 /* LEFT_CLICK */)
   ```
4. **Globe lock:** Cesium's default double-click sets `viewer.trackedEntity`,
   pinning the camera to the node (navigation frozen, centered on it). Neutralize
   every frame so the camera still flies to the node but never locks:
   ```js
   const release = () => { if (viewer.trackedEntity) viewer.trackedEntity = undefined }
   viewer.scene.preRender.addEventListener(release)
   ```

### PITFALL — globe flickers/blinks on scroll or section change (Cesium camera-write collision + React re-mount)
Two distinct bugs, both hit on the LunaV Labs scroll-globe (and apply to ANY Cesium globe animated by scroll):
1. **Per-frame judder (flicker during scroll):** a hand-rolled `requestAnimationFrame` loop calling `camera.setView` every frame COLLIDES with Cesium's own render loop → judder. FIX: drive the spin from `viewer.clock.onTick.addEventListener(...)` (GPU-synced, single setView per tick). Keep `clock.shouldAnimate = true`.
2. **Blink on section change (re-mount):** if the globe component re-renders on every scroll event (because `setProgress` state fires 60×/s and the parent re-renders the `<Viewer>`), React tears down + rebuilds the WebGL canvas → flash. FIX: `React.memo()` the globe component, pass scroll progress via a **ref** (not a prop that changes every scroll), and throttle the scroll handler with rAF. The globe then mounts ONCE and never re-renders.
WORKING pattern (LunaV Labs `src/GlobeStage.jsx`):
```jsx
const GlobeStage = React.memo(function GlobeStage({ progressRef }) {
  const camRef = useRef({ lat:8, height:600000, heading:0, pitch:-55 })
  useEffect(() => {                       // load entities once
    const v = viewerRef.current?.cesiumElement; if (!v) return
    v.clock.shouldAnimate = true
    /* ...cables/quakes/pins... */
  }, [])
  useEffect(() => {                        // ONE steady tick: dolly-out lerp + spin
    const v = viewerRef.current?.cesiumElement; if (!v) return
    const SPIN = 0.025
    const remove = v.clock.onTick.addEventListener(() => {
      const c = camRef.current, p = progressRef.current || 0
      const ps = p*p*(3-2*p)               // smoothstep
      c.height = approach(c.height, 600000*Math.pow(2.4e6/600000, ps))
      c.pitch  = approach(c.pitch, -55 + ps*50)
      c.lat    = approach(c.lat, 8 - ps*6)
      c.heading = (c.heading + SPIN) % 360
      v.camera.setView({ destination: C3.fromDegrees(0,c.lat,c.height),
        orientation: { heading: CesiumMath.toRadians(c.heading), pitch: CesiumMath.toRadians(c.pitch), roll:0 } })
    })
    return () => remove()
  }, [progressRef])
  return <Viewer ref={viewerRef} className="globe-canvas" /* ... */ />
})
```
Verify no-flicker: in the browser, before/after scrolling to a later section the `.cesium-widget canvas` must be the SAME DOM node (`sameCanvasNode: true`); zero JS console errors.
CAVEAT: `Cesium`/`viewer` are NOT exposed on `window` in a Vite build, so you cannot read `viewer.camera` from the browser console — verify via the canvas-node-identity trick above, not by sampling camera heading.

### CHROME THEME — R-Tessera gold + Geist port (2026-08-13)
MARU adopted the LunaV Labs gold/ink look + Geist type onto R-Tessera's chrome. STANDING (local working tree, not yet deployed): the accepted design is GOLD (#C9A96E) chrome + Geist font, matching LunaV Studio. Founder confirmed full unity — even previously-distinct cyan signals are now gold.

Gold accent (#C9A96E) replaced cyan/blue across: brand mark (.rt-mark gold gradient linear-gradient(135deg,#C9A96E,#a8854f) — supersedes the earlier green #00e5c3 mark), header buttons (hover/active + LunaV link), railing dot/border, MCP title/switch/badge, base-btn & mcp-row active, project detail dot/section, primary buttons, link-pinpoint, labs hero gradient + field headings + nav hover, loading spinner, gold ambient radial washes. PLUS (this session): node markers + link pin (ProjectNodes.jsx NODE_COLOR, LinkPinpoint.jsx point) turquoise #00e5c3 → gold #C9A96E; .proj-row-tag.public pill cyan → gold; .mcp-foot code cyan → gold; Labs "visit" link blue #7db4ff → gold.

Intentional NON-gold (leave as-is): neutral structural borders rgba(120,160,220,..)/rgba(150,175,205,..) = chrome outlines, not accents; .labs-badge.beta (blue)/.labs-badge.rnd (amber) = status colors in the Labs badge system (live=gold, beta=blue, rnd=amber).

Font — Geist (matches LunaV Studio, which uses var(--font-geist-sans/mono) via Next.js):
- Installed @fontsource/geist-sans + @fontsource/geist-mono (self-hosted, Vite-friendly, offline-safe — no Google fetch).
- src/index.css: @import Geist Sans 400/500/600/700 + Mono 400/500; defines --rt-font-sans/--rt-font-mono; body { font-family: var(--rt-font-sans); -webkit-font-smoothing: antialiased; }.
- App.css uses font-family: inherit everywhere → whole UI picks up Geist.
- Cesium on-globe labels (lat/lon readouts) in ProjectNodes.jsx/WeatherEntities.jsx/SituationalEntities.jsx use 'Geist Mono': font="600 12px 'Geist Mono', ui-monospace, monospace" (single quotes inside the double-quoted JSX attr — do NOT use &quot;, that renders literal entities; font: '600 12px "Geist Mono", …' in plain-JS label objects is fine).
- Verify (local-only, no deploy): npm run build emits geist-*-*.woff2 into dist/assets; dev server serves the @font-face rules and the woff2 returns HTTP 200 (e.g. curl -s -o /dev/null -w "%{http_code}" http://localhost:5174/node_modules/@fontsource/geist-sans/500.css).
- Founder chose "full family unity" (Option A): apply Geist to R-Tessera, leave LunaV Studio's font setup untouched.

(R-Tessera main had a pre-existing mount failure from the unfinished GlobeView.jsx code-split + missing VITE_GOOGLE_MAPS_API_KEY — unrelated to the CSS; revert to a good commit before expecting the app to boot.)
deployed). Applied in `src/App.css`: cyan/blue accents (#00e5c3/#7dd3fc/#2f9bff) → gold
#C9A96E across brand mark, header buttons (hover/active + LunaV link), railing dot/border,
MCP title/switch/badge, base-btn & mcp-row active states, project detail dot/section, primary
buttons (.mb-btn-primary, link-pinpoint), labs hero gradient + field headings + nav hover,
loading spinner, and warm gold ambient radial washes on header/railing/labs-root. Left
intentional: `.proj-row-tag.public` status pill (cyan = "public" semantic) and inline-code
tint. This is a CSS-only port; it does NOT affect JS. (R-Tessera `main` had a pre-existing
mount failure from the unfinished GlobeView.jsx code-split + missing VITE_GOOGLE_MAPS_API_KEY —
unrelated to the CSS; revert to a good commit before expecting the app to boot.)

## Adding in-app pages / views (NO router)
R-Tessera is a single-globe SPA with **no react-router**. Every "new page / new
screen" is done with an App-level `view` state + a `?view=` query param for
deep-linking. The LunaV Labs showcase (added 2026-08-12) is the reference impl.

**Canonical pattern (use this for any new view):**
```jsx
// in App.jsx
const initialView = useMemo(() => {
  const p = new URLSearchParams(window.location.search)
  if (p.get('link') === '1') return 'globe'          // never override handoff mode
  return p.get('view') === 'labs' ? 'labs' : 'globe'
}, [])
const [view, setView] = useState(initialView)

// globe chrome + Labs page are mutually exclusive — wrap the WHOLE globe tree
// (header, <Viewer>, box1/box2, footer) in ONE fragment so the second view
// never double-renders the globe header:
return (
  <div className="app-shell">
    {view === 'globe' && (<>
      <header className="rt-header">…</header>
      <ErrorBoundary><Viewer>…</Viewer></ErrorBoundary>
      <BaseLayerSelector … />
      <MapControlPanel … />
      <footer className="rt-railing">…</footer>
    </>)}
    {view === 'labs' && <LabsPage onClose={() => { /* clear ?view, setView('globe') */ }} />}
  </div>
)
```
To OPEN a view from a header button, also push `?view=labs` via
`window.history.replaceState` so the URL is shareable/refresh-safe.

### PITFALL — multiple siblings under `&& (…)` break the build
`{cond && ( <A/> <B/> )}` is a JSX SYNTAX ERROR ("JSX expressions must have one
parent element" / "Unexpected token"). Every `&& (…)` block MUST wrap its
children in a single element or a fragment `<>…</>`. Hit this twice while adding
Labs: first the globe block, then the view fragment. Always wrap multi-element
conditional blocks in `<>…</>`. (This is the same class as Pitfall 13 — the `&&`
chain masks the error until `npm run build`.)

### PITFALL — duplicate header when adding a second view
The globe `<header>` is NOT inside any conditional by default. If you add a Labs
(or any) page but only wrap the `<Viewer>` in `view==='globe'`, BOTH the globe
header AND the Labs header render stacked (Labs Page is fixed `z-index:45` over
the globe, so you see a double banner). **Fix:** put the globe `<header>` INSIDE
the `{view==='globe' && (<> … </>)}` fragment alongside the viewer. One header
per view.

### LunaV Labs showcase — data-driven pattern (reusable)
The Labs page proves a clean, editable showcase: a single data file
`src/labs/projects.js` exports `labsProjects` (array of
`{name, status:'LIVE'|'BETA'|'R&D', liveUrl?, function, advantage, technology,
images?}`). `src/labs/LabsPage.jsx` renders each project as its OWN full-width
section, stacked vertically; users scroll (or use the floating nav) to walk
through them in order. Add/rename/reorder projects by editing ONLY the data
file — no JSX surgery.

**Layout (current, 2026-08-12):** one section per project = header (name +
status badge + optional "Visit live ↗") above a two-column body:
- LEFT column: `.labs-images` = 3 stacked `.labs-img` slots (top→bottom),
  each `aspect-ratio:16/9`. Fill via `images: ['/labs/a.png','/labs/b.png',
  '/labs/c.png']` (paths resolve from R-Tessera `/public`, so drop files in
  `public/labs/`). Missing slot → `.labs-img-empty` "Image N coming soon".
- RIGHT column: `.labs-prose` = Function / Advantage / Technology paragraphs.
- A floating `.labs-nav` (fixed, right-center) shows ↑ (prev) / `N/total`
  counter / ↓ (next); buttons disable at the ends; smooth-scrolls to the target
  section.

**Founder naming convention (public roadmap):** every showcase entry uses the
`LunaV ***` prefix — LunaV Studio / **LunaV R-Tessera** (NOT "LunaV Tessera" —
MARU explicitly wanted the R- kept) / LunaV Scan / LunaV Edge / LunaV Sonar.
The deployed app name stays "R-Tessera"; only the public-facing label on the
Labs page is re-prefixed. Apply this prefix to any future public roadmap card.
The Dam Demo is intentionally EXCLUDED from the public listing.

### Editing Labs copy + verifying it is LIVE (2026-08-13 workflow)
MARU frequently asks to rewrite card blurbs. The `function` field is the
description under each card's "Function" heading (the other two fields are
`advantage` and `technology`). **"LunaV Labs" is NOT a separate domain** — it is
the in-app `?view=labs` page inside R-Tessera, so a Labs copy edit deploys by
pushing the R-Tessera repo (there is no separate lunavlabs.vercel.app yet).
Steps that end in PROOF, not assumption:
1. Edit the blurb in `src/labs/projects.js` only — no JSX surgery needed
   (LabsPage.jsx maps over the array).
2. `npm run build` green, then commit as `maru <kingkymaru@gmail.com>` and
   push `origin main` (Vercel webhook requires that author).
3. **Do NOT trust the build or the push.** Vercel rolls a NEW hashed bundle
   (`dist/assets/index-<hash>.js`) ~30–60s after push, and the served HTML only
   references the hash — the copy string is NOT in the HTML. Verify end-to-end:
   ```bash
   # poll until the live HTML references a NEW bundle hash (old one = deploy not rolled yet)
   for i in $(seq 1 6); do
     sleep 10
     H=$(curl -s https://r-tessera.vercel.app | grep -oE 'index-[A-Za-z0-9_-]+\.js' | head -1)
     echo "try $i: $H"; [ "$H" != "<old-hash>" ] && break
   done
   # then grep the LIVE bundle for the exact new strings — only this proves it shipped
   curl -s "https://r-tessera.vercel.app/assets/$H" -o /tmp/live.js
   grep -c "orbital command lattice" /tmp/live.js   # -> 1 = live
   ```
   `grep -c` returning `1` per string is the confirmation; a `0` means the
   deploy is stale (re-poll) or the edit never built.
4. If MARU's pasted copy is truncated mid-sentence, apply exactly what was given
   and FLAG the gap (don't silently invent an ending — but do offer a sensible
   completion he can approve). Minor copy fixes he routinely OKs without asking:
   drop a stray space before a comma (`"Kit , AI"` → `"Kit, AI"`).

### PITFALL — Cesium `Viewer.destroy()` crash on globe↔Labs swap (`t.remove is not a function`)
Clicking "LunaV Labs" from the globe header can blank the page with
`TypeError: t.remove is not a function` at `GlobeView-*.js`. Root cause: Cesium's
`Viewer.destroy()` (which calls `.remove()` on entity collections child
components already tore down) runs in the SAME React commit as Labs mounting →
the teardown races the mount. Full diagnosis + the lagged-unmount fix (keep a
`globeAlive` flag true for one macrotask, then `setGlobeAlive(false)` in
`setTimeout(…,0)` so Cesium.destroy() runs alone) →
`references/lunav_labs_standalone.md` §3. That file also covers why the globe was
slow before the `React.lazy` code-split (main chunk 531 kB → 228 kB) and the
prop-plumbing `ReferenceError` gotcha when extracting `GlobeView.jsx`.

### DIRECTIONAL — LunaV Labs wants to be its OWN clean page, not a `view` under R-Tessera
MARU (2026-08-12) leaned toward making LunaV Labs a **standalone landing page**
on Vercel instead of an in-tree `?view=labs` sub-view. A standalone page removes
the Cesium unmount-crash class entirely (separate entry points = no shared
lifecycle), is instant/zero-Cesium, and is more demo-presentable. Options: (A)
separate route in the same R-Tessera Vercel project (`/labs`), or (B) fully
separate deploy/subdomain (`lunavlabs.vercel.app`). The in-tree `view`-based Labs
still builds + renders in the meantime. When building the standalone page, LIFT
the existing `src/labs/LabsPage.jsx` + `src/labs/projects.js` (data-driven).
Pending specifics → `references/lunav_labs_standalone.md` §4.

### PITFALL — scroll-spy counter + nav scroll break (IntersectionObserver + id/data-idx mismatch)
The floating `.labs-nav` (↑/↓ + `N/total` counter) is driven by:
- an `IntersectionObserver` watching `.labs-project` sections (threshold 0.5)
  that reads `data-idx` off the observed element to set the active index, and
- a `scrollTo(idx)` that does `mainRef.querySelector('#labs-proj-'+idx)` then
  `scrollIntoView({behavior:'smooth'})`.
BUG (hit 2026-08-12): the map rendered
`{labsProjects.map((p,i)=>(<div data-idx={i} key={p.name}><ProjectSection…/></div>))}`
— so `data-idx` and the `id` were on the WRAPPER `<div>`, but the observer
watched `.labs-project` (inside the wrapper). Result: `data-idx` read as null →
active index never updated → counter stuck at "1/5" and ↑ disabled forever.
**FIX:** put BOTH `id={`labs-proj-${index}`}` AND `data-idx={index}` directly on
the `<section className="labs-project">` (drop the wrapper `<div>` entirely):
```jsx
function ProjectSection({ project, index }) {
  return (
    <section className="labs-project" id={`labs-proj-${index}`} data-idx={index}>
      {/* head + body */}
    </section>
  )
}
// map:
{labsProjects.map((p, i) => <ProjectSection project={p} index={i} />)}
```
RULE: the attribute the observer/scroll-target reads MUST live on the exact
element matched by the querySelector — never a parent wrapper. Verify by
clicking ↓ in the browser and reading `.labs-nav-count`: it must advance
(e.g. "1/5"→"2/5") and `main.scrollTop` must increase.

## CCTV camera layer (ROVER-KIT / Luna EDGE, added 2026-08-25)
Pattern for drawing live camera nodes on the globe from the `cctv_cameras`
table (Supabase anon SELECT, no seeding). Reference impl:
`src/components/CctvCameraLayer.jsx` + `src/services/useCctvCameras.js`
(hook returns `{ data, error }` from `supabase.from('cctv_cameras').select('*')`).

**Mount + toggle plumbing (mirror ProjectNodes exactly):**
- `App.jsx`: `const [showCctv, setShowCctv] = useState(false)`; pass
  `showCctv` + a `cctvCount` (derived from the hook) into `GlobeView`, and
  `showCctv` + `setShowCctv` into `MapControlPanel` (the toggle checkbox).
- `GlobeView.jsx`: DESTRUCTURE `showCctv`/`setShowCctv`/`cctvCount` from props
  in the function signature — a missing destructure throws
  `ReferenceError: Can't find variable: showCctv` at map init and blanks the globe.
- In `GlobeView`, do the hook call (`const q = useCctvCameras()`) ABOVE any
  `return`, then render `<CctvCameraLayer show={showCctv} query={q} viewer={viewer} />`
  unconditionally (the layer internally no-ops when `show` is false). Mixing a
  `&&` guard with an unconditional render double-mounts and double-adds entities.
- `MapControlPanel`: checkbox `checked={showCctv}` `onChange={e=>setShowCctv(e.target.checked)}`,
  label `ROVER-KIT · CCTV Cameras` + count badge. Keep checkbox in the DOM even
  when `cctvCount===0` so the user can toggle the layer on before a camera exists.

**Layer internals that WORKED (and the bug that hid the node):**
- Acquire the viewer via `useCesium()` (`const { viewer } = useCesium()`), same
  as `ProjectNodes`. `viewer` may be momentarily null on first render — guard
  `if (!viewer) return`.
- Click-to-open: `new ScreenSpaceEventHandler(viewer.scene.canvas)` +
  `setInputAction((c)=>{ const p = viewer.scene.pick(c.position); const id =
  p?.id?.id ?? p?.id; if (typeof id === 'string' && id.startsWith('cam-')) open(id) }, 1)`.
  Resolve the entity id defensively (see ProjectNodes pitfall — never rely on
  `selectedEntity`).
- **PITFALL — node invisible off-screen + translucency fade:** a single 11px dot
  at real-world coords renders but you WON'T see it if the globe is centered
  elsewhere (no auto-fly) — MapControlPanel showing "CCTV Cameras 1" with no
  visible node is the classic symptom, not a data bug. FIX: (a) bump marker to
  ~14px and DROP `translucencyByDistance` (it fades the dot to alpha 0 when
  zoomed out, so the node vanishes), (b) on `show` flipping true, `viewer.flyTo`
  / `viewer.camera.flyTo` to the camera's `Cartesian3.fromDegrees(lon,lat,0)`
  (~9 km altitude) so the node is guaranteed in view. Pattern:
  ```js
  useEffect(() => {
    if (!show || !viewer || !query.data?.length) return
    const c = query.data[0]
    viewer.camera.flyTo({ destination: C3.fromDegrees(c.lon, c.lat, 9000) })
  }, [show, viewer, query.data])
  ```
- **Floating webcam window:** the node-click opens a draggable `<div>` that
  opens an `Image()` (or WebSocket) to `camera.stream_url`. For `ws://` localhost
  dev URLs, mixed-content blocks `ws://` from an `https://` Vercel page — store a
  `wss://` tunnel URL (e.g. cloudflared) for live, `ws://localhost:8000/ws` for
  local. Verify with a real Luna EDGE stream (Python `app.py` serving a raw
  binary JPEG WebSocket on `0.0.0.0:8000/ws`).
  - **PITFALL — floating window renders BELOW the globe (z-index trap):** a plain
    `<div>` mounted inside the Cesium React tree is subject to the Cesium
    container's CSS `transform`/`will-change`, which creates a new stacking
    context that traps the window under the map even with high z-index. Symptom:
    click opens the node but the video window is invisible / hidden behind the
    globe. **FIX that WORKED:** render the window with `ReactDOM.createPortal(
    <FeedWindow/>, document.body)` so it escapes the Cesium stacking context. Keep
    the drag handlers in the portaled component; nothing else changes.
  - **PITFALL — `ScreenSpaceEventHandler.LEFT_CLICK` is UNDEFINED → "Map failed to
    initialize" (DeveloperError in `setInputAction`):** the click registration
    `handler.setInputAction(fn, ScreenSpaceEventHandler.LEFT_CLICK)` throws because
    `LEFT_CLICK` lives on `ScreenSpaceEventType`, NOT `ScreenSpaceEventHandler`.
    This hard-crashes globe mount (ErrorBoundary "Map failed to initialize").
    FIX: `import { ScreenSpaceEventHandler, ScreenSpaceEventType } from 'resium'` and
    register with `handler.setInputAction(fn, ScreenSpaceEventType.LEFT_CLICK)`.
    (The integer `1` also works but `ScreenSpaceEventType.LEFT_CLICK` is the safe,
    readable form — never `ScreenSpaceEventHandler.LEFT_CLICK`.)
  - **PITFALL — `viewer.scene.preRender.addEventListener(release)` returns a
    REMOVER FUNCTION, not `{remove()}` (unmount crash):** both `ProjectNodes.jsx`
    and `CctvCameraLayer.jsx` neutralize `viewer.trackedEntity` per-frame via
    `const handle = viewer.scene.preRender.addEventListener(release)`. The returned
    value is a **function you call to unsubscribe** — NOT an object with `.remove()`.
    Symptom: `TypeError: handle.remove is not a function at ProjectNodes.jsx:160`
    kills the whole app via ErrorBoundary on unmount. **FIX (useEffect cleanup):**
    ```js
    useEffect(() => {
      if (!viewer) return
      const release = () => { if (viewer.trackedEntity) viewer.trackedEntity = undefined }
      const handle = viewer.scene.preRender.addEventListener(release)
      return () => {
        if (typeof handle === 'function') handle()           // Cesium remover
        else if (handle && typeof handle.removeCallback === 'function') handle.removeCallback()
      }
    }, [viewer])
    ```
  - **Mixed-content fix recipe (live):** to show a localhost `ws://` Luna EDGE feed
    on the deployed `https://r-tessera.vercel.app`, wrap it in a free Cloudflare
    quick tunnel → `wss://`. See `references/cloudflared_wss_tunnel.md` for the
    exact commands, the SQL to point `cctv_cameras.stream_url` at the `wss` URL, and
    the Python `websockets` probe that proves the tunnel reaches Luna EDGE end-to-end.
    Caveat: quick-tunnel URLs ROTATE on every `cloudflared` restart → re-run the SQL
    with the new URL. For a stable URL use a named tunnel (free Cloudflare account +
    `cloudflared tunnel login` to drop `cert.pem`). Kill the tunnel when the demo's
    done — it exposes the webcam to anyone with the URL.

**Verify:** build green → deploy → toggle "CCTV Cameras" ON → globe flies to the
node → red marker visible → click → floating window paints the stream. If the
MapControlPanel count shows N but the map is empty, it is the off-screen/fade
bug above, not a data problem. When grepping the LIVE bundle to prove the CCTV
code shipped, note `GlobeView` is `React.lazy`-split into
`dist/assets/GlobeView-<hash>.js` — the "CCTV Cameras" string / `rt-feed-window`
class / `stream_url` live in THAT chunk, not the entry `index-*.js`.

## Verify after edits
- `npm run build` green (Vite client build).
- Hard-refresh r-tessera.vercel.app; confirm banners render and globe still drags.
- Zoom into a node, then click Projects / Data Layers → camera must STAY where you
  left it (no reset). This is the CameraRig regression check.
- Single-click a node (globe or list row) → detail panel opens immediately; the
  globe does NOT lock/center on the node (you can still drag away).

### View-switch verify (Labs-style pages)
MARU's standing rule: "done" = visibly on screen, not just build-green. For any
new view, don't stop at `npm run build`. Run `npm run preview -- --port <n>` and
use the browser tool to navigate to `http://localhost:<n>/?view=labs`, then take
a snapshot and confirm:
- exactly ONE header (no double globe+Labs banner),
- every card/section renders with real text (not blank),
- clicking the view's "Back" returns to a live `<Canvas>` globe + controls.
This caught the duplicate-header bug that `npm run build` could not.
