# Entity CRUD context pattern (R-Tessera example)

Field/caller-visible reconstructions from the wait, load, save, and deep-link
flows shipped on `main` after the emergency Supabase-wiring pass.

## Context boundary — safe aliasing

If a context exports both reactive state and a cloud helper with the same name,
destructure with renaming at the consumer:

```js
const {
  nodes,
  setNodes,
  loadNodesFromCloud,
  addNode: addNodeFromCloud,
  updateNode: updateNodeFromCloud,
  removeNode: removeNodeFromCloud,
  reloadNodes: reloadFromCloud,
} = useEdgeData()
```

The reactive updater (`addNode`, `updateNode`, `removeNode`, if present) is a
synchronous local setter; cloud helpers are async Supabase writes. After each
write, call `reloadFromCloud()` to reconcile server defaults.

## Call-site audit after refactor

After patching, verify the consumer only calls the aliased cloud helper:

```bash
grep -nE "await addNode\(|await updateNode\(|await removeNode\(" src/App.jsx
# Expect: no matches, or only inside the context file itself.
```

One missed call (`createNodeGroup` calling bare `addNode`) caused runtime drift
until caught by this grep+fix loop.

## Field-mapping guard

DB columns should be fixed and named once; the JS layer translates documents:

```js
// Inside context helper
const row = {
  model_url: model.url,
  lat: model.latitude,
  lon: model.longitude,
}
```

`lat`/`lon` collisions with JS-reserved words are fine in Postgres column names,
but if you destructure them with an object-literal shorthand in JS, rename the
JS keys to avoid shadowing.

## URL deep-link effect

Native URLSearchParams, no router needed:

```js
useEffect(() => {
  const params = new URLSearchParams(window.location.search)
  const modelId = params.get('model_id')
  if (!modelId || !isSupabaseConfigured) return
  let cancelled = false
  ;(async () => {
    const { data, error } = await supabase
      .from('glb_models')
      .select('*')
      .eq('id', modelId)
      .single()
    if (cancelled || error || !data) return
    await new Promise((resolve) => requestAnimationFrame(resolve))
    const viewer = viewerRef.current
    if (!viewer) return
    viewer.camera.flyTo({
      destination: Cartesian3.fromDegrees(
        Number(data.longitude),
        Number(data.latitude),
        Number(data.height || 0) + 80,
      ),
      orientation: {
        heading: CesiumMath.toRadians(Number(data.heading || 0)),
        pitch: CesiumMath.toRadians(Number(data.pitch || -25)),
        roll: CesiumMath.toRadians(Number(data.roll || 0)),
      },
      duration: 2,
    })
  })()
  return () => { cancelled = true }
}, [isSupabaseConfigured])
```

Wait one animation frame after fetch; otherwise `viewerRef.current` is still
null because the Cesium `<Viewer>` has not finished initializing.

## Migration flow for new entity table

```bash
# 1) Create migration file
supabase migration new <name>

# 2) Push to live project
supabase db push
```

`supabase db push` prompts for confirmation; answer `Y` once. The live URL for
`.../api/nodes` returning 404 is expected after migration removal — all reads
now flow through the context.

## Build/verify sequence

```bash
npm run build        # must exit 0 before commit
git add -A
git commit -m "fix/feat: ..."
git push origin main  # Vercel autodeploys
```

Ignored `dist/` churn in `git status` is normal after rebuild; it is not a
regression if the tree shows stale `D dist/...` plus a new `dist/...` while
`.gitignore` covers `dist/`.
