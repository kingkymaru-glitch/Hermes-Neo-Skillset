# LunaV design mocks — look & feel exploration before any repo change

Use when the founder asks to "improve the look and feel", "make it look more professional",
"kill the AI-generated feel", or wants to see a direction before anything is built. Build
throwaway standalone HTML in a scratch dir and serve it locally. NEVER edit the repo for a
design exploration — no branch, no commit, no push.

## The founder's design bar (state it back to him)

Professional, sleek, futuristic — the reference he gives is **Iron Man's Jarvis HUD** and
**game-developer UI** (the effort that goes into a game's menus), explicitly **without
overdoing it**. His standing complaint about the current build: *"I know this is so AI
generated."* The goal is to make that reading impossible.

## What kills the "AI-generated" reading

- **Real density.** Actual numbers with units, IDs, revisions, timestamps. Placeholder rows
  and lorem ipsum are the tell.
- **One accent, used for STATE.** Colour means something. The current build glows blue on
  everything — that is itself the tell.
- **Corner brackets and chamfers, not rounded glass cards.** Precision geometry over soft
  blobs. (`clip-path` chamfer, or 9px corner brackets via `::before`/`::after`.)
- **Two type voices.** Monospace for data/readouts/labels, a tight grotesk for words. Not
  one family everywhere.
- **Hierarchy with weight.** Not everything at the same size and emphasis.
- **Hairlines + one accent.** `rgba(148,180,220,.10)`-style borders, no heavy shadows.

## The stance axis (pick 2-3 that genuinely differ)

Variants must differ in STANCE, not pixels. The axis that worked for the 3D twin:

| Stance | Chrome | Data density | The 3D is | Feels like |
|---|---|---|---|---|
| HUD Overlay / instrument | ~15% overlay | medium | the screen | flight instrument |
| Dual Console / engineering tool | ~45%, 3 columns | high | the middle column | CAD / asset tool |
| Cinematic Stage / showroom | ~8%, near-zero | low (4 numbers) | the whole point | product configurator |

Opinionate in the head-to-head: name which is strongest and which is weakest, and why.

## 3D scene conventions (Three.js)

- **Wireframe edges are UNLIT.** `LineBasicMaterial` / `EdgesGeometry` ignore scene lighting
  entirely. An exposure/brightness control that only changes light intensities will barely
  move a wireframe model — drive the edge and shell COLOURS as well as the lights. Verify by
  reading the material state back over JS, not by eye.
- **Give a mock scene real lights** (`AmbientLight` + key `DirectionalLight` + a cool rim)
  and `MeshStandardMaterial` shells, not `MeshBasicMaterial` — unlit wireframe reads flat and
  dead.
- **One `applyLook()` for exposure + highlight**, with named base/low/high colours per
  material, so the slider and the "highlight all" toggle cannot drift apart.
- **De-collide DOM labels projected from 3D.** Project all pin positions first, sort by screen
  Y, then push each label down if it would overlap the previous one. Otherwise callouts stack
  on each other and the mock reads sloppy.

## Verify a visual change correctly

A/B the two extremes and compare the images; never a single frame, and never a whole-image
brightness statistic. The general rule — and why percentiles lie on a UI frame — lives in the
`sketch` skill. Read that before claiming a visual change works.

## Where these live

Scratch dir outside the repo (e.g. `~/lunav-design/`), served over localhost
(`python3 -m http.server <port> --bind 127.0.0.1`). See the `desktop-preview` skill for the
TCC / `file://` pitfalls — `~/Desktop` is not readable by the agent browser.
