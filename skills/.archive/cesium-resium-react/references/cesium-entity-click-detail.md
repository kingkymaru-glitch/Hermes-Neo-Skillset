# Cesium entity click → in-app detail panel (verified pattern)

Companion to G43. Use this when clicking a custom entity marker (node/pin/asset)
must open a detail panel WITHOUT overlap and WITHOUT locking the globe camera.

## What breaks (seen on R-Tessera `ProjectNodes.jsx`)
1. **Double-click handler** (`LEFT_DOUBLE_CLICK`, code 8) — the panel never opened.
   Cesium's default double-click is also bound to entity-tracking, and the custom
   handler wasn't reliably invoked. Use `LEFT_CLICK` (code 1).
2. **`viewer.selectedEntity`** read inside the click callback — Cesium only fills
   `selectedEntity` AFTER the click resolves, so the first click sees `null` and
   only the second click finds it. Use `viewer.scene.pick(click.position)` instead
   (synchronous geometric hit-test).
3. **Camera lock** — Cesium's default double-click sets `viewer.trackedEntity`,
   pinning the camera onto the entity and freezing navigation. Neutralize it.

## Click handler (the fix)
```js
const resolveNodeId = (picked) => {
  const candidate = picked?.id?.id ?? picked?.id ?? picked?.primitive?.id
  let str = candidate
  if (typeof str !== 'string' && str?.id) str = str.id
  if (typeof str === 'string' && str.startsWith('node-')) return str.replace('node-', '')
  return null
}
useEffect(() => {
  if (!viewer || viewer.isDestroyed?.()) return
  const handler = viewer.screenSpaceEventHandler
  if (!handler) return
  const onClick = (click) => {
    if (!show || !click?.position) return
    const picked = viewer.scene.pick(click.position)
    const nodeId = resolveNodeId(picked)
    if (!nodeId) return
    const n = nodes.find((x) => x.id === nodeId)
    if (n) openDetail(n)   // flyTo + setSelected + fetch details
  }
  handler.setInputAction(onClick, 1 /* LEFT_CLICK */)
  return () => handler.removeInputAction(1)
}, [viewer, show, nodes, openDetail])

// Camera must never lock onto the node:
useEffect(() => {
  if (!viewer || viewer.isDestroyed?.()) return
  const release = () => { if (viewer.trackedEntity) viewer.trackedEntity = undefined }
  const handle = viewer.scene.preRender.addEventListener(release)
  release()
  return () => handle.remove()
}, [viewer])
```

## Panel placement to avoid overlap
- If a left-docked list panel exists, dock the detail panel on the **right**
  (R-Tessera: `position: fixed; right: 14px; bottom: 60px`) so they can never
  overlap. A top-right detail panel collides with a top-right Map Control drawer.
- Kept the list panel (left) and detail panel (right) on opposite sides — the
  original overlap bug was caused by BOTH the detail card and the list sitting at
  `fixed; left; top:70px`.

## openDetail shape (fetch live details from shared Supabase)
```js
const openDetail = useCallback(async (n) => {
  viewer.camera.flyTo({ destination: Cartesian3.fromDegrees(n.lon, n.lat, 1200000), duration: 1.0 })
  setSelected(n)
  setSiteLoading(true)
  const { site, error } = await fetchProjectSite(n.lunav_project_id, n.lunav_share_token)
  setSiteLoading(false)
  if (error) setSiteError(error.message); else setSite(site)
}, [viewer])
```
`fetchProjectSite` calls the SAME `get_shared_project` SECURITY DEFINER RPC anon
viewers use — so the detail table renders the real public record (no service role).
