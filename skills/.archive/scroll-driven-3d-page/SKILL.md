---
name: scroll-driven-3d-page
description: Use when building a scroll-driven 3D web page.
---

# Scroll-driven 3D page (single file, Three.js)

A landing page where one 3D object sits in a pinned stage and *scroll position*
drives its animation — assemble/explode, reveal, label, resolve to a CTA. One
self-contained HTML file, openable by double-click.

## FIRST: agree the deliverable SHAPE before writing any code

An "interactive viewer" and a "scroll story" are DIFFERENT PRODUCTS, and this is
the single most expensive mistake in this class of task:

- **Interactive viewer** — orbit controls, a slider to explode, a component/tree
  panel, hover-to-inspect, double-click-to-isolate. This is an *engineering review
  tool*. It has no "scroll down".
- **Scroll story** — a pinned stage, copy scrolling past it, and scroll progress
  driving the animation through narrative beats.

If the user asked for a scroll story and the artifact is a viewer, **no amount of
polish fixes it** — rebuild the shape. Confirm which one is wanted up front.

**"It looks bad" is not actionable; the FEELING is.** Ask for the impression they
want ("premium product unboxing", "technical inspection") and the goal ("what
should the visitor conclude?"), then translate. Also ask what the object
represents to the business — the animation should carry the product story, not be
decoration.

**Back up the previous file before overwriting it** (e.g. `<name>.max-backup.html`)
when it came from another agent or the user — they may want to compare.

## The scroll architecture (copy this shape)

```html
<div class="scroll-track">                        <!-- height: 500vh -->
  <div class="stage">                             <!-- position: sticky; top:0; height:100vh -->
    <canvas id="gl"></canvas>
    <div class="overlay">…captions / CTA…</div>   <!-- pointer-events:none -->
  </div>
</div>
```

- Progress is the ONLY clock:
  `progress = clamp(-track.getBoundingClientRect().top / (track.offsetHeight - innerHeight), 0, 1)`.
  Drive **every** transform from it. A time-based tween desyncs from the scrollbar
  and cannot be scrubbed backwards — never mix the two.
- Map progress to state with two helpers: `seg(p, a, b)` (0..1 inside a window) and
  a smoothstep `ease(t) = t*t*(3-2t)`. Give each beat its own `[a, b]` window, and
  let beats overlap slightly — the lid lifting while the walls begin to open reads
  better than strict sequencing.
- **Smooth the scrub**: keep `target` (from scroll) and `p` (smoothed,
  `p += (target - p) * 0.12` per frame); snap `p = target` when within ~0.0004 so it
  settles instead of creeping.
- **Pause the render loop when the track is off-screen** with `IntersectionObserver`.
  A hero must not burn GPU/RAM while the user reads the rest of the page — this
  matters a lot on a memory-pressured machine.
- Captions: give each a `data-at="0.00…0.88"` and cross-fade by progress (in over the
  first ~20% of its segment, out over the last ~20%). Toggle the final CTA on at
  `p > 0.88`.

## Render / performance (keeps a single file single-file)

- Three.js via an `importmap` module script from a CDN.
- Cap `setPixelRatio(Math.min(devicePixelRatio, 2))`.
- **ONE shadow-casting `DirectionalLight`** plus an invisible shadow catcher:
  `new THREE.Mesh(new THREE.PlaneGeometry(80,80), new THREE.ShadowMaterial({opacity:.34}))`
  rotated flat. Cheaper and cleaner than a lit floor.
- Add a `HemisphereLight` for ambient, plus one coloured rim and one fill light —
  three cheap lights read far better than one bright one.
- **Generate textures procedurally on a `<canvas>`** (wood grain = base fill +
  hundreds of low-alpha strokes + a few radial "knots"). No image files, so the
  page stays one portable file.
- Wrap `new WebGLRenderer()` in try/catch, add a `no-webgl` body class, and make the
  fallback show the captions statically — a blank hero is worse than a flat one.

## Geometry pitfalls (each cost real time)

- **Hinged panels: put the pivot AT the hinge edge.** Create a `Group` positioned on
  the hinge line and offset the mesh `+h/2` inside it, so `group.rotation.x` swings
  the panel like a real hinge. A mesh built centred rotates about its middle instead.
- **A side wall must be built thickness-on-X, NOT rotated into place.** Do not make a
  thickness-on-Z panel and add `rotation.y = PI/2` — composing Euler `y` + `z`
  rotates it about the wrong axis and it swings sideways. For left/right walls use
  `BoxGeometry(T, H, D)` and swing with `.rotation.z` (left `+`, right `−` moves them
  outward).
- **Trim moves WITH its panel.** Slats, straps and handles added to the parent group
  stay floating in place when the wall opens. Add them as children of the panel's
  pivot.
- Animate the whole-object group's `rotation.y` slowly across the scroll so the
  reveal is never static, and dolly the camera slightly (`lookAt` y rising with
  progress) so the reveal has depth.

## Verification (you cannot see the render)

You have no eyes on the canvas. Verify everything verifiable, then be explicit that
the visual is unverified:

1. Extract the module script and syntax-check it — HTML linters do not parse it:
   `node --check <extracted>.mjs`. Catches unbalanced braces from a bad edit.
2. `grep` for duplicate `id=` — a duplicate silently breaks `getElementById`.
3. Confirm the CDN import actually resolves (`curl -o /dev/null -w '%{http_code}'`).
4. Tell the user plainly you cannot see the 3D, then ask for THREE specific
   observations, not "how does it look": does the material read correctly (wood vs
   plastic)? is the scroll PACE right (does the reveal finish too early / drag)? are
   the individual objects recognisable?
5. After any multi-line scripted/regex edit, re-read the edited region — a regex
   that removes a block can eat an adjacent structural line.
