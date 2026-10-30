# Viewer3D — persistent model MOVE + ROTATE (Phase 2)

Raw Three.js (no react-three-fiber) in `src/components/Viewer3D.tsx`. This is the
pattern for letting a user move/rotate the active model via sliders and persisting
it to Supabase. Reuse it for any future "transform the model in the cockpit" work.

## The geometry trick (why it works)
A GLB/OBJ loads at its own arbitrary origin. To rotate about the model's OWN centre
(not the world origin) you must FIRST re-center the geometry at the origin, THEN apply
the persisted offset on top. `place(obj)` does:

```ts
const box = new THREE.Box3().setFromObject(obj);
const center = box.getCenter(new THREE.Vector3());
const size = box.getSize(new THREE.Vector3());
obj.position.sub(center);                       // re-center at world origin
const scale = 25 / Math.max(size.x, size.y, size.z);
obj.scale.setScalar(scale);                     // uniform 25-unit footprint
modelBasePosRef.current = obj.position.clone(); // capture re-centered base
```
`modelBasePosRef` is the key: it stores the re-centered position so live slider
changes can RE-APPLY without reloading the model.

## Persisted transform application (at load)
Rotation is stored in DEGREES in the DB → convert with `THREE.MathUtils.degToRad`.
```ts
const t = modelTransform;
if (t) {
  obj.position.x += t.position_x;
  obj.position.y += t.position_y;
  obj.position.z += t.position_z;
  obj.rotation.x = THREE.MathUtils.degToRad(t.rotation_x);
  obj.rotation.y = THREE.MathUtils.degToRad(t.rotation_y);
  obj.rotation.z = THREE.MathUtils.degToRad(t.rotation_z);
}
```

## Live re-apply (slider drag, no reload)
A dedicated effect re-applies whenever `modelTransform` changes — keeps dragging smooth:
```ts
useEffect(() => {
  const obj = modelGroupRef.current, base = modelBasePosRef.current;
  if (!obj || !base) return;
  obj.position.set(base.x + (modelTransform?.position_x ?? 0),
                   base.y + (modelTransform?.position_y ?? 0),
                   base.z + (modelTransform?.position_z ?? 0));
  obj.rotation.set(THREE.MathUtils.degToRad(modelTransform?.rotation_x ?? 0),
                   THREE.MathUtils.degToRad(modelTransform?.rotation_y ?? 0),
                   THREE.MathUtils.degToRad(modelTransform?.rotation_z ?? 0));
}, [modelTransform]);
```

## Click-to-pick the MODEL (open the transform drawer)
In `handleClick`, AFTER marker/proxy picking fails, raycast the model group:
```ts
const liveRef = useRef({ ..., onModelClick });
// inside handleClick:
const modelHits = raycaster.intersectObject(modelGroupRef.current, true);
if (modelHits.length > 0) { liveRef.current.onModelClick?.(modelGroupRef.current?.userData?.modelId); return; }
```
Wire `onModelClick` in `ProjectWorkspace` to open the transform drawer:
`onModelClick={() => !readOnly && setTransformOpen(true)}`.

## Props added to Viewer3D
- `modelTransform?: { position_x,y,z: number; rotation_x,y,z: number }` (degrees).
- `onModelClick?: (modelId: string) => void`.

## Workspace side (ProjectWorkspace.tsx)
- `saveModelTransform(patch: Partial<Model3D>)` → `supabase.from("models").update(patch).eq("id", activeModelId)` then `setModels(...)`.
- Drawer rendered from `transformOpen && activeModel && !readOnly`, with 6 `<input type="range">`
  (Move X/Y/Z ±50 step 0.5; Rotate X/Y/Z ±180 step 1) + "Reset to Origin".
- Typed dynamic access: `activeModel[\`position_${axis}\`] ?? 0` cast `as Partial<Model3D>`.
- Model-row ⤢ button sets `activeModelId` + `setTransformOpen(true)`.

## Schema
```sql
alter table public.models
  add column if not exists position_x double precision not null default 0,
  add column if not exists position_y double precision not null default 0,
  add column if not exists position_z double precision not null default 0,
  add column if not exists rotation_x double precision not null default 0,  -- degrees
  add column if not exists rotation_y double precision not null default 0,
  add column if not exists rotation_z double precision not null default 0;
```
Write the migration to `supabase/migrations/YYYYMMDD_<name>.sql` (idempotent with
`IF NOT EXISTS` guards) AND mirror the columns into `supabase/schema.sql`.

## Pitfalls
- **Select `*` carries new columns for free.** `page.tsx` loads models with `.select("*")`,
  so the new columns flow into `Model3D` without a query change. BUT if a future query
  uses an EXPLICIT column list, you MUST add `position_x,…` to it or they'll be `undefined`.
- **Don't rotate the raw loaded object without re-centering first** — it spins around the
  world origin and flies off-screen. Always re-center (the `obj.position.sub(center)` step).
- **`Model3D` type** must declare the 6 new fields (`file_size_bytes`, `position_*`,
  `rotation_*`) or TS errors on `activeModel.position_x`.
- **Apply the migration to the LIVE DB manually** (Vercel does not run migrations).
  SQL Editor paste, or `supabase db query --linked --file` if the CLI is linked.
