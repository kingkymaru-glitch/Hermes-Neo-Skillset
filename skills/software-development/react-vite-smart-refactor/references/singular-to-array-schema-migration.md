# Singular → array schema migration in a React component

Class of task: a DB/type column changes from one value to many
(`area_polygon` → `area_polygons: T[] | null`), and/or a stored object gains
new persisted fields (annotations gain `w`/`h`). Types are already updated by
someone else; your job is to make ONE component match them.

## Order of operations that works

1. **Read the authoritative type first.** Derive local aliases from it instead
   of re-declaring the shape, so drift is impossible:
   ```ts
   type AreaPolygon = { type: "Polygon"; coordinates: number[][][] };
   type Annotation  = ProjectSite["annotations"][number];
   ```
   `T[keyof]`/`T["field"][number]` indexed access means a later types.ts change
   surfaces as a tsc error rather than silent divergence.

2. **Fix the EMPTY_/default constant before anything else.** A stale default
   object (`area_polygon: null`, missing `annotations: []`) produces a cascade
   of confusing errors at every spread site. One edit kills many.

3. **Patch in passes, not one giant rewrite:** constant+state → effects →
   handlers → JSX. The patch tool returns LSP diagnostics after each pass, so
   each pass tells you exactly what the next pass must fix. Errors that appear
   mid-sequence (`Cannot find name 'polyRef'`) are expected scaffolding noise,
   not mistakes — they resolve as you go.

4. **Grep for the old singular name at the end** across `src/`, expect zero.
   Type-checking alone can miss it in `any`-typed or optional-chained paths.

## Array-ification patterns

- **Ref array with unconditional teardown.** A single `useRef<any>` becomes
  `useRef<any[]>([])`. Remove EVERY previous layer before re-adding, and do the
  teardown *outside* any early return, or stale layers leak on the
  now-empty-array case:
  ```ts
  for (const l of polyRefs.current) { try { map.removeLayer(l); } catch {} }
  polyRefs.current = [];
  for (const poly of site?.area_polygons ?? []) { /* add + push */ }
  ```
  The old code's `if (!site?.area_polygon) return;` guard is exactly the bug to
  avoid: with arrays, "nothing to draw" still requires cleanup.

- **Append, never overwrite.** `[...(site?.x ?? []), item]`.

- **Conditional field spread for one-time seeding.** When a derived field
  (map center) must only be set on the FIRST item, don't pass nulls:
  ```ts
  const first = site?.center_lon == null;
  persist({ items: [...list, item], ...(first ? { center_lon, center_lat } : {}) });
  ```
  Spreading `{}` omits the keys entirely so the patch semantics stay clean.

- **Per-index delete** = `list.filter((_, idx) => idx !== i)`. Keep the
  bulk "delete all" action too; they answer different user intents.

- **Callbacks that read the array need the container in deps.** `useCallback`
  bodies reading `site?.area_polygons` must depend on `site`, or they append to
  a stale snapshot and silently drop concurrent additions.

## Pixel-positioned DOM overlays on a map (Leaflet)

- Absolutely-positioned React overlays computed from
  `map.latLngToContainerPoint()` are **frozen at last render**. React has no
  idea the map panned. Subscribe and bump a tick:
  ```ts
  useEffect(() => {
    const bump = () => setMapTick(t => t + 1);
    map.on("move", bump); map.on("zoom", bump); map.on("resize", bump);
    return () => { map.off("move", bump); map.off("zoom", bump); map.off("resize", bump); };
  }, [mapReady]);
  ```
  Put the tick in a `data-*` attribute, NOT in `key` — keying on it remounts the
  subtree every animation frame and destroys focus/pointer capture mid-drag.

- **Pixel resize needs no lat/lng conversion.** Move handlers convert
  `dxPx → dLng` via bounds ratio; a width/height handle just adds the raw pixel
  delta with a floor: `Math.max(60, startW + dxPx)`. Handle it as an early
  `return` at the top of the shared pointer-move handler.

- **Saved vs draft resize need different commit paths.** Draft resize mutates
  local draft state. Resizing an already-persisted item needs a transient
  "override" state for the live drag plus a commit-on-pointer-up that calls
  persist once — never persist per pointermove.

- `stopPropagation` on the inner contentEditable's pointerdown, or dragging the
  body steals the text caret.

- Elements need `pointerEvents: "auto"` inside a `pointerEvents: "none"`
  full-bleed overlay wrapper, and `touchAction: "none"` for pointer capture.

## Reporting

State the mandated gate result plainly (`tsc --noEmit` → exit 0). If a
non-mandated gate is red, see
`references/lint-baseline-vs-introduced-errors.md` — do not imply overall
green, and do not silently expand scope to chase pre-existing violations.
