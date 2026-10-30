# Spatial Proxy placeholders that are NOT defects (ss-rover-cloud pattern)

Reusable lesson from the ss-rover-cloud "Spatial Proxy" feature (Three.js / Next.js inspection app). The user wanted box/plane placeholders that (a) are never counted as defects, (b) are click-selectable in the 3D view, (c) carry a free-text description, (d) are deletable — distinct from real findings.

## Keep placeholders as a SEPARATE entity from defects
- Defects = `markers` table (PASS/WARNING/FAIL severity). Proxies = `proxies` table (`ProxyShape`). They are different tables from day one, so severity counters (`markers.filter(m=>m.status===X).length`) never include them — by construction.
- The trap: even when data is separate, the UI can still imply "this is a defect" if (1) the proxy renders with the same red/amber severity coloring as findings, or (2) there's no explicit "not a defect" copy. Fix: give proxies their own default color (turquoise `#00e5c3`) and add a visible note in the editor drawer: "Spatial Proxy — a standalone placeholder… not a defect and never counted in PASS/WARNING/FAIL totals."

## Enable click-to-select a NON-marker object in the 3D view
Markers already have a raycaster pass (`pickMarker`). Proxies need their OWN pass because they live in a different `Map` (`proxyObjectsRef`, not `markerObjectsRef`):
```ts
const pickProxy = (e: MouseEvent): string | null => {
  const rect = renderer.domElement.getBoundingClientRect();
  mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
  mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;
  raycasterRef.current.setFromCamera(mouse, camera);
  const hits = raycasterRef.current.intersectObjects(
    Array.from(proxyObjectsRef.current.values()), true);
  for (const h of hits) {
    let o: THREE.Object3D | null = h.object;
    while (o && !o.userData?.proxyId) o = o.parent;
    if (o?.userData?.proxyId) return o.userData.proxyId as string;
  }
  return null;
};
```
- Tag each proxy mesh with `mesh.userData.proxyId = p.id` in the proxy sync effect.
- In the shared `handleClick`, BEFORE the marker-create branch, call `pickProxy(e)`; if hit and not `readOnly`, fire `onProxyClick?.(id)` and `return` (so selecting a proxy doesn't also try to create a marker).
- Mirror the marker pattern: keep the callback in a `liveRef` so the stable click handler sees the latest `onProxyClick`.
- Parent component passes `onProxyClick={setActiveProxyId}` so clicking the mesh opens the proxy editor drawer (same UX as clicking a finding).

## Description field on a placeholder
- Add `description text` column to the proxies table (idempotent `alter table … add column if not exists description text`) and surface it in any read-only RPC (`get_shared_project`) so the client portal shows it too.
- Type `ProxyShape.description: string | null`. Drawer textarea saved via the existing `saveProxy(patch)` (`.update(patch)` covers it).

## Delete scope
The proxy delete must only remove the proxy (`supabase.from('proxies').delete().eq('id', id)`), never a marker. Keep it gated to `!readOnly`.

## Verify
`npm run build` green; apply the migration (`supabase db query --linked --file <migration>.sql` to the linked project); confirm column via `information_schema.columns`. Push → Vercel auto-promotes. Re-derive the live bundle hash and grep (per `vercel-prod-deploy-verification`) — but proxies are inside an auth-gated SPA so bundle-grep may not show; rely on the DB column check + a user screenshot of the drawer.
