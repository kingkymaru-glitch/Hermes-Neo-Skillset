# Pitfall 6d — named cesium/resium/three export used but never imported

## Symptom
`lint` 0 errors, `build` green, but the page loads to a **blank white screen** (React
ErrorBoundary tears the tree down). Console: `ReferenceError: <Name> is not defined`.
Reported by the user as "localhost:5174 blank / errors out".

## Real cause (MARU `my-digital-twin` / `src/App.jsx`)
Added `heightReference={HeightReference.CLAMP_TO_GROUND}` to five `<PointGraphics>`
markers, but `HeightReference` was absent from the file's `import { ... } from 'cesium'`
block. The name exists in the Cesium library, so it is NOT an unresolved-module import
(build passes). It is simply not bound in this file → runtime ReferenceError.

## Distinguish from the other Pitfall-6 variants
- 6: un-imported `useX` hook or un-destructured context field.
- 6b: parent-scoped flag read inside a nested component.
- 6c: hook exists in file but the rendering component never calls it.
- **6d (this one): a plain named export** (`HeightReference`, `Cartographic`,
  `NearFarScalar`, `VerticalOrigin`, `Color`, `Entity`, `PointGraphics`, …) referenced at
  module/component top level, missing from the `from 'cesium'` import block. Grep gates
  for `useX(` miss it because there's no `use`.

## Prevention (encode into the edit)
When you ADD a reference to a library named export, the SAME edit must add it to the
matching `import { ... } from 'cesium' | 'resium' | 'three'` block — IF not already there.
This repo keeps one big `from 'cesium'` block at the top of App.jsx; grep it first.

## Grep gate (after the edit)
```bash
grep -oE "HeightReference|Cartographic|NearFarScalar|VerticalOrigin|Cartesian[23]" src/App.jsx | sort -u
grep -n "from 'cesium'" src/App.jsx   # then read the block; every name above must be listed
```
If a name you just added is referenced but NOT in the import block → build still passes,
page crashes at runtime. Grep, don't trust the build.

## Fast triage once the page is blank
```bash
curl -s "http://localhost:5174/src/App.jsx" | grep -c "HeightReference"   # present in served module?
# then open the source and confirm it's listed in the `import { ... } from 'cesium'` block
```
